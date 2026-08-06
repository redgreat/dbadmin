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
                               a.CustomerName
                        FROM tb_workorderinfo a
                        WHERE (a.Id=%s OR a.AppNo=%s) AND a.Deleted=0
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
                            "order_type": row[2] if len(row) > 2 else "",
                            "order_type_name": row[3] if len(row) > 3 else "",
                            "status_type_name": row[4] if len(row) > 4 else "",
                            "work_status": row[5] if len(row) > 5 else "",
                            "close_status_name": row[6] if len(row) > 6 else "",
                            "customer_name": row[7] if len(row) > 7 else "",
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
                        "SELECT Id, OrderDetailId FROM tb_workfixitemdetail WHERE WorkOrderId=%s",
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
                        await cur.execute(
                            f"SELECT Id, OrderDetailId FROM {table} WHERE {where_col}=%s",
                            (workorder_id,),
                        )
                        rows = await cur.fetchall()
                        for row in rows:
                            row_id = row[0]
                            old_detail_id = str(row[1]) if row[1] else ""
                            try:
                                await cur.execute(
                                    f"UPDATE {table} SET OrderDetailId=%s WHERE Id=%s",
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
                        await cur.execute(
                            f"SELECT Id, OrderDetailId FROM {table} WHERE {where_col}=%s",
                            (workorder_id,),
                        )
                        rows = await cur.fetchall()
                        for row in rows:
                            row_id = row[0]
                            old_detail_id = str(row[1]) if row[1] else ""
                            try:
                                await cur.execute(
                                    f"UPDATE {table} SET OrderDetailId=%s WHERE Id=%s",
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


ehcf_service = EhcfService()
