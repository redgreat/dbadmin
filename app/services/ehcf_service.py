import logging
from typing import Dict, List, Tuple

import aiomysql

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

# 单据来源仅允许修改充电桩单据（壹好车服服务商编码）
ALLOWED_SERVICE_PROVIDER_CODE = "1067"

# 附件类型枚举（tb_workresourceinfo.SourceType）
RESOURCE_SOURCE_TYPE_MAP = {
    1: "设备参照图片",
    2: "AFC主单附件",
    3: "AFC费用附件",
    4: "AFC备案附件",
    5: "主单附件",
    6: "收件附件",
    7: "VHS备案附件",
    8: "归还附件",
    9: "二手车检测报告",
    10: "AFC路况异常附件",
    11: "在线支付费用附件",
    12: "VHS服务凭证",
    13: "退单凭证",
    14: "回款提报还款凭证",
    15: "回款提报谈判记录",
    16: "回款提报其他",
    17: "VHS邮寄凭证",
    18: "金融预约附件",
    19: "金融备案视频附件",
    20: "谈判记录附件",
    21: "营业执照",
    22: "相关资质证书",
    23: "车务ETC附件",
    24: "通用异常签到附件",
    25: "车管工单附件",
    26: "AFC住宿打卡附件",
    27: "VHS请求关闭退单凭证",
    28: "下单附件",
    29: "科目附件",
    30: "服务结果附件",
    31: "异常反馈附件",
    32: "勘测附件",
    33: "安装附件",
    34: "增项费附件",
    35: "增项费付款附件",
    36: "勘测费付款附件",
    37: "AFC二访附件",
    38: "车务补录附件",
    39: "车务工单PDF报告",
}

# tb_remarkinfo.Type：附件删除/恢复备注
REMARK_TYPE_RESOURCE_DELETE = 13
REMARK_TYPE_RESOURCE_RESTORE = 14

_ehcf_conn_id = None
_order_conn_id = None


async def _get_conn_id():
    global _ehcf_conn_id
    if _ehcf_conn_id is None:
        _ehcf_conn_id = await settings.EHCF_CONN_ID()
    return _ehcf_conn_id


async def _get_order_conn_id():
    global _order_conn_id
    if _order_conn_id is None:
        _order_conn_id = await settings.ORDER_CONN_ID()
    return _order_conn_id


class EhcfService:
    """壹好车服业务服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        await db_pool.ensure_pool(await _get_conn_id())

    async def _get_order_pool(self):
        """获取订单中心数据库连接池（OE/OI 序列与订单编码均在订单中心库）"""
        await db_pool.ensure_pool(await _get_order_conn_id())
        pool = db_pool.get_pool(await _get_order_conn_id())
        if pool is None:
            raise ValueError("订单中心连接池不存在")
        return pool

    @staticmethod
    async def _next_val(cur, seq_no: str) -> str:
        """在指定连接上调用 fn_nextval 生成序列值（序列均在订单中心库）"""
        await cur.execute("SELECT fn_nextval(%s);", (seq_no,))
        row = await cur.fetchone()
        return str(row[0]) if row and row[0] else ""

    async def query_workorder(self, keyword: str) -> Dict:
        """查询工单基础信息，支持AppCode或Id"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = """
                        SELECT a.AppCode, a.Id, a.OrderType,
                               fn_GetOrderTypeByCode(a.OrderType) AS OrderTypeName,
                               fn_GetStatusTypeByCode(a.Id) AS StatusTypeName,
                               a.WorkStatus,
                               fn_GetCloseStatusNameByOrderId(a.Id) AS CloseStatusName,
                               a.CustomerName, b.VinNumber
                        FROM tb_workorderinfo a
                        LEFT JOIN tb_workcarinfo b ON b.WorkOrderId = a.Id
                        WHERE (a.Id=%s OR a.AppCode=%s) AND a.Deleted=0
                        LIMIT 1
                    """
                    await cur.execute(sql, (keyword, keyword))
                    row = await cur.fetchone()
                    if not row:
                        return {"found": False, "message": f"未找到工单: {keyword}"}

                    return {
                        "found": True,
                        "workorder": {
                            "app_code": row[0] if row[0] else "",
                            "id": str(row[1]) if row[1] else "",
                            "order_type": row[2] if row[2] else "",
                            "order_type_name": row[3] if row[3] else "",
                            "status_type_name": row[4] if row[4] else "",
                            "work_status": row[5] if row[5] else "",
                            "close_status_name": row[6] if row[6] else "",
                            "customer_name": row[7] if row[7] else "",
                            "vin_number": row[8] if row[8] else "",
                        },
                        "message": "查询成功",
                    }
        else:
            raise ValueError("不支持的连接池类型")

    async def query_detail_ids(self, workorder_id: str) -> Dict:
        """查询需要修复的明细Id"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        results = {"goods_detail": [], "goods_detail_other": [], "fix_item_detail": []}

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # tb_workgoodsdetail
                    await cur.execute(
                        "SELECT Id, OrderDetailId FROM tb_workgoodsdetail WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    for row in await cur.fetchall():
                        results["goods_detail"].append({
                            "id": str(row[0]), "order_detail_id": str(row[1]) if row[1] else ""
                        })

                    # tb_workgoodsdetail_other
                    await cur.execute(
                        "SELECT Id, OrderDetailId FROM tb_workgoodsdetail_other WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    for row in await cur.fetchall():
                        results["goods_detail_other"].append({
                            "id": str(row[0]), "order_detail_id": str(row[1]) if row[1] else ""
                        })

                    # tb_workfixitemdetail
                    await cur.execute(
                        "SELECT Id, NewOrderDetailId FROM tb_workfixitemdetail WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    for row in await cur.fetchall():
                        results["fix_item_detail"].append({
                            "id": str(row[0]), "order_detail_id": str(row[1]) if row[1] else ""
                        })
        else:
            raise ValueError("不支持的连接池类型")

        total = sum(len(v) for v in results.values())
        return {
            "total": total,
            "details": results,
            "message": f"共查到 {total} 条明细记录",
        }

    async def fix_order_detail_ids(self, workorder_id: str) -> Dict:
        """修复订单明细Id（每行明细生成一个新的OE编号）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        results = {"updated": [], "failed": []}

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 处理三张表
                    tables = [
                        ("tb_workgoodsdetail", "WorkOrderId"),
                        ("tb_workgoodsdetail_other", "WorkOrderId"),
                        ("tb_workfixitemdetail", "WorkOrderId"),
                    ]

                    # 收集所有明细行，按原始 OrderDetailId 分组
                    all_rows = []
                    for table, where_col in tables:
                        detail_field = "NewOrderDetailId" if table == "tb_workfixitemdetail" else "OrderDetailId"
                        await cur.execute(
                            f"SELECT Id, {detail_field} FROM {table} WHERE {where_col}=%s",
                            (workorder_id,),
                        )
                        for row in await cur.fetchall():
                            all_rows.append({
                                "table": table,
                                "detail_field": detail_field,
                                "row_id": row[0],
                                "old_detail_id": str(row[1]) if row[1] else "",
                            })

                    # 为每行明细生成新的 OE 编号（每行一个，OE 序列在订单中心库）
                    order_pool = await self._get_order_pool()
                    if isinstance(order_pool, aiomysql.Pool):
                        async with order_pool.acquire() as order_conn:
                            async with order_conn.cursor() as order_cur:
                                for r in all_rows:
                                    new_id = await self._next_val(order_cur, 'OE')
                                    if not new_id:
                                        return {"success": False, "message": "生成OE编号失败"}
                                    r["new_id"] = new_id
                    else:
                        raise ValueError("不支持的连接池类型")

                    # 更新所有明细行
                    for r in all_rows:
                        new_oe_id = r["new_id"]
                        try:
                            await cur.execute(
                                f"UPDATE {r['table']} SET {r['detail_field']}=%s WHERE Id=%s",
                                (new_oe_id, r["row_id"]),
                            )
                            results["updated"].append({
                                "table": r["table"],
                                "id": str(r["row_id"]),
                                "old": r["old_detail_id"],
                                "new": new_oe_id,
                            })
                        except Exception as e:
                            results["failed"].append({
                                "table": r["table"],
                                "id": str(r["row_id"]),
                                "error": str(e),
                            })
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(results["failed"]) == 0,
            "updated_count": len(results["updated"]),
            "failed_count": len(results["failed"]),
            "results": results,
            "message": f"修复完成: 成功 {len(results['updated'])} 条, 失败 {len(results['failed'])} 条",
        }

    async def regenerate_order_ids(self, workorder_id: str) -> Dict:
        """重新生成订单Id和明细Id（明细每行生成一个新值，订单级字段按原始值分组）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        results = {"updated": [], "failed": []}

        if isinstance(pool, aiomysql.Pool):
            order_pool = await self._get_order_pool()
            if not isinstance(order_pool, aiomysql.Pool):
                raise ValueError("不支持的连接池类型")
            async with pool.acquire() as conn, order_pool.acquire() as order_conn:
                async with conn.cursor() as cur, order_conn.cursor() as order_cur:
                    # 1. 收集所有明细行，按原始 OrderDetailId 分组并生成新值
                    detail_tables = [
                        ("tb_workgoodsdetail", "WorkOrderId"),
                        ("tb_workgoodsdetail_other", "WorkOrderId"),
                        ("tb_workfixitemdetail", "WorkOrderId"),
                    ]

                    # 收集所有明细行
                    all_detail_rows = []
                    for table, where_col in detail_tables:
                        detail_field = "NewOrderDetailId" if table == "tb_workfixitemdetail" else "OrderDetailId"
                        await cur.execute(
                            f"SELECT Id, {detail_field} FROM {table} WHERE {where_col}=%s",
                            (workorder_id,),
                        )
                        for row in await cur.fetchall():
                            all_detail_rows.append({
                                "table": table,
                                "detail_field": detail_field,
                                "row_id": row[0],
                                "old_detail_id": str(row[1]) if row[1] else "",
                            })

                    # 为每行明细生成新的 OE 编号（明细每行一个，OE 序列在订单中心库）
                    for r in all_detail_rows:
                        new_id = await self._next_val(order_cur, 'OE')
                        if not new_id:
                            return {"success": False, "message": "生成OE编号失败"}
                        r["new_id"] = new_id

                    # 更新明细表
                    for r in all_detail_rows:
                        new_oi_id = r["new_id"]
                        try:
                            await cur.execute(
                                f"UPDATE {r['table']} SET {r['detail_field']}=%s WHERE Id=%s",
                                (new_oi_id, r["row_id"]),
                            )
                            results["updated"].append({
                                "table": r["table"],
                                "id": str(r["row_id"]),
                                "field": "OrderDetailId",
                                "old": r["old_detail_id"],
                                "new": new_oi_id,
                            })
                        except Exception as e:
                            results["failed"].append({
                                "table": r["table"],
                                "id": str(r["row_id"]),
                                "error": str(e),
                            })

                    # 2. 更新 tb_workgoodsinfo 的 MallOrderId 和 OrderNo（按原始值分组）
                    await cur.execute(
                        "SELECT MallOrderId, OrderNo FROM tb_workgoodsinfo WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    goodsinfo_rows = await cur.fetchall()
                    # 收集所有不同的原始 MallOrderId
                    unique_mall_ids = list({str(row[0]) if row[0] else "" for row in goodsinfo_rows})
                    mall_oi_mapping = {}
                    mall_order_no_mapping = {}
                    # 按旧 MallOrderId 分组：同一个旧 OI 共享一个新 OI，不同旧值各生成一个（订单级，OI 序列在订单中心库）
                    for old_mall_id in unique_mall_ids:
                        new_oi_id = await self._next_val(order_cur, 'OI')
                        if not new_oi_id:
                            return {"success": False, "message": "生成OI编号失败"}
                        mall_oi_mapping[old_mall_id] = new_oi_id

                        # 订单编码在订单中心库生成
                        await order_cur.execute("SELECT fn_GetOrderNoByPrefix('');")
                        on_row = await order_cur.fetchone()
                        new_order_no = str(on_row[0]) if on_row else ""
                        mall_order_no_mapping[old_mall_id] = new_order_no

                    for row in goodsinfo_rows:
                        old_mall_order_id = str(row[0]) if row[0] else ""
                        old_order_no = str(row[1]) if row[1] else ""
                        new_oi_id = mall_oi_mapping[old_mall_order_id]
                        new_order_no = mall_order_no_mapping[old_mall_order_id]
                        try:
                            await cur.execute(
                                "UPDATE tb_workgoodsinfo SET MallOrderId=%s, OrderNo=%s WHERE WorkOrderId=%s",
                                (new_oi_id, new_order_no, workorder_id),
                            )
                            results["updated"].append({
                                "table": "tb_workgoodsinfo",
                                "field": "MallOrderId+OrderNo",
                                "old": f"{old_mall_order_id} / {old_order_no}",
                                "new": f"{new_oi_id} / {new_order_no}",
                            })
                        except Exception as e:
                            results["failed"].append({
                                "table": "tb_workgoodsinfo",
                                "error": str(e),
                            })

                    # 3. 更新 tb_workfixgoodsinfo 的 NewMallOrderId（按原始值分组）
                    await cur.execute(
                        "SELECT Id, NewMallOrderId FROM tb_workfixgoodsinfo WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    fixgoods_rows = await cur.fetchall()
                    unique_fix_ids = list({str(row[1]) if row[1] else "" for row in fixgoods_rows})
                    # 按旧值分组生成新 MallOrderId（订单级，OI 序列在订单中心库）
                    fix_oi_mapping = {}
                    for old_id in unique_fix_ids:
                        new_oi_id = await self._next_val(order_cur, 'OI')
                        if not new_oi_id:
                            return {"success": False, "message": "生成OI编号失败"}
                        fix_oi_mapping[old_id] = new_oi_id

                    for row in fixgoods_rows:
                        row_id = row[0]
                        old_val = str(row[1]) if row[1] else ""
                        new_oi_id = fix_oi_mapping[old_val]
                        try:
                            await cur.execute(
                                "UPDATE tb_workfixgoodsinfo SET NewMallOrderId=%s WHERE Id=%s",
                                (new_oi_id, row_id),
                            )
                            results["updated"].append({
                                "table": "tb_workfixgoodsinfo",
                                "id": str(row_id),
                                "field": "NewMallOrderId",
                                "old": old_val,
                                "new": new_oi_id,
                            })
                        except Exception as e:
                            results["failed"].append({
                                "table": "tb_workfixgoodsinfo",
                                "id": str(row_id),
                                "error": str(e),
                            })

                    # 4. 更新 tb_workfixiteminfo 的 NewMallOrderId（按原始值分组）
                    await cur.execute(
                        "SELECT Id, NewMallOrderId FROM tb_workfixiteminfo WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    fixitem_rows = await cur.fetchall()
                    unique_fixitem_ids = list({str(row[1]) if row[1] else "" for row in fixitem_rows})
                    # 按旧值分组生成新 MallOrderId（订单级，OI 序列在订单中心库）
                    fixitem_oi_mapping = {}
                    for old_id in unique_fixitem_ids:
                        new_oi_id = await self._next_val(order_cur, 'OI')
                        if not new_oi_id:
                            return {"success": False, "message": "生成OI编号失败"}
                        fixitem_oi_mapping[old_id] = new_oi_id

                    for row in fixitem_rows:
                        row_id = row[0]
                        old_val = str(row[1]) if row[1] else ""
                        new_oi_id = fixitem_oi_mapping[old_val]
                        try:
                            await cur.execute(
                                "UPDATE tb_workfixiteminfo SET NewMallOrderId=%s WHERE Id=%s",
                                (new_oi_id, row_id),
                            )
                            results["updated"].append({
                                "table": "tb_workfixiteminfo",
                                "id": str(row_id),
                                "field": "NewMallOrderId",
                                "old": old_val,
                                "new": new_oi_id,
                            })
                        except Exception as e:
                            results["failed"].append({
                                "table": "tb_workfixiteminfo",
                                "id": str(row_id),
                                "error": str(e),
                            })
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(results["failed"]) == 0,
            "updated_count": len(results["updated"]),
            "failed_count": len(results["failed"]),
            "results": results,
            "message": f"重新生成完成: 成功 {len(results['updated'])} 条, 失败 {len(results['failed'])} 条",
        }

    async def query_workorder_status(self, workorder_nos: list[str]) -> dict:
        """查询工单状态信息"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for wo in workorder_nos:
                        await cur.execute(
                            """SELECT a.Id, a.AppCode, a.Deleted, a.DeletedAt, a.DeletedById,
                                      a.WorkStatus, a.CustomerName, a.OrderType,
                                      fn_GetOrderTypeByCode(a.OrderType) AS OrderTypeName
                               FROM tb_workorderinfo a
                               WHERE (a.Id=%s OR a.AppCode=%s)""",
                            (wo, wo),
                        )
                        rows = await cur.fetchall()
                        if not rows:
                            not_found_docs.append(wo)
                            continue
                        for row in rows:
                            found_docs.append({
                                "id": str(row[0]) if row[0] else "",
                                "app_code": str(row[1]) if row[1] else "",
                                "deleted": row[2],
                                "deleted_at": str(row[3]) if row[3] else "",
                                "deleted_by_id": str(row[4]) if row[4] else "",
                                "work_status": row[5] if row[5] is not None else "",
                                "customer_name": str(row[6]) if row[6] else "",
                                "order_type": str(row[7]) if row[7] else "",
                                "order_type_name": str(row[8]) if row[8] else "",
                            })
        else:
            raise ValueError("不支持的连接池类型")

        deleted_by_ids = [doc["deleted_by_id"] for doc in found_docs if doc["deleted_by_id"]]
        user_map = {}
        if deleted_by_ids:
            try:
                from app.services.user_service import user_service
                user_map = await user_service.batch_get_by_user_center_ids(deleted_by_ids)
            except Exception as e:
                logger.warning(f"获取删除人信息失败: {e}")

        unmatched_ids = [did for did in deleted_by_ids if did not in user_map]
        if unmatched_ids:
            try:
                from app.services.user_service import user_service
                local_map = await user_service.get_local_user_display_names(unmatched_ids)
                for did, display_name in local_map.items():
                    user_map[did] = {"user_name": display_name, "code": "", "user_center_user_id": did}
            except Exception as e:
                logger.warning(f"本库用户查询降级失败: {e}")

        for doc in found_docs:
            u = user_map.get(doc["deleted_by_id"], {})
            doc["deleted_by_name"] = u.get("user_name", "")
            doc["deleted_by_code"] = u.get("code", "")

        return {
            "success": len(not_found_docs) == 0,
            "total_count": len(workorder_nos),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "message": f"找到 {len(found_docs)} 条，未找到 {len(not_found_docs)} 条",
        }

    async def delete_logical_workorder(
        self,
        workorder_ids: list[str],
        operator_id: str,
        remark: str = "",
        person_name: str = "",
        person_code: str = "",
    ) -> tuple[int, list[str], list[str]]:
        """批量逻辑删除工单（调用存储过程 proc_DeleteOrderInfo，并写入 tb_remarkinfo 备注）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        success = 0
        failed: list[str] = []
        remark_failed: list[str] = []
        for wo_id in workorder_ids:
            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "CALL proc_DeleteOrderInfo(%s, %s, NOW())",
                                (wo_id, operator_id),
                            )
                            try:
                                await cur.execute(
                                    """INSERT INTO tb_remarkinfo
                                           (Type, Remark, RemarkPersonCode, RemarkPersonName, WorkOrderId, RemarkTime)
                                       VALUES (5, %s, %s, %s, %s, NOW())""",
                                    (remark or "", person_code or "", person_name or "", wo_id),
                                )
                            except Exception as insert_e:
                                remark_failed.append(wo_id)
                                logger.warning(f"逻辑删除工单 {wo_id} 写入备注失败: {insert_e}")
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception as e:
                failed.append(wo_id)
                logger.error(f"逻辑删除工单失败 {wo_id}: {e}")
        return success, failed, remark_failed

    async def query_resources(
        self,
        keyword: str = "",
        source_type: int | None = None,
        deleted_by_id: str = "",
        include_deleted: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """附件列表查询（工单附件三表关联，分页）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    where = ["a.Deleted=0"]
                    params: list = []
                    if keyword:
                        where.append("(a.Id=%s OR a.AppCode=%s)")
                        params.extend([keyword, keyword])
                    if source_type is not None:
                        where.append("b.SourceType=%s")
                        params.append(source_type)
                    if deleted_by_id:
                        where.append("b.DeletedById=%s")
                        params.append(deleted_by_id)
                    if not include_deleted:
                        # 默认只查正常数据；包含已删除时两表删除标记均不过滤，全部查出
                        where.append("b.Deleted=0")
                        where.append("c.Deleted=0")
                    where_sql = " AND ".join(where)

                    await cur.execute(
                        "SELECT COUNT(*) FROM tb_workorderinfo a "
                        "JOIN tb_workresourceinfo b ON b.WorkOrderId=a.Id "
                        "JOIN basic_resourceitem c ON c.Id=b.ResourceId "
                        f"WHERE {where_sql}",
                        tuple(params),
                    )
                    total = (await cur.fetchone())[0]

                    await cur.execute(
                        "SELECT a.Id, a.AppCode, "
                        "fn_GetOrderTypeByCode(a.OrderType), "
                        "fn_GetStatusNameByCode(a.WorkStatus), "
                        "b.Id, b.SourceType, b.ResourceName, b.Remark, "
                        "b.RemindContent, b.ResourceTag, "
                        "b.Deleted, b.DeletedById, b.DeletedAt, c.Url "
                        "FROM tb_workorderinfo a "
                        "JOIN tb_workresourceinfo b ON b.WorkOrderId=a.Id "
                        "JOIN basic_resourceitem c ON c.Id=b.ResourceId "
                        f"WHERE {where_sql} "
                        "ORDER BY b.Id DESC LIMIT %s OFFSET %s",
                        (*params, page_size, (page - 1) * page_size),
                    )
                    rows = await cur.fetchall()

                    deleted_by_ids = [str(r[11]) for r in rows if r[11]]
                    user_map = await self._resolve_user_names(deleted_by_ids)

                    items = []
                    for r in rows:
                        did = str(r[11]) if r[11] else ""
                        u = user_map.get(did, {})
                        items.append({
                            "workorder_id": str(r[0]) if r[0] else "",
                            "app_code": str(r[1]) if r[1] else "",
                            "order_type_name": str(r[2]) if r[2] else "",
                            "work_status_name": str(r[3]) if r[3] else "",
                            "resource_id": str(r[4]) if r[4] else "",
                            "source_type": r[5] if r[5] is not None else "",
                            "source_type_name": RESOURCE_SOURCE_TYPE_MAP.get(
                                r[5], str(r[5] or "")
                            ),
                            "resource_name": str(r[6]) if r[6] else "",
                            "remark": str(r[7]) if r[7] else "",
                            "remind_content": str(r[8]) if r[8] else "",
                            "resource_tag": str(r[9]) if r[9] else "",
                            "deleted": r[10],
                            "deleted_by_id": did,
                            "deleted_by_name": u.get("user_name", ""),
                            "deleted_by_code": u.get("code", ""),
                            "deleted_at": str(r[12]) if r[12] else "",
                            "url": str(r[13]) if r[13] else "",
                        })

                    return {
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                        "items": items,
                        "message": f"共查到 {total} 条附件",
                    }
        raise ValueError("不支持的连接池类型")

    @staticmethod
    async def _resolve_user_names(user_ids: list[str]) -> dict:
        """用户中心Id批量翻译姓名/编码（查不到时降级查本库用户）"""
        if not user_ids:
            return {}
        user_map: dict = {}
        try:
            from app.services.user_service import user_service

            user_map = await user_service.batch_get_by_user_center_ids(user_ids)
        except Exception as e:
            logger.warning(f"获取用户信息失败: {e}")
        unmatched = [d for d in user_ids if d not in user_map]
        if unmatched:
            try:
                from app.services.user_service import user_service

                local_map = await user_service.get_local_user_display_names(unmatched)
                for did, display_name in local_map.items():
                    user_map[did] = {
                        "user_name": display_name,
                        "code": "",
                        "user_center_user_id": did,
                    }
            except Exception as e:
                logger.warning(f"本库用户查询降级失败: {e}")
        return user_map

    async def delete_resources(
        self, resource_ids: list[str], operator_id: str, remark: str = ""
    ) -> Dict:
        """附件逻辑删除（记录删除人；原因备注写入 tb_remarkinfo Type=13）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        if not operator_id:
            raise ValueError("请填写操作人")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(resource_ids))
                    await cur.execute(
                        f"SELECT Id, WorkOrderId FROM tb_workresourceinfo "
                        f"WHERE Id IN ({placeholders}) AND Deleted=0",
                        tuple(resource_ids),
                    )
                    rows = await cur.fetchall()

                    operator_name, operator_code = "", ""
                    if remark:
                        um = await self._resolve_user_names([operator_id])
                        u = um.get(operator_id, {})
                        operator_name = u.get("user_name", "")
                        operator_code = u.get("code", "")

                    if not rows:
                        return {
                            "updated_count": 0,
                            "failed_count": len(resource_ids),
                            "message": "未找到可删除的附件（可能已被删除）",
                        }

                    await cur.execute(
                        "UPDATE tb_workresourceinfo "
                        "SET Deleted=1, DeletedById=%s, DeletedAt=NOW() "
                        f"WHERE Id IN ({placeholders}) AND Deleted=0",
                        (operator_id, *resource_ids),
                    )
                    updated = cur.rowcount

                    # 联动删除资源文件：仅当该资源已无其他正常附件引用时才标记删除
                    if updated > 0:
                        await cur.execute(
                            f"SELECT DISTINCT b.ResourceId FROM tb_workresourceinfo b "
                            f"WHERE b.Id IN ({placeholders}) AND b.ResourceId IS NOT NULL "
                            f"AND NOT EXISTS ("
                            f"SELECT 1 FROM tb_workresourceinfo b2 "
                            f"WHERE b2.ResourceId = b.ResourceId AND b2.Id NOT IN ({placeholders}) "
                            f"AND b2.Deleted = 0)",
                            (*resource_ids, *resource_ids),
                        )
                        safe_resource_ids = [
                            str(r[0]) for r in await cur.fetchall() if r[0]
                        ]
                        if safe_resource_ids:
                            sp = ",".join(["%s"] * len(safe_resource_ids))
                            await cur.execute(
                                "UPDATE basic_resourceitem "
                                "SET Deleted=1, DeletedById=%s, DeletedAt=NOW() "
                                f"WHERE Id IN ({sp}) AND Deleted=0",
                                (operator_id, *safe_resource_ids),
                            )
                            logger.info(
                                f"附件删除联动标记资源文件 {len(safe_resource_ids)} 个: "
                                f"{safe_resource_ids}"
                            )

                    remark_failed = []
                    if remark:
                        for r in rows:
                            try:
                                await cur.execute(
                                    "INSERT INTO tb_remarkinfo "
                                    "(Type, Remark, WorkOrderId, RemarkPersonCode, RemarkPersonName, RemarkTime) "
                                    "VALUES (%s, %s, %s, %s, %s, NOW())",
                                    (
                                        REMARK_TYPE_RESOURCE_DELETE,
                                        remark,
                                        str(r[1]) if r[1] else "",
                                        operator_code,
                                        operator_name,
                                    ),
                                )
                            except Exception as e:
                                remark_failed.append(str(r[0]))
                                logger.warning(f"附件 {r[0]} 删除备注写入失败: {e}")

                    failed = len(resource_ids) - updated
                    return {
                        "updated_count": updated,
                        "failed_count": failed,
                        "remark_failed_count": len(remark_failed),
                        "message": f"附件删除完成: 成功 {updated} 条, 失败 {failed} 条",
                    }
        raise ValueError("不支持的连接池类型")

    async def restore_resources(
        self, resource_ids: list[str], operator_id: str = "", remark: str = ""
    ) -> Dict:
        """附件恢复（Deleted 置回 0；填写操作人时仅恢复该删除人删除的附件）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    where = "Deleted=1"
                    params: list = []
                    if operator_id:
                        where += " AND DeletedById=%s"
                        params.append(operator_id)
                    placeholders = ",".join(["%s"] * len(resource_ids))

                    operator_name, operator_code = "", ""
                    if remark and operator_id:
                        um = await self._resolve_user_names([operator_id])
                        u = um.get(operator_id, {})
                        operator_name = u.get("user_name", "")
                        operator_code = u.get("code", "")

                    await cur.execute(
                        "UPDATE tb_workresourceinfo "
                        "SET Deleted=0, DeletedById=NULL, DeletedAt=NULL "
                        f"WHERE Id IN ({placeholders}) AND {where}",
                        (*resource_ids, *params),
                    )
                    updated = cur.rowcount

                    # 恢复资源文件：附件恢复后其引用的资源若处于删除状态则一并恢复
                    if updated > 0:
                        await cur.execute(
                            f"SELECT DISTINCT ResourceId FROM tb_workresourceinfo "
                            f"WHERE Id IN ({placeholders}) AND ResourceId IS NOT NULL",
                            tuple(resource_ids),
                        )
                        affected_resources = [
                            str(r[0]) for r in await cur.fetchall() if r[0]
                        ]
                        if affected_resources:
                            ap = ",".join(["%s"] * len(affected_resources))
                            await cur.execute(
                                "UPDATE basic_resourceitem "
                                "SET Deleted=0, DeletedById=NULL, DeletedAt=NULL "
                                f"WHERE Id IN ({ap}) AND Deleted=1",
                                tuple(affected_resources),
                            )

                    remark_failed = []
                    if remark:
                        await cur.execute(
                            "SELECT Id, WorkOrderId FROM tb_workresourceinfo "
                            f"WHERE Id IN ({placeholders})",
                            tuple(resource_ids),
                        )
                        rows = await cur.fetchall()
                        for r in rows:
                            try:
                                await cur.execute(
                                    "INSERT INTO tb_remarkinfo "
                                    "(Type, Remark, WorkOrderId, RemarkPersonCode, RemarkPersonName, RemarkTime) "
                                    "VALUES (%s, %s, %s, %s, %s, NOW())",
                                    (
                                        REMARK_TYPE_RESOURCE_RESTORE,
                                        remark,
                                        str(r[1]) if r[1] else "",
                                        operator_code,
                                        operator_name,
                                    ),
                                )
                            except Exception as e:
                                remark_failed.append(str(r[0]))
                                logger.warning(f"附件 {r[0]} 恢复备注写入失败: {e}")

                    failed = len(resource_ids) - updated
                    return {
                        "updated_count": updated,
                        "failed_count": failed,
                        "remark_failed_count": len(remark_failed),
                        "message": f"附件恢复完成: 成功 {updated} 条, 失败 {failed} 条",
                    }
        raise ValueError("不支持的连接池类型")

    async def restore_logical_workorder(self, workorder_id: str, operator_id: str) -> bool:
        """恢复逻辑删除的工单（调用存储过程 proc_UnDeleteOrderInfo）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "CALL proc_UnDeleteOrderInfo(%s, %s)",
                        (workorder_id, operator_id),
                    )
                    return True
        raise ValueError("不支持的连接池类型")

    async def close_workorder_batch(self, workorder_ids: list[str]) -> tuple[int, list[str]]:
        """批量关闭工单（修改 tb_workorderinfo 和 tb_workorderstatus 的 WorkStatus 为 10）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        success = 0
        failed: list[str] = []
        for wo_id in workorder_ids:
            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "UPDATE tb_workorderinfo SET WorkStatus=10 WHERE Id=%s",
                                (wo_id,),
                            )
                            await cur.execute(
                                "UPDATE tb_workorderstatus SET WorkStatus=10 WHERE WorkOrderId=%s",
                                (wo_id,),
                            )

                            # 查询 ServiceProviderCode，根据不同服务商调用对应的存储过程
                            await cur.execute(
                                "SELECT ServiceProviderCode FROM tb_workorderinfo WHERE Id=%s",
                                (wo_id,),
                            )
                            sp_row = await cur.fetchone()
                            sp_code = str(sp_row[0]) if sp_row and sp_row[0] else ""

                            if sp_code == "1067":
                                # 壹好车服：调用 proc_ChpCompletedWorkOrderById
                                try:
                                    await cur.execute(
                                        "CALL proc_ChpCompletedWorkOrderById(%s)",
                                        (wo_id,),
                                    )
                                    logger.info(f"工单 {wo_id} 调用 proc_ChpCompletedWorkOrderById 成功")
                                except Exception as sp_e:
                                    logger.warning(f"工单 {wo_id} 调用 proc_ChpCompletedWorkOrderById 失败: {sp_e}")

                            elif sp_code == "1003":
                                # 服务商1003：调用 proc_VhsCompletedWorkOrderById 和 proc_VhsCompletedWorkOrderInfoById
                                try:
                                    await cur.execute(
                                        "CALL proc_VhsCompletedWorkOrderById(%s)",
                                        (wo_id,),
                                    )
                                    logger.info(f"工单 {wo_id} 调用 proc_VhsCompletedWorkOrderById 成功")
                                except Exception as sp_e:
                                    logger.warning(f"工单 {wo_id} 调用 proc_VhsCompletedWorkOrderById 失败: {sp_e}")

                                try:
                                    await cur.execute(
                                        "CALL proc_VhsCompletedWorkOrderInfoById(%s)",
                                        (wo_id,),
                                    )
                                    logger.info(f"工单 {wo_id} 调用 proc_VhsCompletedWorkOrderInfoById 成功")
                                except Exception as sp_e:
                                    logger.warning(f"工单 {wo_id} 调用 proc_VhsCompletedWorkOrderInfoById 失败: {sp_e}")

                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception as e:
                failed.append(wo_id)
                logger.error(f"关闭工单失败 {wo_id}: {e}")
        return success, failed

    async def fetch_workorder_ids_by_nos(self, workorder_nos: list[str]) -> dict:
        """根据工单编码或Id获取对应的Id（同一编码可能对应多条工单，如加装/检修）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for wo in workorder_nos:
                        await cur.execute(
                            """SELECT a.Id, a.AppCode, a.OrderType, a.Deleted,
                                      fn_GetOrderTypeByCode(a.OrderType) AS OrderTypeName,
                                      a.DeletedById
                               FROM tb_workorderinfo a
                               WHERE (a.Id=%s OR a.AppCode=%s)""",
                            (wo, wo),
                        )
                        rows = await cur.fetchall()
                        if not rows:
                            not_found_docs.append(wo)
                            continue
                        for row in rows:
                            found_docs.append({
                                "workorder_id": str(row[0]),
                                "app_code": str(row[1]) if row[1] else "",
                                "order_type": str(row[2]) if row[2] else "",
                                "deleted": row[3],
                                "order_type_name": str(row[4]) if row[4] else "",
                                "deleted_by_id": str(row[5]) if row[5] else "",
                                "input": wo,
                            })
        else:
            raise ValueError("不支持的连接池类型")

        workorder_id_map: dict[str, str] = {}
        for doc in found_docs:
            workorder_id_map.setdefault(doc["input"], doc["workorder_id"])

        return {
            "success": len(not_found_docs) == 0,
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "workorder_id_map": workorder_id_map,
        }

    async def query_create_type(self, workorder_nos: list[str]) -> dict:
        """查询工单CreateType（单据来源）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for wo in workorder_nos:
                        await cur.execute(
                            """SELECT a.Id, a.AppCode, a.CreateType, a.CustomerName, a.OrderType,
                                      a.ServiceProviderCode,
                                      fn_GetOrderTypeByCode(a.OrderType) AS OrderTypeName
                               FROM tb_workorderinfo a
                               WHERE (a.Id=%s OR a.AppCode=%s) AND a.Deleted=0""",
                            (wo, wo),
                        )
                        rows = await cur.fetchall()
                        if not rows:
                            not_found_docs.append(wo)
                            continue
                        for row in rows:
                            service_provider_code = str(row[5]) if row[5] else ""
                            found_docs.append({
                                "workorder_id": str(row[0]),
                                "app_code": str(row[1]) if row[1] else "",
                                "create_type": row[2] if row[2] is not None else "",
                                "customer_name": str(row[3]) if row[3] else "",
                                "order_type": str(row[4]) if row[4] else "",
                                "service_provider_code": service_provider_code,
                                "allow_modify": service_provider_code
                                == ALLOWED_SERVICE_PROVIDER_CODE,
                                "order_type_name": str(row[6]) if row[6] else "",
                                "input": wo,
                            })
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(not_found_docs) == 0,
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "message": f"找到 {len(found_docs)} 条，未找到 {len(not_found_docs)} 条",
        }

    async def update_create_type(
        self, workorder_no: str, create_type: int, restrict_charging_pile: bool = False
    ) -> dict:
        """修改工单CreateType（单据来源）

        restrict_charging_pile=True 时仅允许充电桩单据（ServiceProviderCode=1067），
        供独立的「修改单据来源」菜单使用；工单管理原入口不限制。
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 先查询工单是否存在
                    await cur.execute(
                        """SELECT Id, AppCode, CreateType, ServiceProviderCode FROM tb_workorderinfo
                           WHERE (Id=%s OR AppCode=%s) AND Deleted=0""",
                        (workorder_no, workorder_no),
                    )
                    row = await cur.fetchone()
                    if not row:
                        return {
                            "success": False,
                            "message": f"未找到工单: {workorder_no}",
                        }

                    workorder_id = str(row[0])
                    app_code = str(row[1]) if row[1] else ""
                    old_create_type = row[2]
                    service_provider_code = str(row[3]) if row[3] else ""

                    # 仅充电桩单据可修改（独立菜单入口）
                    if (
                        restrict_charging_pile
                        and service_provider_code != ALLOWED_SERVICE_PROVIDER_CODE
                    ):
                        return {
                            "success": False,
                            "workorder_id": workorder_id,
                            "app_code": app_code,
                            "service_provider_code": service_provider_code,
                            "message": (
                                f"工单 {workorder_id} 非充电桩单据"
                                f"（ServiceProviderCode={service_provider_code or '空'}），"
                                f"仅充电桩单据（ServiceProviderCode={ALLOWED_SERVICE_PROVIDER_CODE}）可修改单据来源"
                            ),
                        }

                    # 幂等：当前值已是目标值，直接返回成功，不再 UPDATE、不报错
                    if old_create_type is not None and str(old_create_type) == str(create_type):
                        return {
                            "success": True,
                            "already_updated": True,
                            "workorder_id": workorder_id,
                            "app_code": app_code,
                            "service_provider_code": service_provider_code,
                            "old_create_type": old_create_type,
                            "new_create_type": create_type,
                            "message": f"工单 {workorder_id} 的 CreateType 已是 {create_type}，无需修改",
                        }

                    if restrict_charging_pile:
                        # 带上服务商编码条件双保险，防止并发下误改
                        await cur.execute(
                            "UPDATE tb_workorderinfo SET CreateType=%s "
                            "WHERE Id=%s AND ServiceProviderCode=%s",
                            (create_type, workorder_id, ALLOWED_SERVICE_PROVIDER_CODE),
                        )
                        if cur.rowcount != 1:
                            return {
                                "success": False,
                                "workorder_id": workorder_id,
                                "app_code": app_code,
                                "service_provider_code": service_provider_code,
                                "message": f"修改失败: 工单 {workorder_id} 非充电桩单据或状态已变化，请重新查询",
                            }
                    else:
                        await cur.execute(
                            "UPDATE tb_workorderinfo SET CreateType=%s WHERE Id=%s",
                            (create_type, workorder_id),
                        )

                    return {
                        "success": True,
                        "workorder_id": workorder_id,
                        "app_code": app_code,
                        "service_provider_code": service_provider_code,
                        "old_create_type": old_create_type,
                        "new_create_type": create_type,
                        "message": f"修改成功: 工单 {workorder_id} 的 CreateType 从 {old_create_type} 修改为 {create_type}",
                    }
        else:
            raise ValueError("不支持的连接池类型")


ehcf_service = EhcfService()
