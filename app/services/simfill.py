import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import aiomysql

from app.services.db_pool import db_pool, is_connection_error
from app.settings.config import settings

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]

BATCH_SIZE = 200
GRACE_MONTHS = 6  # 到期时间固定宽限月数：出库时间 + 卡年限 + 6 个月
OUTSTOCK_TYPE = "OT3"  # 批发出库
MATERIAL_TYPE_SIM = "流量卡"
MAX_KEYWORDS = 200
EMPTY_DT_STR = "0000-00-00 00:00:00"


def _to_str(value: Any) -> str:
    """统一转字符串（datetime -> 'YYYY-MM-DD HH:MM:SS'，None -> ''）"""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value).strip()


def _is_empty_dt(value: Any) -> bool:
    """判断数据库时间字段是否为空（None / '' / 零值）"""
    return value is None or _to_str(value) in ("", EMPTY_DT_STR)


def _parse_sim_age(goods_name: str | None) -> int | None:
    """
    从仓储商品名解析卡年限（年）。
    规则与 SIM卡状态校验报警/SIM卡状态校验预警.py 中「SIM卡卡期限为0或无」口径一致：
    取商品名中「卡」字前的数字，如 '12年卡' -> 12。
    """
    if not goods_name:
        return None
    # 优先匹配「12年」「12 年」
    m = re.search(r"(\d+)\s*年", goods_name)
    if m:
        return int(m.group(1))
    # 兜底：取第一个「卡」字前最后两位（与预警脚本同口径）
    if "卡" in goods_name:
        head = goods_name.split("卡", 1)[0]
        tail = head[-2:]
        if tail.isdigit():
            return int(tail)
    return None


class SIMFillService:
    """
    SIM卡批发数据补录服务。

    背景：仓储中心批发出库（OT3）后经 MQ 推送 SIM 卡中心，
    部分卡因 MQ 丢失 / 消费失败未同步。本服务按正式同步链路
    （见 D:/github/SIM/AGENTS.md §4）反查各表缺口并补录，
    **只写 SIM 卡中心（连接 SIM_CONN）**，仓储中心（WMS_CONN）仅只读查询。
    """

    async def _ensure_wms_pool(self):
        wms_conn_id = await settings.WMS_CONN_ID()
        if wms_conn_id == 0:
            raise ValueError("仓储中心数据库连接未配置")
        pool = await db_pool.ensure_pool(wms_conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("仓储中心连接必须是 MySQL 类型")
        return wms_conn_id, pool

    async def _ensure_sim_pool(self):
        sim_conn_id = await settings.SIM_CONN_ID()
        if sim_conn_id == 0:
            raise ValueError("SIM卡中心数据库连接未配置")
        pool = await db_pool.ensure_pool(sim_conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("SIM卡中心连接必须是 MySQL 类型")
        return sim_conn_id, pool

    async def _reconnect_known_pools(self):
        for conn_id in (await settings.WMS_CONN_ID(), await settings.SIM_CONN_ID()):
            if conn_id:
                try:
                    await db_pool.reconnect_pool(conn_id)
                except Exception as exc:
                    logger.warning(f"自动重连数据库失败: conn_id={conn_id}, error={exc}")

    async def _emit_progress(
        self,
        progress_cb: ProgressCallback | None,
        stage: str,
        message: str,
        progress: int,
        **extra,
    ):
        if progress_cb:
            await progress_cb({
                "stage": stage,
                "message": message,
                "progress": max(0, min(progress, 100)),
                **extra,
            })

    # ------------------------------------------------------------------
    # 输入解析
    # ------------------------------------------------------------------
    @staticmethod
    def parse_keywords(text: str) -> list[str]:
        keywords = []
        seen = set()
        for line in (text or "").split("\n"):
            token = line.strip()
            if not token or token in seen:
                continue
            seen.add(token)
            keywords.append(token)
        return keywords

    # ------------------------------------------------------------------
    # 仓储中心（WMS_CONN，只读）：解析关键词 -> 批发出库单据
    # ------------------------------------------------------------------
    async def _fetch_wms_outstock_by_orders(self, cur, out_stock_nos: list[str]) -> dict[str, dict]:
        """按出库单号查批发出库单据（现表 + 历史表），返回 {OutStockNo: row}"""
        if not out_stock_nos:
            return {}
        sql = """
            SELECT o.OutStockNo, o.OutStockType, o.AuditState,
                   o.AuditTime, o.AuditPerson, o.AuditName,
                   o.CustSettleId, o.CustSettleName,
                   o.ToWarehouseId, o.ToWarehouseName,
                   d.GoodsName, d.MaterialType, n.MaterialNo,
                   sd.ProCode AS DeliveProCode, sd.CityCode AS DeliveCityCode,
                   sd.DeliveAddress, sd.LinkMan, sd.LinkTel, sd.Id AS DeliveId
            FROM tb_outstockinfo o
            JOIN tb_outstockdetail d ON d.OutStockId = o.Id AND d.Deleted = 0
            JOIN tb_outstockno n ON n.DetailId = d.Id AND n.Deleted = 0
            LEFT JOIN tb_stockdeliveinfo sd ON sd.StockId = o.Id AND sd.Deleted = 0
            WHERE o.Deleted = 0 AND o.OutStockType = %s AND o.OutStockNo IN ({ph})
            UNION ALL
            SELECT o.OutStockNo, o.OutStockType, o.AuditState,
                   o.AuditTime, o.AuditPerson, o.AuditName,
                   o.CustSettleId, o.CustSettleName,
                   o.ToWarehouseId, o.ToWarehouseName,
                   d.GoodsName, d.MaterialType, n.MaterialNo,
                   sd.ProCode AS DeliveProCode, sd.CityCode AS DeliveCityCode,
                   sd.DeliveAddress, sd.LinkMan, sd.LinkTel, sd.Id AS DeliveId
            FROM tb_outstockinfohis o
            JOIN tb_outstockdetailhis d ON d.OutStockId = o.Id AND d.Deleted = 0
            JOIN tb_outstockno n ON n.DetailId = d.Id AND n.Deleted = 0
            LEFT JOIN tb_stockdeliveinfo sd ON sd.StockId = o.Id AND sd.Deleted = 0
            WHERE o.Deleted = 0 AND o.OutStockType = %s AND o.OutStockNo IN ({ph})
        """
        result: dict[str, dict] = {}
        for start in range(0, len(out_stock_nos), BATCH_SIZE):
            chunk = out_stock_nos[start:start + BATCH_SIZE]
            ph = ",".join(["%s"] * len(chunk))
            await cur.execute(sql.format(ph=ph), (OUTSTOCK_TYPE, *chunk, OUTSTOCK_TYPE, *chunk))
            for row in await cur.fetchall():
                out_stock_no = row["OutStockNo"]
                out_stock_no = row["OutStockNo"]
                prev = result.get(out_stock_no)
                # 现表优先；同一单多条收货地址时取 Id 最小的一条
                if prev is None or (row.get("DeliveId") or 0) < (prev.get("DeliveId") or 0):
                    result[out_stock_no] = row
        return result

    async def _fetch_wms_outstock_by_cards(self, cur, sim_numbers: list[str]) -> dict[str, dict]:
        """按卡号反查：库存卡最近一次动作为批发出库(OT3) -> 出库单"""
        if not sim_numbers:
            return {}
        sql = """
            SELECT o.OutStockNo, o.OutStockType, o.AuditState,
                   o.AuditTime, o.AuditPerson, o.AuditName,
                   o.CustSettleId, o.CustSettleName,
                   o.ToWarehouseId, o.ToWarehouseName,
                   d.GoodsName, d.MaterialType, n.MaterialNo,
                   sd.ProCode AS DeliveProCode, sd.CityCode AS DeliveCityCode,
                   sd.DeliveAddress, sd.LinkMan, sd.LinkTel, sd.Id AS DeliveId
            FROM tb_materialstock a
            JOIN tb_outstockinfo o ON o.OutStockNo = a.LastStockNo AND o.Deleted = 0 AND o.OutStockType = %s
            JOIN tb_outstockdetail d ON d.OutStockId = o.Id AND d.Deleted = 0
            JOIN tb_outstockno n ON n.DetailId = d.Id AND n.Deleted = 0
            LEFT JOIN tb_stockdeliveinfo sd ON sd.StockId = o.Id AND sd.Deleted = 0
            WHERE a.Deleted = 0 AND a.LastStockType = %s AND n.MaterialNo = a.MaterialNo
              AND n.MaterialNo IN ({ph})
            UNION ALL
            SELECT o.OutStockNo, o.OutStockType, o.AuditState,
                   o.AuditTime, o.AuditPerson, o.AuditName,
                   o.CustSettleId, o.CustSettleName,
                   o.ToWarehouseId, o.ToWarehouseName,
                   d.GoodsName, d.MaterialType, n.MaterialNo,
                   sd.ProCode AS DeliveProCode, sd.CityCode AS DeliveCityCode,
                   sd.DeliveAddress, sd.LinkMan, sd.LinkTel, sd.Id AS DeliveId
            FROM tb_materialstock a
            JOIN tb_outstockinfohis o ON o.OutStockNo = a.LastStockNo AND o.Deleted = 0 AND o.OutStockType = %s
            JOIN tb_outstockdetailhis d ON d.OutStockId = o.Id AND d.Deleted = 0
            JOIN tb_outstockno n ON n.DetailId = d.Id AND n.Deleted = 0
            LEFT JOIN tb_stockdeliveinfo sd ON sd.StockId = o.Id AND sd.Deleted = 0
            WHERE a.Deleted = 0 AND a.LastStockType = %s AND n.MaterialNo = a.MaterialNo
              AND n.MaterialNo IN ({ph})
        """
        result: dict[str, dict] = {}
        for start in range(0, len(sim_numbers), BATCH_SIZE):
            chunk = sim_numbers[start:start + BATCH_SIZE]
            ph = ",".join(["%s"] * len(chunk))
            await cur.execute(
                sql.format(ph=ph),
                (OUTSTOCK_TYPE, OUTSTOCK_TYPE, *chunk, OUTSTOCK_TYPE, OUTSTOCK_TYPE, *chunk),
            )
            for row in await cur.fetchall():
                key = row["MaterialNo"]
                prev = result.get(key)
                # 同一卡多条收货地址时取 Id 最小的一条
                if prev is None or (row.get("DeliveId") or 0) < (prev.get("DeliveId") or 0):
                    result[key] = row
        return result

    async def resolve_wms_sources(self, keywords: list[str]) -> dict[str, Any]:
        """
        解析输入关键词（出库单号 / SIM卡号，任意混合，换行分隔已在 parse_keywords 处理）：

        返回 {
            "by_card": {SIM卡号: 出库单row},
            "resolved_orders": [出库单号...],
            "not_found": [无法解析的关键词...],
        }
        """
        by_card: dict[str, dict] = {}
        resolved_orders: set[str] = set()
        not_found: list[str] = []

        _, wms_pool = await self._ensure_wms_pool()
        async with wms_pool.acquire() as conn, conn.cursor(aiomysql.cursors.DictCursor) as cur:
            # 第一轮：全部关键词先按出库单号试
            order_map = await self._fetch_wms_outstock_by_orders(cur, keywords)
            for kw in keywords:
                if kw in order_map:
                    resolved_orders.add(kw)
            # 出库单 -> 卡号清单（只看 SIM 卡物料）
            for out_stock_no, row in order_map.items():
                if row.get("MaterialType") == MATERIAL_TYPE_SIM:
                    by_card[row["MaterialNo"]] = row
                resolved_orders.add(out_stock_no)

            # 第二轮：剩余关键词按卡号反查（库存卡最近一次动作为批发出库）
            rest = [kw for kw in keywords if kw not in order_map]
            card_map = await self._fetch_wms_outstock_by_cards(cur, rest)
            for sim_number, row in card_map.items():
                by_card[sim_number] = row
                resolved_orders.add(row["OutStockNo"])

            for kw in rest:
                if kw not in card_map:
                    not_found.append(kw)

        return {
            "by_card": by_card,
            "resolved_orders": sorted(resolved_orders),
            "not_found": not_found,
        }

    # ------------------------------------------------------------------
    # SIM 卡中心（SIM_CONN）：现状查询 + 补录计划计算
    # ------------------------------------------------------------------
    async def _fetch_sim_current(self, cur, sim_numbers: list[str]) -> dict[str, dict]:
        """按卡号查 SIM 卡中心现状（主表/状态表/库存表/跟踪记录数）"""
        if not sim_numbers:
            return {}
        sql = """
            SELECT i.SIMNumber, i.Id AS SimId, i.SIMYears,
                   s.SIMStatus, s.SIMMarkStatus, s.SIMLifeCycle, s.ExpiryDate,
                   w.OutStockTime, w.OperationName, w.OperationTime,
                   w.ProCode, w.ProName, w.CityCode, w.CityName,
                   (SELECT COUNT(1) FROM tb_simfollowinfo f
                     WHERE f.SIMNumber = i.SIMNumber
                       AND f.OperationName = '批发出库'
                       AND IFNULL(f.Deleted, 0) = 0) AS FollowCount
            FROM tb_siminfo i
            LEFT JOIN tb_simstatus s ON s.Id = i.Id
            LEFT JOIN tb_simwarehouse w ON w.Id = i.Id
            WHERE i.SIMNumber IN ({ph})
        """
        result: dict[str, dict] = {}
        for start in range(0, len(sim_numbers), BATCH_SIZE):
            chunk = sim_numbers[start:start + BATCH_SIZE]
            ph = ",".join(["%s"] * len(chunk))
            await cur.execute(sql.format(ph=ph), tuple(chunk))
            for row in await cur.fetchall():
                result[row["SIMNumber"]] = row
        return result

    async def _fetch_district_names(self, cur, codes: set[str]) -> dict[str, str]:
        """basic_district（SIM 卡中心库）区划编码 -> 名称，用于解析收货地址省市区"""
        codes = {c for c in codes if c}
        if not codes:
            return {}
        sql = ("SELECT Code, Name FROM basic_district "
               "WHERE Code IN ({ph}) AND Deleted = 0")
        result: dict[str, str] = {}
        for start in range(0, len(codes), BATCH_SIZE):
            chunk = sorted(codes)[start:start + BATCH_SIZE]
            ph = ",".join(["%s"] * len(chunk))
            await cur.execute(sql.format(ph=ph), tuple(chunk))
            for row in await cur.fetchall():
                result[row["Code"]] = row["Name"]
        return result

    @staticmethod
    def _delive_region(wms_row: dict, district_map: dict[str, str]) -> dict[str, str]:
        """取出库单收货地址（tb_stockdeliveinfo）的省市区编码，并解析名称"""
        pro_code = wms_row.get("DeliveProCode") or ""
        city_code = wms_row.get("DeliveCityCode") or ""
        return {
            "pro_code": pro_code,
            "pro_name": district_map.get(pro_code, "") if pro_code else "",
            "city_code": city_code,
            "city_name": district_map.get(city_code, "") if city_code else "",
        }

    @staticmethod
    def _build_plan(sim_number: str, wms_row: dict, sim_current: dict | None,
                    sim_age: int | None,
                    pro_code: str = "", pro_name: str = "",
                    city_code: str = "", city_name: str = "") -> dict[str, Any]:
        """
        按正式同步链路字段映射（AGENTS.md §4.2）计算单卡补录计划。

        返回结构（tables 中 pending=True 表示该表本次要写）：
        {
            "sim_number", "out_stock_no", "out_stock_time", "audit_name",
            "sim_age", "blocked_reason",
            "tables": {
                "tb_siminfo": {"pending": bool, "fields": [{"field","current","new"}]},
                "tb_simwarehouse": {"pending": bool, "fields": [...], "steps": {"outstock": bool, "region": bool}},
                "tb_simstatus": {"pending": bool, "fields": [...]},
                "tb_simfollowinfo": {"pending": bool, "fields": [...]},
            }
        }
        """
        plan: dict[str, Any] = {
            "sim_number": sim_number,
            "out_stock_no": wms_row.get("OutStockNo"),
            "out_stock_time": _to_str(wms_row.get("AuditTime")),
            "audit_name": _to_str(wms_row.get("AuditName")) or _to_str(wms_row.get("AuditPerson")),
            "sim_age": sim_age,
            "blocked_reason": None,
            "tables": {},
        }

        if sim_current is None:
            plan["blocked_reason"] = "SIM卡中心无此卡（未入库同步），请先用「SIM卡同步」入库"
            return plan
        if (sim_current.get("SIMMarkStatus") or 0) == 4:
            plan["blocked_reason"] = "卡已注销（SIMMarkStatus=4），不补录"
            return plan
        if (sim_current.get("SIMStatus") or 0) == 1:
            plan["blocked_reason"] = "卡已加装（SIMStatus=1），不补录"
            return plan
        if not plan["out_stock_time"]:
            plan["blocked_reason"] = "仓储出库单缺少审核时间（AuditTime），无法补录"
            return plan

        tables: dict[str, Any] = {}

        # 1) tb_siminfo.SIMYears（空才补）
        cur_years = sim_current.get("SIMYears")
        need_years = cur_years is None or int(cur_years or 0) == 0
        tables["tb_siminfo"] = {
            "pending": need_years and sim_age is not None,
            "fields": [{
                "field": "SIMYears",
                "current": cur_years,
                "new": sim_age,
            }],
            "blocked": need_years and sim_age is None,
        }

        # 2) tb_simwarehouse 出库时间/操作人/操作时间（空才补）
        need_outstock = _is_empty_dt(sim_current.get("OutStockTime"))
        # 3) tb_simwarehouse 省市区（空才补）
        need_region = not _to_str(sim_current.get("ProName")) or not _to_str(sim_current.get("CityName"))
        tables["tb_simwarehouse"] = {
            "pending": need_outstock or need_region,
            "steps": {"outstock": need_outstock, "region": need_region},
            "fields": [
                {"field": "OutStockTime", "current": _to_str(sim_current.get("OutStockTime")),
                 "new": plan["out_stock_time"] if need_outstock else None},
                {"field": "OperationName", "current": _to_str(sim_current.get("OperationName")),
                 "new": plan["audit_name"] if need_outstock else None},
                {"field": "OperationTime", "current": _to_str(sim_current.get("OperationTime")),
                 "new": plan["out_stock_time"] if need_outstock else None},
                {"field": "ProCode/ProName", "current": _to_str(sim_current.get("ProName")),
                 "new": f"{pro_name}({pro_code})" if need_region and pro_name else None},
                {"field": "CityCode/CityName", "current": _to_str(sim_current.get("CityName")),
                 "new": f"{city_name}({city_code})" if need_region and city_name else None},
            ],
            "blocked": need_region and not pro_name,
        }

        # 4) tb_simstatus.ExpiryDate（空才补）= 出库时间 + 卡年限 + 6 个月
        need_expiry = _is_empty_dt(sim_current.get("ExpiryDate"))
        tables["tb_simstatus"] = {
            "pending": need_expiry and sim_age is not None,
            "fields": [{
                "field": "ExpiryDate",
                "current": _to_str(sim_current.get("ExpiryDate")),
                "new": f"{sim_age}年+{GRACE_MONTHS}个月" if sim_age else None,
            }],
            "blocked": need_expiry and sim_age is None,
        }

        # 5) tb_simfollowinfo 批发出库跟踪记录（没有才插）
        follow_count = int(sim_current.get("FollowCount") or 0)
        tables["tb_simfollowinfo"] = {
            "pending": follow_count == 0,
            "fields": [{
                "field": "批发出库跟踪记录",
                "current": f"已有{follow_count}条",
                "new": "OperationName=批发出库, OperationSystem=4(订单中心)",
            }],
        }

        plan["tables"] = tables
        plan["has_pending"] = any(t.get("pending") for t in tables.values())
        plan["has_blocked"] = any(t.get("blocked") for t in tables.values())
        return plan

    # ------------------------------------------------------------------
    # SQL 构造（参数化执行 + 文本预览共用一套）
    # ------------------------------------------------------------------
    @staticmethod
    def _build_card_statements(plan: dict, pro_code: str = "", pro_name: str = "",
                               city_code: str = "", city_name: str = "") -> list[dict]:
        """
        按补录计划构造待执行语句（空才补、幂等），与 simcenter/批发出库未同步补数/_模板 一致。
        返回 [{sql, params, preview}]
        """
        sim_number = plan["sim_number"]
        out_stock_time = plan["out_stock_time"]
        audit_name = plan["audit_name"]
        sim_age = plan.get("sim_age")
        tables = plan.get("tables") or {}
        statements: list[dict] = []

        if tables.get("tb_siminfo", {}).get("pending"):
            sql = ("UPDATE tb_siminfo SET SIMYears = %s WHERE SIMNumber = %s "
                   "AND (SIMYears IS NULL OR SIMYears = 0)")
            statements.append({
                "sql": sql, "params": (sim_age, sim_number),
                "preview": f"UPDATE tb_siminfo SET SIMYears = {sim_age} WHERE SIMNumber = '{sim_number}' "
                           f"AND (SIMYears IS NULL OR SIMYears = 0);",
            })

        steps = tables.get("tb_simwarehouse", {}).get("steps") or {}
        if steps.get("outstock"):
            sql = ("UPDATE tb_simwarehouse SET OutStockTime = %s, "
                   "OperationName = IFNULL(NULLIF(OperationName,''), %s), "
                   "OperationTime = IFNULL(OperationTime, %s) "
                   "WHERE SIMNumber = %s "
                   "AND (OutStockTime IS NULL OR OutStockTime = '0000-00-00 00:00:00')")
            statements.append({
                "sql": sql, "params": (out_stock_time, audit_name, out_stock_time, sim_number),
                "preview": f"UPDATE tb_simwarehouse SET OutStockTime = '{out_stock_time}', "
                           f"OperationName = IFNULL(NULLIF(OperationName,''), '{audit_name}'), "
                           f"OperationTime = IFNULL(OperationTime, '{out_stock_time}') "
                           f"WHERE SIMNumber = '{sim_number}' "
                           f"AND (OutStockTime IS NULL OR OutStockTime = '0000-00-00 00:00:00');",
            })
        if steps.get("region") and pro_name and city_name:
            sql = ("UPDATE tb_simwarehouse SET ProCode = %s, ProName = %s, CityCode = %s, CityName = %s "
                   "WHERE SIMNumber = %s AND (IFNULL(ProName,'') = '' OR IFNULL(CityName,'') = '')")
            statements.append({
                "sql": sql, "params": (pro_code, pro_name, city_code, city_name, sim_number),
                "preview": f"UPDATE tb_simwarehouse SET ProCode = '{pro_code}', ProName = '{pro_name}', "
                           f"CityCode = '{city_code}', CityName = '{city_name}' "
                           f"WHERE SIMNumber = '{sim_number}' "
                           f"AND (IFNULL(ProName,'') = '' OR IFNULL(CityName,'') = '');",
            })

        if tables.get("tb_simstatus", {}).get("pending"):
            months = int(sim_age) + GRACE_MONTHS
            sql = ("UPDATE tb_simstatus s JOIN tb_simwarehouse w ON w.Id = s.Id "
                   "SET s.ExpiryDate = DATE_ADD(%s, INTERVAL %s MONTH) "
                   "WHERE s.SIMNumber = %s "
                   "AND (s.ExpiryDate IS NULL OR s.ExpiryDate = '0000-00-00 00:00:00')")
            statements.append({
                "sql": sql, "params": (out_stock_time, months, sim_number),
                "preview": f"UPDATE tb_simstatus s JOIN tb_simwarehouse w ON w.Id = s.Id "
                           f"SET s.ExpiryDate = DATE_ADD('{out_stock_time}', INTERVAL {months} MONTH) "
                           f"WHERE s.SIMNumber = '{sim_number}' "
                           f"AND (s.ExpiryDate IS NULL OR s.ExpiryDate = '0000-00-00 00:00:00');",
            })

        if tables.get("tb_simfollowinfo", {}).get("pending"):
            sql = ("INSERT INTO tb_simfollowinfo "
                   "(SIMId, SIMNumber, SIMLifeCycle, SIMStatus, SIMMarkStatus, "
                   " OperationName, OperationSystem, CreatedByName, CreatedAt, Deleted) "
                   "SELECT s.Id, s.SIMNumber, s.SIMLifeCycle, s.SIMStatus, s.SIMMarkStatus, "
                   " '批发出库', 4, %s, %s, 0 FROM tb_simstatus s "
                   "WHERE s.SIMNumber = %s "
                   "AND NOT EXISTS (SELECT 1 FROM tb_simfollowinfo f "
                   "  WHERE f.SIMNumber = %s AND f.OperationName = '批发出库' "
                   "    AND f.CreatedAt = %s AND IFNULL(f.Deleted,0) = 0)")
            statements.append({
                "sql": sql,
                "params": (audit_name, out_stock_time, sim_number, sim_number, out_stock_time),
                "preview": f"INSERT INTO tb_simfollowinfo (...) SELECT ... '批发出库', 4, "
                           f"'{audit_name}', '{out_stock_time}', 0 FROM tb_simstatus s "
                           f"WHERE s.SIMNumber = '{sim_number}' AND NOT EXISTS (...);",
            })

        return statements

    # ------------------------------------------------------------------
    # 对外：查询待补录数据
    # ------------------------------------------------------------------
    async def query_pending(self, keywords_text: str) -> dict[str, Any]:
        """
        查询需要补录的数据（WMS 只读 + SIM 只读），返回每卡每表的缺口明细与待写值。
        """
        keywords = self.parse_keywords(keywords_text)
        if not keywords:
            raise ValueError("请输入至少一个 SIM 卡号或仓储出库单号")
        if len(keywords) > MAX_KEYWORDS:
            raise ValueError(f"单次最多支持 {MAX_KEYWORDS} 个关键词")

        try:
            return await self._query_pending_once(keywords)
        except Exception as exc:
            if not is_connection_error(exc):
                raise
            logger.warning(f"批发补录查询检测到数据库连接异常，自动重连后重试一次: {exc}")
            await self._reconnect_known_pools()
            return await self._query_pending_once(keywords)

    async def _query_pending_once(self, keywords: list[str]) -> dict[str, Any]:
        wms_result = await self.resolve_wms_sources(keywords)
        by_card = wms_result["by_card"]
        logger.info(f"批发补录查询: keywords={len(keywords)}, 命中卡={len(by_card)}, "
                    f"出库单={len(wms_result['resolved_orders'])}, 未找到={wms_result['not_found']}")

        items: list[dict[str, Any]] = []
        pending_count = 0
        skipped_count = 0

        if by_card:
            _, sim_pool = await self._ensure_sim_pool()
            async with sim_pool.acquire() as sim_conn, sim_conn.cursor(aiomysql.cursors.DictCursor) as sim_cur:
                sim_current_map = await self._fetch_sim_current(sim_cur, list(by_card.keys()))
                # 收货地址省市区编码 -> 名称（basic_district 在 SIM 卡中心库）
                region_codes: set[str] = set()
                for wms_row in by_card.values():
                    region_codes.add(wms_row.get("DeliveProCode") or "")
                    region_codes.add(wms_row.get("DeliveCityCode") or "")
                district_map = await self._fetch_district_names(sim_cur, region_codes)

            for sim_number, wms_row in by_card.items():
                sim_age = _parse_sim_age(wms_row.get("GoodsName"))
                region = self._delive_region(wms_row, district_map)
                plan = self._build_plan(
                    sim_number, wms_row, sim_current_map.get(sim_number), sim_age, **region
                )
                if plan["blocked_reason"]:
                    skipped_count += 1
                elif plan["has_pending"]:
                    pending_count += 1
                items.append({
                    "sim_number": plan["sim_number"],
                    "out_stock_no": plan["out_stock_no"],
                    "goods_name": wms_row.get("GoodsName"),
                    "cust_settle_name": wms_row.get("CustSettleName"),
                    "out_stock_time": plan["out_stock_time"],
                    "audit_name": plan["audit_name"],
                    "sim_age": sim_age,
                    "blocked_reason": plan["blocked_reason"],
                    "has_pending": plan["has_pending"],
                    "has_blocked": plan["has_blocked"],
                    "tables": plan["tables"],
                    # 省市区默认取「出库单收货地址」(tb_stockdeliveinfo)，页面可改
                    "pro_code": region["pro_code"],
                    "pro_name": region["pro_name"],
                    "city_code": region["city_code"],
                    "city_name": region["city_name"],
                    "delive_address": wms_row.get("DeliveAddress"),
                    "link_man": wms_row.get("LinkMan"),
                    "link_tel": wms_row.get("LinkTel"),
                })

        return {
            "items": items,
            "summary": {
                "keyword_count": len(keywords),
                "card_count": len(by_card),
                "pending_count": pending_count,
                "skipped_count": skipped_count,
                "not_found": wms_result["not_found"],
                "resolved_orders": wms_result["resolved_orders"],
            },
        }

    # ------------------------------------------------------------------
    # 对外：执行补录（只写 SIM 卡中心）
    # ------------------------------------------------------------------
    @staticmethod
    def _statement_table(sql: str) -> str:
        if sql.startswith("UPDATE tb_siminfo"):
            return "tb_siminfo"
        if sql.startswith("UPDATE tb_simwarehouse"):
            return "tb_simwarehouse"
        if sql.startswith("UPDATE tb_simstatus"):
            return "tb_simstatus"
        if sql.startswith("INSERT INTO tb_simfollowinfo"):
            return "tb_simfollowinfo"
        return "unknown"

    async def execute_fill(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """
        执行补录。

        Args:
            items: [{sim_number, sim_age?, pro_code?, pro_name?, city_code?, city_name?}]
                   sim_age 与省市区为页面可改项；缺省时用仓储商品名解析 / 不写。

        安全约束（AGENTS.md §5.1）：
            - 只写 SIM 卡中心；仓储中心不写。
            - 重新读取现状，空值才补、幂等；每卡一个事务。
            - 已加装 / 已注销 / SIM 中心无此卡 → 跳过。
        """
        if not items:
            raise ValueError("没有需要补录的数据")
        if len(items) > MAX_KEYWORDS:
            raise ValueError(f"单次最多支持 {MAX_KEYWORDS} 个卡")

        # 归一化入参
        fill_items: dict[str, dict[str, Any]] = {}
        for raw in items:
            sim_number = _to_str((raw or {}).get("sim_number"))
            if not sim_number or sim_number in fill_items:
                continue
            sim_age = (raw or {}).get("sim_age")
            fill_items[sim_number] = {
                "sim_number": sim_number,
                "sim_age": int(sim_age) if str(sim_age or "").strip().isdigit() else None,
                "pro_code": _to_str((raw or {}).get("pro_code")),
                "pro_name": _to_str((raw or {}).get("pro_name")),
                "city_code": _to_str((raw or {}).get("city_code")),
                "city_name": _to_str((raw or {}).get("city_name")),
            }
        if not fill_items:
            raise ValueError("没有有效的 SIM 卡号")

        try:
            return await self._execute_fill_once(fill_items)
        except Exception as exc:
            if not is_connection_error(exc):
                raise
            logger.warning(f"批发补录执行检测到数据库连接异常，自动重连后重试一次: {exc}")
            await self._reconnect_known_pools()
            return await self._execute_fill_once(fill_items)

    async def _execute_fill_once(self, fill_items: dict[str, dict[str, Any]]) -> dict[str, Any]:
        sim_numbers = list(fill_items.keys())

        # 1) 重新读取仓储中心批发出库单据（只读）
        wms_result = await self.resolve_wms_sources(sim_numbers)
        by_card = wms_result["by_card"]

        # 2) 重新读取 SIM 卡中心现状（只读）+ 收货地址省市区名称解析
        sim_current_map: dict[str, dict] = {}
        district_map: dict[str, str] = {}
        _, sim_pool = await self._ensure_sim_pool()
        async with sim_pool.acquire() as sim_conn, sim_conn.cursor(aiomysql.cursors.DictCursor) as sim_cur:
            sim_current_map = await self._fetch_sim_current(sim_cur, sim_numbers)
            region_codes: set[str] = set()
            for wms_row in by_card.values():
                region_codes.add(wms_row.get("DeliveProCode") or "")
                region_codes.add(wms_row.get("DeliveCityCode") or "")
            district_map = await self._fetch_district_names(sim_cur, region_codes)

        results: list[dict[str, Any]] = []
        updated_by_table: dict[str, int] = {}

        for sim_number, override in fill_items.items():
            wms_row = by_card.get(sim_number)
            if wms_row is None:
                results.append({"sim_number": sim_number, "success": False,
                                "skipped_reason": "仓储中心未找到该卡的批发出库(OT3)记录",
                                "updated_by_table": {}})
                continue

            sim_age = override["sim_age"]
            if sim_age is None:
                sim_age = _parse_sim_age(wms_row.get("GoodsName"))

            # 省市区：默认取出库单收货地址，页面提交值优先（页面可改）
            delive = self._delive_region(wms_row, district_map)
            eff_pro_code = override["pro_code"] or delive["pro_code"]
            eff_pro_name = override["pro_name"] or delive["pro_name"]
            eff_city_code = override["city_code"] or delive["city_code"]
            eff_city_name = override["city_name"] or delive["city_name"]

            plan = self._build_plan(
                sim_number, wms_row, sim_current_map.get(sim_number), sim_age,
                pro_code=eff_pro_code, pro_name=eff_pro_name,
                city_code=eff_city_code, city_name=eff_city_name,
            )

            if plan["blocked_reason"]:
                results.append({"sim_number": sim_number, "success": False,
                                "skipped_reason": plan["blocked_reason"], "updated_by_table": {}})
                continue
            if not plan["has_pending"]:
                results.append({"sim_number": sim_number, "success": False,
                                "skipped_reason": "数据已同步，无需补录", "updated_by_table": {}})
                continue

            # 阻断项：需要卡年限但解析不到 / 需要省市区但未填写
            blocked_msgs = []
            tables = plan["tables"]
            if tables.get("tb_siminfo", {}).get("blocked") or tables.get("tb_simstatus", {}).get("blocked"):
                blocked_msgs.append("卡年限无法从商品名解析，请在页面填写「卡年限」")
            if tables.get("tb_simwarehouse", {}).get("blocked"):
                blocked_msgs.append("出库单收货地址无省市区且页面未填写，请手动填写省/市编码与名称")
            if blocked_msgs:
                results.append({"sim_number": sim_number, "success": False,
                                "skipped_reason": "；".join(blocked_msgs), "updated_by_table": {}})
                continue

            statements = self._build_card_statements(
                plan,
                pro_code=eff_pro_code, pro_name=eff_pro_name,
                city_code=eff_city_code, city_name=eff_city_name,
            )
            if not statements:
                results.append({"sim_number": sim_number, "success": False,
                                "skipped_reason": "无可执行语句", "updated_by_table": {}})
                continue

            # 3) 每卡一个事务，只写 SIM 卡中心
            card_updated: dict[str, int] = {}
            try:
                async with sim_pool.acquire() as conn, conn.cursor() as cur:
                    await conn.begin()
                    try:
                        for stmt in statements:
                            await cur.execute(stmt["sql"], stmt["params"])
                            table = self._statement_table(stmt["sql"])
                            affected = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
                            card_updated[table] = card_updated.get(table, 0) + affected
                        await conn.commit()
                    except Exception:
                        await conn.rollback()
                        raise
                for table, count in card_updated.items():
                    updated_by_table[table] = updated_by_table.get(table, 0) + count
                results.append({"sim_number": sim_number, "success": True,
                                "skipped_reason": None, "updated_by_table": card_updated,
                                "sql_preview": [s["preview"] for s in statements]})
                logger.info(f"批发补录成功: sim_number={sim_number}, updated={card_updated}")
            except Exception as exc:
                logger.error(f"批发补录失败: sim_number={sim_number}, error={exc}", exc_info=True)
                results.append({"sim_number": sim_number, "success": False,
                                "skipped_reason": None, "updated_by_table": {},
                                "error": str(exc)})

        success_count = sum(1 for r in results if r["success"])
        return {
            "results": results,
            "summary": {
                "total": len(results),
                "success_count": success_count,
                "failed_count": sum(1 for r in results if not r["success"] and r.get("error")),
                "skipped_count": sum(1 for r in results if not r["success"] and not r.get("error")),
                "updated_by_table": updated_by_table,
                "not_found": wms_result["not_found"],
            },
        }


sim_fill_service = SIMFillService()
