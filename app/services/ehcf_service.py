from typing import Dict, List, Tuple
import aiomysql
import logging

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

_ehcf_conn_id = None


async def _get_conn_id():
    global _ehcf_conn_id
    if _ehcf_conn_id is None:
        _ehcf_conn_id = await settings.EHCF_CONN_ID()
    return _ehcf_conn_id


class EhcfService:
    """壹好车服业务服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        await db_pool.ensure_pool(await _get_conn_id())

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
        """修复订单明细Id（生成新的OE编号）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        results = {"updated": [], "failed": []}

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 生成一个新的OE编号
                    await cur.execute("SELECT fn_nextval('OE');")
                    oe_row = await cur.fetchone()
                    new_oe_id = str(oe_row[0]) if oe_row else ""

                    if not new_oe_id:
                        return {"success": False, "message": "生成OE编号失败"}

                    # 处理三张表
                    tables = [
                        ("tb_workgoodsdetail", "WorkOrderId"),
                        ("tb_workgoodsdetail_other", "WorkOrderId"),
                        ("tb_workfixitemdetail", "WorkOrderId"),
                    ]

                    for table, where_col in tables:
                        # tb_workfixitemdetail 的字段名是 NewOrderDetailId
                        detail_field = "NewOrderDetailId" if table == "tb_workfixitemdetail" else "OrderDetailId"
                        await cur.execute(
                            f"SELECT Id, {detail_field} FROM {table} WHERE {where_col}=%s",
                            (workorder_id,),
                        )
                        rows = await cur.fetchall()
                        for row in rows:
                            row_id = row[0]
                            old_detail_id = str(row[1]) if row[1] else ""
                            try:
                                await cur.execute(
                                    f"UPDATE {table} SET {detail_field}=%s WHERE Id=%s",
                                    (new_oe_id, row_id),
                                )
                                results["updated"].append({
                                    "table": table,
                                    "id": str(row_id),
                                    "old": old_detail_id,
                                    "new": new_oe_id,
                                })
                            except Exception as e:
                                results["failed"].append({
                                    "table": table,
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
            "message": f"修复完成: 成功 {len(results['updated'])} 条, 失败 {len(results['failed'])} 条",
        }

    async def regenerate_order_ids(self, workorder_id: str) -> Dict:
        """重新生成订单Id和明细Id"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        results = {"updated": [], "failed": []}

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 生成新的OI编号
                    await cur.execute("SELECT fn_nextval('OI');")
                    oi_row = await cur.fetchone()
                    new_oi_id = str(oi_row[0]) if oi_row else ""

                    # 生成新的订单编码
                    await cur.execute("SELECT fn_GetOrderNoByPrefix('');")
                    on_row = await cur.fetchone()
                    new_order_no = str(on_row[0]) if on_row else ""

                    # 生成新的OE编号
                    await cur.execute("SELECT fn_nextval('OE');")
                    oe_row = await cur.fetchone()
                    new_oe_id = str(oe_row[0]) if oe_row else ""

                    if not new_oi_id or not new_order_no:
                        return {"success": False, "message": "生成OI编号或订单编码失败"}
                    if not new_oe_id:
                        new_oe_id = new_oi_id

                    # 1. 更新明细表的 OrderDetailId
                    detail_tables = [
                        ("tb_workgoodsdetail", "WorkOrderId"),
                        ("tb_workgoodsdetail_other", "WorkOrderId"),
                        ("tb_workfixitemdetail", "WorkOrderId"),
                    ]
                    for table, where_col in detail_tables:
                        # tb_workfixitemdetail 的字段名是 NewOrderDetailId
                        detail_field = "NewOrderDetailId" if table == "tb_workfixitemdetail" else "OrderDetailId"
                        await cur.execute(
                            f"SELECT Id, {detail_field} FROM {table} WHERE {where_col}=%s",
                            (workorder_id,),
                        )
                        rows = await cur.fetchall()
                        for row in rows:
                            row_id = row[0]
                            old_detail_id = str(row[1]) if row[1] else ""
                            try:
                                await cur.execute(
                                    f"UPDATE {table} SET {detail_field}=%s WHERE Id=%s",
                                    (new_oi_id, row_id),
                                )
                                results["updated"].append({
                                    "table": table,
                                    "id": str(row_id),
                                    "field": "OrderDetailId",
                                    "old": old_detail_id,
                                    "new": new_oi_id,
                                })
                            except Exception as e:
                                results["failed"].append({
                                    "table": table,
                                    "id": str(row_id),
                                    "error": str(e),
                                })

                    # 2. 更新 tb_workgoodsinfo 的 MallOrderId 和 OrderNo
                    await cur.execute(
                        "SELECT MallOrderId, OrderNo FROM tb_workgoodsinfo WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    rows = await cur.fetchall()
                    for row in rows:
                        old_mall_order_id = str(row[0]) if row[0] else ""
                        old_order_no = str(row[1]) if row[1] else ""
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

                    # 3. 更新 tb_workfixgoodsinfo 的 NewMallOrderId
                    await cur.execute(
                        "SELECT Id, NewMallOrderId FROM tb_workfixgoodsinfo WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    rows = await cur.fetchall()
                    for row in rows:
                        row_id = row[0]
                        old_val = str(row[1]) if row[1] else ""
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

                    # 4. 更新 tb_workfixiteminfo 的 NewMallOrderId
                    await cur.execute(
                        "SELECT Id, NewMallOrderId FROM tb_workfixiteminfo WHERE WorkOrderId=%s",
                        (workorder_id,),
                    )
                    rows = await cur.fetchall()
                    for row in rows:
                        row_id = row[0]
                        old_val = str(row[1]) if row[1] else ""
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
            "summary": {
                "new_oi_id": new_oi_id,
                "new_order_no": new_order_no,
                "new_oe_id": new_oe_id,
            },
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

    async def delete_logical_workorder(self, workorder_ids: list[str], operator_id: str) -> tuple[int, list[str]]:
        """批量逻辑删除工单（调用存储过程 proc_DeleteOrderInfo）"""
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
                                "CALL proc_DeleteOrderInfo(%s, %s, NOW())",
                                (wo_id, operator_id),
                            )
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception as e:
                failed.append(wo_id)
                logger.error(f"逻辑删除工单失败 {wo_id}: {e}")
        return success, failed

    async def restore_logical_workorder(self, workorder_id: str, operator_id: str) -> bool:
        """恢复逻辑删除的工单（调用存储过程 proc_UnDeleteOrderInfo）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("EHCF连接池不存在")

        from datetime import datetime

        now = datetime.now()
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "CALL proc_UnDeleteOrderInfo(%s, %s, %s)",
                        (workorder_id, operator_id, now),
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
                            """SELECT a.Id, a.AppCode, a.OrderType,
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
                                "workorder_id": str(row[0]),
                                "app_code": str(row[1]) if row[1] else "",
                                "order_type": str(row[2]) if row[2] else "",
                                "order_type_name": str(row[3]) if row[3] else "",
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


ehcf_service = EhcfService()
