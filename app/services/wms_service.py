import logging
from typing import Callable

import aiomysql

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

# 仓储中心固定连接的Id（延迟获取，避免模块加载时Tortoise未初始化）
_wms_conn_id = None

async def _get_conn_id():
    global _wms_conn_id
    if _wms_conn_id is None:
        _wms_conn_id = await settings.WMS_CONN_ID()
    return _wms_conn_id


class WmsService:
    """仓储中心业务服务"""

    # ========================================================================
    # 单据查询表配置 —— 后续新增表类型只需在此处添加即可
    # 格式: (主表名, 历史表名, 单据号字段名, doc_type标识)
    # ========================================================================
    STOCK_TABLES: list[tuple[str, str, str, str]] = [
        # (主表, 历史表, No字段, doc_type)
        ("tb_instockinfo",   "tb_instockinfohis",   "InStockNo",  "instock"),
        ("tb_outstockinfo",  "tb_outstockinfohis",  "OutStockNo", "outstock"),
        # TODO: 预留 —— 内部交易单（按实际表名取消注释并修改）
        # ("tb_simtransinfo", "tb_simtransinfohis", "SimTransNo", "simtrans"),
        # TODO: 预留 —— 销售退货单（按实际表名取消注释并修改）
        # ("tb_sale_return_info", "tb_sale_return_info_his", "SaleReturnNo", "sale_return"),
        # TODO: 预留 —— 采购退货单（按实际表名取消注释并修改）
        # ("tb_purchase_return_info", "tb_purchase_return_info_his", "PurchaseReturnNo", "purchase_return"),
    ]

    # ------------------------------------------------------------------
    # 价格查询表配置：主表(进行中) 与 历史表(已完成) 均支持查询与修改
    # 格式: (主表, 主表明细, 历史表, 历史明细, No字段, 关联字段, 价格字段, 数量字段, doc_type)
    # ------------------------------------------------------------------
    PRICE_TABLES: list[tuple[str, str, str, str, str, str, str, str, str]] = [
        (
            "tb_instockinfo", "tb_instockdetail", "tb_instockinfohis", "tb_instockdetailhis",
            "InStockNo", "InStockId", "InStockPrice", "InStockedNum", "instock",
        ),
        (
            "tb_outstockinfo", "tb_outstockdetail", "tb_outstockinfohis", "tb_outstockdetailhis",
            "OutStockNo", "OutStockId", "OutStockPrice", "OutStockedNum", "outstock",
        ),
    ]

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        await db_pool.ensure_pool(await _get_conn_id())

    # ------------------------------------------------------------------
    # 核心查询方法：统一的单据查找逻辑
    # ------------------------------------------------------------------
    async def _find_stock_doc(
        self,
        cur,
        stock_no: str,
        select_cols: str = "Id AS stock_id, Deleted AS deleted, DeletedById",
        *,
        filter_cb: Callable | None = None,
    ) -> tuple | None:
        """
        在所有配置的表中查找单据（先主表后历史表），返回首条命中的记录。

        Args:
            cur: 数据库游标
            stock_no: 输入值（可能是纯数字Id或单据编码）
            select_cols: SELECT的字段列表
            filter_cb: 可选的行级过滤器 callable(row) -> bool，用于跳过不符合条件的行

        Returns:
            命中的 (row, main_table, no_field, doc_type) 元组，或 None
        """
        is_numeric = stock_no.isdigit()
        numeric_id = int(stock_no) if is_numeric else None

        for main_table, his_table, no_field, doc_type in self.STOCK_TABLES:
            # 查询顺序：主表(Id) → 主表(No) → 历史表(Id) → 历史表(No)
            search_targets = [
                (main_table, "Id",      numeric_id if is_numeric else stock_no),
                (main_table, no_field,  stock_no),
                (his_table,   "Id",      numeric_id if is_numeric else stock_no),
                (his_table,   no_field,  stock_no),
            ]
            for table, field, value in search_targets:
                sql = f"SELECT {select_cols}, '{doc_type}' AS doc_type, " \
                      f"{'main' if table == main_table else 'his'} AS table_type " \
                      f"FROM {table} WHERE {field}=%s LIMIT 1"
                try:
                    await cur.execute(sql, (value,))
                    row = await cur.fetchone()
                    if row:
                        if filter_cb is None or filter_cb(row):
                            logger.debug(
                                f"[validate_stock] 命中: stock_no={stock_no} → "
                                f"table={table}, field={field}, id={row[0]}, doc_type={doc_type}"
                            )
                            return row
                except Exception as e:
                    logger.warning(f"[validate_stock] 查询异常 table={table} field={field} value={value}: {e}")
                    continue

        logger.info(f"[validate_stock] 未找到单据: stock_no='{stock_no}', is_numeric={is_numeric}")
        return None

    async def _find_all_stock_docs(
        self,
        cur,
        stock_no: str,
        select_cols: str = "Id",
    ) -> list[tuple]:
        """
        在所有配置的表中查找单据的所有匹配记录（用于批量删除）。

        Returns:
            匹配的 Id 列表
        """
        is_numeric = stock_no.isdigit()
        numeric_id = int(stock_no) if is_numeric else None
        stock_ids: list[tuple] = []

        for main_table, his_table, no_field, doc_type in self.STOCK_TABLES:
            search_targets = [
                (main_table, "Id",      numeric_id if is_numeric else stock_no),
                (main_table, no_field,  stock_no),
                (his_table,   "Id",      numeric_id if is_numeric else stock_no),
                (his_table,   no_field,  stock_no),
            ]
            for table, field, value in search_targets:
                sql = f"SELECT {select_cols} FROM {table} WHERE {field}=%s"
                try:
                    await cur.execute(sql, (value,))
                    rows = await cur.fetchall()
                    for row in rows:
                        stock_ids.append(row)
                        logger.debug(
                            f"[find_all] 命中: stock_no={stock_no} → "
                            f"table={table}, field={field}, id={row[0]}"
                        )
                except Exception as e:
                    logger.warning(f"[find_all] 查询异常 table={table} field={field} value={value}: {e}")
                    continue

        return stock_ids

    async def validate_stock(self, stock_nos: list[str], validate_type: str, operator_id: str = None) -> dict:
        """
        验证单据状态，支持传入单据编码或数字Id
        同时查询所有配置的主表和历史表（入库、出库、内部交易、退货等）

        Args:
            stock_nos: 单据编码或数字Id列表
            validate_type: 验证类型 (logical_delete, physical_delete, restore)
            operator_id: 删除人Id（恢复时需要验证）

        Returns:
            验证结果字典
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        found_docs = []
        not_found_docs = []
        invalid_docs = []  # 状态不符合的单据

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn, conn.cursor() as cur:
                for stock_no in stock_nos:
                    # 使用统一查询方法在所有配置的表中查找
                    result = await self._find_stock_doc(
                        cur, stock_no,
                        select_cols="Id AS stock_id, Deleted AS deleted, DeletedById",
                    )

                    if not result:
                        not_found_docs.append(stock_no)
                    else:
                        stock_id, deleted, deleted_by_id, doc_type, table_type = result
                        doc_info = {
                            "stock_id": stock_id,
                            "stock_no": stock_no,
                            "deleted": deleted,
                            "deleted_by_id": deleted_by_id,
                            "doc_type": doc_type,
                            "table_type": table_type
                        }

                        if validate_type == "logical_delete":
                            if deleted == 1:
                                invalid_docs.append({
                                    **doc_info,
                                    "reason": "单据已被逻辑删除，不能再次删除"
                                })
                            else:
                                found_docs.append(doc_info)

                        elif validate_type == "physical_delete":
                            found_docs.append(doc_info)

                        elif validate_type == "restore":
                            if deleted == 0:
                                invalid_docs.append({
                                    **doc_info,
                                    "reason": "单据未被逻辑删除，无需恢复"
                                })
                            elif operator_id and deleted_by_id != operator_id:
                                invalid_docs.append({
                                    **doc_info,
                                    "reason": f"删除人不匹配，期望 {operator_id}，实际 {deleted_by_id}"
                                })
                            else:
                                found_docs.append(doc_info)
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(not_found_docs) == 0 and len(invalid_docs) == 0,
            "total_count": len(stock_nos),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "invalid_count": len(invalid_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "invalid_docs": invalid_docs,
            "message": self._build_validation_message(
                len(found_docs), len(not_found_docs), len(invalid_docs), validate_type
            )
        }

    def _build_validation_message(
        self, found_count: int, not_found_count: int, invalid_count: int, validate_type: str
    ) -> str:
        """构建验证消息"""
        type_names = {
            "logical_delete": "逻辑删除",
            "physical_delete": "物理删除",
            "restore": "恢复"
        }
        type_name = type_names.get(validate_type, "操作")

        parts = []
        if found_count > 0:
            parts.append(f"可{type_name} {found_count} 条")
        if not_found_count > 0:
            parts.append(f"{not_found_count} 条单据不存在")
        if invalid_count > 0:
            parts.append(f"{invalid_count} 条单据状态不符合")

        return "，".join(parts) if parts else f"所有单据均可{type_name}"

    async def fetch_stock_ids_by_nos(self, stock_nos: list[str]) -> dict[str, int]:
        """根据单据编码或数字Id获取对应的stock_id，查询所有配置的主表和历史表"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        result: dict[str, int] = {}
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for stock_no in stock_nos:
                        # 使用统一查询方法
                        row = await self._find_stock_doc(cur, stock_no, select_cols="Id AS stock_id")
                        if row:
                            result[stock_no] = row[0]
        else:
            raise ValueError("不支持的连接池类型")

        return result

    async def delete_logical_batch(self, stock_nos: list[str], operator_id: str) -> tuple[int, list[str]]:
        """批量逻辑删除单据，查询所有配置的主表和历史表中的记录"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: list[str] = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn, conn.cursor() as cur:
                for stock_no in stock_nos:
                    try:
                        # 使用统一查询方法查找所有匹配记录（含扩展表）
                        all_rows = await self._find_all_stock_docs(cur, stock_no, select_cols="Id")

                        if not all_rows:
                            failed.append(stock_no)
                            continue

                        # 对每条记录都调用存储过程删除
                        for row in all_rows:
                            stock_id = row[0]
                            await cur.execute("CALL proc_DeleteStockInfoById(%s, %s)", (stock_id, operator_id))

                        success += 1
                    except Exception as e:
                        logger.error(f"[delete_logical_batch] 删除失败 stock_no={stock_no}: {e}")
                        failed.append(stock_no)
        else:
            raise ValueError("不支持的连接池类型")

        return success, failed

    async def delete_physical_batch(self, stock_nos: list[str], operator_id: str) -> tuple[int, list[str]]:
        """批量物理删除单据，查询所有配置的主表和历史表中的记录"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: list[str] = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn, conn.cursor() as cur:
                for stock_no in stock_nos:
                    try:
                        # 使用统一查询方法查找所有匹配记录（含扩展表）
                        all_rows = await self._find_all_stock_docs(cur, stock_no, select_cols="Id")

                        if not all_rows:
                            failed.append(stock_no)
                            continue

                        # 对每条记录都调用存储过程删除
                        for row in all_rows:
                            stock_id = row[0]
                            await cur.execute("CALL proc_TruncateStockInfoById(%s)", (stock_id,))

                        success += 1
                    except Exception as e:
                        logger.error(f"[delete_physical_batch] 删除失败 stock_no={stock_no}: {e}")
                        failed.append(stock_no)
        else:
            raise ValueError("不支持的连接池类型")

        return success, failed

    async def restore_logical(self, stock_no: str, operator_id: str) -> bool:
        """恢复逻辑删除的单据，支持传入编码或Id，查询所有配置的主表和历史表"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        stock_id = None
        source_table = None

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 在所有配置的表中查找已删除的单据（Deleted=1），先查his表再查主表
                    is_numeric = stock_no.isdigit()
                    numeric_id = int(stock_no) if is_numeric else None

                    for main_table, his_table, no_field, doc_type in self.STOCK_TABLES:
                        search_targets = [
                            (his_table,   "Id",      numeric_id if is_numeric else stock_no),
                            (his_table,   no_field,  stock_no),
                            (main_table,  "Id",      numeric_id if is_numeric else stock_no),
                            (main_table,  no_field,  stock_no),
                        ]
                        for table, field, value in search_targets:
                            await cur.execute(
                                f"SELECT Id, DeletedById FROM {table} WHERE {field}=%s AND Deleted=1 LIMIT 1",
                                (value,),
                            )
                            row = await cur.fetchone()
                            if row:
                                stock_id = row[0]
                                source_table = table
                                logger.info(f"[restore_logical] 找到已删除单据: stock_no={stock_no} → table={table}, id={stock_id}")
                                break
                        if stock_id:
                            break

                    if not stock_id:
                        raise ValueError(f"未找到已删除的单据 {stock_no}")

                    # 调用存储过程恢复单据
                    await cur.execute("CALL proc_ReDeleteStockInfoById(%s, %s)", (stock_id, operator_id))
                    return True
        else:
            raise ValueError("不支持的连接池类型")

    async def _fetch_owing_status(self, cur, detail_id: str) -> dict:
        """
        查询明细对应的应付单对账状态（主表 + 历史表），判断是否允许修改价格。
        判断逻辑与存储过程 proc_StockPriceChange 保持一致：
        若存在满足以下任一条件的应付记录，则视为"已对账/部分对账"，不允许修改：
          ReconcStatus IN (1,2)   —— 部分对账 / 已对账
          OwingStatus  IN (2,3,4) —— 申请中 / 部分付款 / 已付款
          UnReconcNum <> StockNum —— 待对账数量不等于数量（已发生部分对账）

        Returns:
            {"can_modify": bool, "reconc_status": int|None, "owing_status": int|None,
             "stock_no": str, "material_name": str, "reason": str}
        """
        for table_name, label in (("tb_owinginfo", "应付单"), ("tb_owinginfohis", "应付单历史")):
            sql = f"""
                SELECT StockNo, MaterialName, ReconcStatus, OwingStatus, UnReconcNum, StockNum
                FROM {table_name}
                WHERE StockDetailId=%s AND Deleted=0
                LIMIT 1
            """
            await cur.execute(sql, (detail_id,))
            row = await cur.fetchone()
            if row:
                stock_no, material_name, reconc_status, owing_status, unreconc_num, stock_num = row
                if (reconc_status in (1, 2)
                        or owing_status in (2, 3, 4)
                        or (unreconc_num is not None and stock_num is not None and float(unreconc_num) != float(stock_num))):
                    return {
                        "can_modify": False,
                        "reconc_status": reconc_status,
                        "owing_status": owing_status,
                        "stock_no": stock_no,
                        "material_name": material_name,
                        "reason": f"单据「{stock_no}」的物料「{material_name}」已对账或部分对账，不再允许价格调整",
                    }
                # 存在应付记录但未对账，视为允许修改
                return {
                    "can_modify": True,
                    "reconc_status": reconc_status,
                    "owing_status": owing_status,
                    "stock_no": stock_no,
                    "material_name": material_name,
                    "reason": "",
                }

        # 无应付单记录，允许修改
        return {
            "can_modify": True,
            "reconc_status": None,
            "owing_status": None,
            "stock_no": "",
            "material_name": "",
            "reason": "",
        }

    async def query_price(self, stock_code: str, material_name: str, new_price: str) -> list[dict]:
        """
        查询价格信息，支持入库单/出库单，以及进行中(主表)/已完成(历史表) 四类单据。
        每行结果附带对账状态与是否可修改标记。

        Args:
            stock_code: 单据编码（入库单或出库单）
            material_name: 物料名称
            new_price: 修改后价格

        Returns:
            查询结果列表，每项包含 detail_id / material_name / original_price / num /
            doc_type / table_type / stock_no / new_price / can_modify / 对账状态等
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        results = []
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn, conn.cursor() as cur:
                # 同一明细 Id 可能同时存在于主表(进行中)和历史表(已完成)，
                # 存储过程会同时更新两张表，故按 detail_id 去重，主表优先。
                seen_detail_ids: set[str] = set()

                for (main_table, main_detail, his_table, his_detail,
                     no_field, fk_field, price_field, num_field, doc_type) in self.PRICE_TABLES:

                    # 依次查询：主表(进行中) → 历史表(已完成)
                    for table, detail, table_type in ((main_table, main_detail, "main"),
                                                      (his_table, his_detail, "his")):
                        sql = f"""
                            SELECT b.Id, b.MaterialName, b.{price_field}, b.{num_field},
                                   a.{no_field}, '{doc_type}', '{table_type}'
                            FROM {table} a
                            JOIN {detail} b
                              ON b.{fk_field}=a.Id
                              AND b.MaterialName LIKE %s
                              AND b.Deleted=0
                            WHERE a.{no_field}=%s
                              AND a.Deleted=0
                        """
                        await cur.execute(sql, (f"%{material_name}%", stock_code))
                        rows = await cur.fetchall()
                        for row in rows:
                            detail_id = str(row[0])
                            if detail_id in seen_detail_ids:
                                continue
                            seen_detail_ids.add(detail_id)
                            owing = await self._fetch_owing_status(cur, detail_id)
                            results.append({
                                "detail_id": detail_id,
                                "material_name": str(row[1]),
                                "original_price": str(row[2]),
                                "num": str(row[3]) if row[3] is not None else "0",
                                "instocked_num": str(row[3]) if row[3] is not None else "0",
                                "stock_no": str(row[4]) if row[4] else stock_code,
                                "doc_type": row[5],
                                "table_type": row[6],
                                "new_price": new_price,
                                "can_modify": owing["can_modify"],
                                "reconc_status": owing["reconc_status"],
                                "owing_status": owing["owing_status"],
                                "reason": owing["reason"],
                            })
        else:
            raise ValueError("不支持的连接池类型")

        return results

    async def validate_owing_status(self, stock_id: str) -> dict:
        """
        验证应付单是否对账（stock_id 实为出入库明细 Id，对应 tb_owinginfo.StockDetailId）。
        判断逻辑与存储过程 proc_StockPriceChange 一致。
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn, conn.cursor() as cur:
                owing = await self._fetch_owing_status(cur, stock_id)
                if owing["can_modify"]:
                    return {
                        "success": True,
                        "message": "应付单未对账，允许修改",
                        "reconc_status": owing["reconc_status"],
                        "owing_status": owing["owing_status"],
                    }
                return {
                    "success": False,
                    "message": owing["reason"] or "应付单已对账，不允许修改价格",
                    "reconc_status": owing["reconc_status"],
                    "owing_status": owing["owing_status"],
                }
        else:
            raise ValueError("不支持的连接池类型")

    async def modify_price(self, detail_id: str, new_price: str) -> dict:
        """
        修改价格：调用存储过程 proc_StockPriceChange(InDetailId, NewPrice)。
        存储过程返回结果集 (Result AS ErType, sys_ErrMessage AS ErMessage)，
        其中 Result=-1 表示单据已对账或部分对账，不允许修改。

        Args:
            detail_id: 明细Id（入库明细或出库明细）
            new_price: 修改后价格

        Returns:
            {"success": bool, "message": str}
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn, conn.cursor() as cur:
                await cur.execute("CALL proc_StockPriceChange(%s, %s)", (detail_id, new_price))

                # 存储过程末尾 SELECT Result AS ErType, sys_ErrMessage AS ErMessage
                row = await cur.fetchone()
                if row:
                    result_code = row[0]
                    err_message = row[1] if len(row) > 1 and row[1] else ""
                    if result_code is not None and int(result_code) == -1:
                        return {
                            "success": False,
                            "message": err_message or "单据已对账或部分对账，不允许修改价格",
                        }
                return {"success": True, "message": "价格修改成功"}
        else:
            raise ValueError("不支持的连接池类型")

    async def query_stock_status(self, stock_nos: list[str]) -> dict:
        """查询单据状态信息，返回Id、单号、AuditTime、Deleted、DeletedById、DeletedAt，并关联OA获取删除人姓名
        查询所有配置的主表和历史表（入库、出库及扩展表）
        """
        from app.services.user_service import user_service

        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for stock_no in stock_nos:
                        is_numeric = stock_no.isdigit()
                        numeric_id = int(stock_no) if is_numeric else None

                        result = None
                        for main_table, his_table, no_field, doc_type in self.STOCK_TABLES:
                            # 根据doc_type决定SELECT中的单据号字段
                            select_no_field = no_field

                            search_targets = [
                                (main_table, "Id",      numeric_id if is_numeric else stock_no),
                                (main_table, no_field,  stock_no),
                                (his_table,   "Id",      numeric_id if is_numeric else stock_no),
                                (his_table,   no_field,  stock_no),
                            ]
                            for table, field, value in search_targets:
                                sql = f"""SELECT Id, {select_no_field}, AuditTime, Deleted, DeletedById, DeletedAt,
                                                 '{doc_type}' AS doc_type
                                          FROM {table} WHERE {field}=%s LIMIT 1"""
                                try:
                                    await cur.execute(sql, (value,))
                                    row = await cur.fetchone()
                                    if row:
                                        result = row
                                        logger.debug(f"[query_stock_status] 命中: stock_no={stock_no} → table={table}, id={row[0]}")
                                        break
                                except Exception as e:
                                    logger.warning(f"[query_stock_status] 查询异常 table={table}: {e}")
                                    continue
                            if result:
                                break

                        if not result:
                            not_found_docs.append(stock_no)
                        else:
                            doc_type = result[6]
                            stock_no_actual = result[1]
                            found_docs.append({
                                "id": str(result[0]),
                                "stock_no": str(stock_no_actual) if stock_no_actual else stock_no,
                                "doc_type": doc_type,
                                "audit_time": str(result[2]) if result[2] else "",
                                "deleted": result[3],
                                "deleted_by_id": str(result[4]) if result[4] else "",
                                "deleted_at": str(result[5]) if result[5] else "",
                            })
        else:
            raise ValueError("不支持的连接池类型")

        deleted_by_ids = [doc["deleted_by_id"] for doc in found_docs if doc["deleted_by_id"]]
        user_map = {}
        if deleted_by_ids:
            try:
                user_map = await user_service.batch_get_by_user_center_ids(deleted_by_ids)
            except Exception as e:
                logger.warning(f"获取删除人信息失败: {e}")

        # 降级：OA 查不到的 ID，尝试从本库 user 表查询 DisplayName
        unmatched_ids = [did for did in deleted_by_ids if did not in user_map]
        if unmatched_ids:
            try:
                local_map = await user_service.get_local_user_display_names(unmatched_ids)
                for did, display_name in local_map.items():
                    user_map[did] = {"user_name": display_name, "code": "", "user_center_user_id": did}
            except Exception as e:
                logger.warning(f"本库用户查询降级失败: {e}")

        for doc in found_docs:
            u = user_map.get(doc["deleted_by_id"], {})
            doc["deleted_by_name"] = u.get("user_name", "")
            doc["deleted_by_code"] = u.get("code", "")

        parts = []
        if found_docs:
            parts.append(f"找到 {len(found_docs)} 条")
        if not_found_docs:
            parts.append(f"{len(not_found_docs)} 条不存在")
        message = "，".join(parts) if parts else "查询完成"

        return {
            "success": len(not_found_docs) == 0,
            "total_count": len(stock_nos),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "message": message,
        }


    async def query_owing_status(self, out_stock_no: str = "", stock_id: str = "") -> dict:
        """
        查询出库单应收状态，先查tb_outstockinfo，查不到再查tb_outstockinfohis

        Args:
            out_stock_no: 出库单号
            stock_id: 出库单ID

        Returns:
            查询结果字典，包含数据来源表名
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        if not out_stock_no and not stock_id:
            return {"success": False, "message": "请输入出库单号或ID", "data": None}

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 构建查询条件
                    condition_parts = []
                    params = []
                    if out_stock_no:
                        condition_parts.append("OutStockNo=%s")
                        params.append(out_stock_no)
                    if stock_id:
                        if condition_parts:
                            condition_parts.append("OR")
                        condition_parts.append("Id=%s")
                        params.append(stock_id)
                    where_clause = ' '.join(condition_parts)

                    # 先查tb_outstockinfo，查不到再查tb_outstockinfohis
                    tables = [("tb_outstockinfo", "main"), ("tb_outstockinfohis", "his")]
                    row = None
                    source_table = None

                    for table_name, table_type in tables:
                        sql = f"""
                            SELECT Id, OutStockNo,
                                   fn_GetStockTypeById(OutStockType) AS OutStockType,
                                   WarehouseName, ToWarehouseName,
                                   AuditTime, IsReceive
                            FROM {table_name}
                            WHERE ({where_clause}) AND Deleted=0
                            LIMIT 1
                        """
                        await cur.execute(sql, params)
                        row = await cur.fetchone()
                        if row:
                            source_table = table_type
                            break

                    if not row:
                        return {"success": False, "message": "未找到该出库单", "data": None}

                    return {
                        "success": True,
                        "message": "查询成功",
                        "data": {
                            "id": str(row[0]),
                            "out_stock_no": str(row[1]) if row[1] else "",
                            "out_stock_type": str(row[2]) if row[2] else "",
                            "warehouse_name": str(row[3]) if row[3] else "",
                            "to_warehouse_name": str(row[4]) if row[4] else "",
                            "audit_time": str(row[5]) if row[5] else "",
                            "is_receive": row[6] if row[6] is not None else 0,
                            "source_table": source_table,
                        }
                    }
        else:
            raise ValueError("不支持的连接池类型")

    async def update_receive_status(self, stock_id: str, is_receive: int, operator_id: str, source_table: str = "main") -> dict:
        """
        修改出库单应收状态

        Args:
            stock_id: 出库单ID
            is_receive: 应收状态: 0-未收, 1-已收
            operator_id: 修改人Id
            source_table: 数据来源表 main-主表, his-历史表

        Returns:
            修改结果字典
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        # 根据来源表选择对应的表名
        table_name = "tb_outstockinfo" if source_table == "main" else "tb_outstockinfohis"

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 更新IsReceive字段，同时记录修改人和更新时间
                    sql = f"""
                        UPDATE {table_name}
                        SET IsReceive=%s,
                            UpdatedById=%s,
                            UpdatedAt=NOW()
                        WHERE Id=%s AND Deleted=0
                    """
                    await cur.execute(sql, (is_receive, operator_id, stock_id))

                    if cur.rowcount > 0:
                        return {"success": True, "message": "修改成功"}
                    else:
                        return {"success": False, "message": "未找到该出库单或无需修改"}
        else:
            raise ValueError("不支持的连接池类型")


wms_service = WmsService()
