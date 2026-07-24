from typing import Dict, List, Optional, Tuple
import aiomysql
import logging

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

# 订单固定连接的Id（延迟获取，避免模块加载时Tortoise未初始化）
_order_conn_id = None
_gfs_conn_id = None
_mallcenter_conn_id = None

async def _get_conn_id():
    global _order_conn_id
    if _order_conn_id is None:
        _order_conn_id = await settings.ORDER_CONN_ID()
    return _order_conn_id

async def _get_gfs_conn_id():
    global _gfs_conn_id
    if _gfs_conn_id is None:
        _gfs_conn_id = await settings.GFS_CONN_ID()
    return _gfs_conn_id

async def _get_mallcenter_conn_id():
    global _mallcenter_conn_id
    if _mallcenter_conn_id is None:
        _mallcenter_conn_id = await settings.ORDER_CONN_ID()
    return _mallcenter_conn_id

class OrderService:
    """订单业务服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        await db_pool.ensure_pool(await _get_conn_id())

    async def fetch_audit_time_map(self, order_nos: List[str]) -> Dict:
        """根据订单编码或数字Id获取审核时间，返回详细的验证结果"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for order_no in order_nos:
                        is_numeric = order_no.isdigit()

                        # 根据输入类型决定主查和备查
                        queries = []
                        if is_numeric:
                            doc_id = int(order_no)
                            queries = [
                                ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE Id=%s LIMIT 1", (doc_id,)),
                                ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                            ]
                        else:
                            queries = [
                                ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                                ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE Id=%s LIMIT 1", (order_no,)),
                            ]

                        # 按优先级逐条查询，找到第一个命中的就停
                        result = None
                        for sql, params in queries:
                            await cur.execute(sql, params)
                            row = await cur.fetchone()
                            if row:
                                result = row
                                break

                        if not result:
                            not_found_docs.append(order_no)
                            logger.warning(f"订单未找到: {order_no}")
                        else:
                            order_id, order_no_actual, audit_time = result
                            found_docs.append({
                                "order_id": order_id,
                                "order_no": order_no,
                                "actual_order_no": order_no_actual,
                                "audit_time": audit_time
                            })
                            logger.info(f"找到订单: {order_no} -> Id={order_id}, OrderNo={order_no_actual}")
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(not_found_docs) == 0,
            "total_count": len(order_nos),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "message": self._build_fetch_message(len(found_docs), len(not_found_docs)),
            "audit_time_map": {doc["order_no"]: doc["audit_time"] for doc in found_docs}
        }

    async def fetch_order_ids_by_nos(self, order_nos: List[str]) -> Dict:
        """根据订单编码或数字Id获取对应的Id，优先按输入类型匹配，返回详细的验证结果"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for order_no in order_nos:
                        is_numeric = order_no.isdigit()

                        # 根据输入类型决定主查和备查
                        queries = []
                        if is_numeric:
                            doc_id = int(order_no)
                            queries = [
                                ("SELECT Id, OrderNo FROM tb_orderinfo WHERE Id=%s LIMIT 1", (doc_id,)),
                                ("SELECT Id, OrderNo FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                            ]
                        else:
                            queries = [
                                ("SELECT Id, OrderNo FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                                ("SELECT Id, OrderNo FROM tb_orderinfo WHERE Id=%s LIMIT 1", (order_no,)),
                            ]

                        # 按优先级逐条查询，找到第一个命中的就停
                        result = None
                        for sql, params in queries:
                            await cur.execute(sql, params)
                            row = await cur.fetchone()
                            if row:
                                result = row
                                break

                        if not result:
                            not_found_docs.append(order_no)
                            logger.warning(f"订单未找到: {order_no}")
                        else:
                            order_id, order_no_actual = result
                            found_docs.append({
                                "order_id": order_id,
                                "order_no": order_no,
                                "actual_order_no": order_no_actual
                            })
                            logger.info(f"找到订单: {order_no} -> Id={order_id}, OrderNo={order_no_actual}")
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(not_found_docs) == 0,
            "total_count": len(order_nos),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "message": self._build_fetch_message(len(found_docs), len(not_found_docs)),
            "order_id_map": {doc["order_no"]: doc["order_id"] for doc in found_docs}
        }

    def _build_fetch_message(self, found_count: int, not_found_count: int) -> str:
        """构建获取订单的消息"""
        parts = []
        if found_count > 0:
            parts.append(f"找到 {found_count} 条订单")
        if not_found_count > 0:
            parts.append(f"{not_found_count} 条订单不存在")

        return "，".join(parts) if parts else "所有订单均找到"

    async def fetch_deleted_order_by_no(self, order_no: str, deleted_by_id: str = None) -> Optional[Dict]:
        """根据订单编码或数字Id查询已删除的订单（Deleted=1），验证唯一性"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        is_numeric = order_no.isdigit()

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 根据输入类型构建查询条件
                    if is_numeric:
                        doc_id = int(order_no)
                        conditions = [
                            ("Id", doc_id),
                            ("OrderNo", order_no),
                        ]
                    else:
                        conditions = [
                            ("OrderNo", order_no),
                            ("Id", order_no),
                        ]

                    for col_name, col_val in conditions:
                        deleted_cond = " AND DeletedById = %s" if deleted_by_id else ""
                        count_params = (col_val, deleted_by_id) if deleted_by_id else (col_val,)
                        count_sql = f"SELECT COUNT(*) FROM tb_orderinfo WHERE {col_name} = %s AND Deleted=1{deleted_cond}"
                        await cur.execute(count_sql, count_params)
                        count_row = await cur.fetchone()
                        count = count_row[0] if count_row else 0

                        if count == 1:
                            sel_params = (col_val, deleted_by_id) if deleted_by_id else (col_val,)
                            sql = f"SELECT Id, OrderNo, Deleted, DeletedById FROM tb_orderinfo WHERE {col_name} = %s AND Deleted=1{deleted_cond}"
                            await cur.execute(sql, sel_params)
                            row = await cur.fetchone()
                            if row:
                                return {
                                    "id": row[0],
                                    "order_no": row[1],
                                    "deleted": row[2],
                                    "deleted_by_id": row[3] if len(row) > 3 else None,
                                }

                    return None
        raise ValueError("不支持的连接池类型")

    async def update_audit_time_batch(self, order_ids: List[int], new_time) -> int:
        """批量更新订单审核时间（使用指定连接池）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholder = ",".join(["%s"] * len(order_ids))
                    sql = f"UPDATE tb_orderinfo SET AuditTime = %s WHERE Id IN ({placeholder})"
                    await cur.execute(sql, tuple([new_time, *order_ids]))
                    return cur.rowcount or 0
        raise ValueError("不支持的连接池类型")

    async def delete_logical_batch(self, order_ids: List[int], deleted_by_id: str = None) -> Tuple[int, List[int]]:
        """批量逻辑删除订单（逐行调用存储过程）"""
        import uuid
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        
        # 如果没有传入deleted_by_id，生成一个随机GUID
        if deleted_by_id is None:
            deleted_by_id = str(uuid.uuid4())
        
        success = 0
        failed: List[int] = []
        for order_id in order_ids:
            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute("CALL proc_DeleteOrderInfoById(%s, %s)", (order_id, deleted_by_id))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(order_id)
        return success, failed

    async def delete_physical_batch(self, order_ids: List[int]) -> Tuple[int, List[int]]:
        """批量物理删除订单（逐行调用存储过程）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        
        success = 0
        failed: List[int] = []
        for order_id in order_ids:
            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute("CALL proc_TruncateOrderInfoById(%s)", (order_id,))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(order_id)
        return success, failed

    async def restore_logical(self, order_id: int, operator_id: str) -> bool:
        """恢复逻辑删除的订单"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("CALL proc_UnDeleteOrderInfoById(%s, %s)", (order_id, operator_id))
                    return True
        raise ValueError("不支持的连接池类型")

    async def query_order_status(self, order_nos: List[str]) -> Dict:
        """查询订单状态信息，返回Id、OrderNo、AuditTime、Deleted、DeletedById、DeletedAt，并关联OA获取删除人姓名"""
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
                    for order_no in order_nos:
                        is_numeric = order_no.isdigit()
                        queries = []
                        if is_numeric:
                            doc_id = int(order_no)
                            queries = [
                                ("SELECT Id, OrderNo, AuditTime, Deleted, DeletedById, DeletedAt FROM tb_orderinfo WHERE Id=%s LIMIT 1", (doc_id,)),
                            ]
                        else:
                            queries = [
                                ("SELECT Id, OrderNo, AuditTime, Deleted, DeletedById, DeletedAt FROM tb_orderinfo WHERE OrderNo=%s LIMIT 1", (order_no,)),
                                ("SELECT Id, OrderNo, AuditTime, Deleted, DeletedById, DeletedAt FROM tb_orderinfo WHERE Id=%s LIMIT 1", (order_no,)),
                            ]

                        result = None
                        for sql, params in queries:
                            await cur.execute(sql, params)
                            row = await cur.fetchone()
                            if row:
                                result = row
                                break

                        if not result:
                            not_found_docs.append(order_no)
                        else:
                            found_docs.append({
                                "id": str(result[0]),
                                "order_no": str(result[1]) if result[1] else "",
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

        return {
            "success": len(not_found_docs) == 0,
            "total_count": len(order_nos),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "message": self._build_fetch_message(len(found_docs), len(not_found_docs)),
        }

    async def query_gfs_order_status(self, order_nos: List[str] = None, order_ids: List[str] = None) -> Dict:
        """查询GFS订单状态，验证对账、开票、回款、推广费状态"""
        await db_pool.ensure_pool(await _get_gfs_conn_id())
        pool = db_pool.get_pool(await _get_gfs_conn_id())
        if pool is None:
            raise ValueError("GFS连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 按订单编码查询
                    if order_nos:
                        placeholders = ",".join(["%s"] * len(order_nos))
                        sql = f"SELECT OrderNo, ReconcState, InvoiceState, ReceiptState, PromotionState FROM finance_basic.basic_orderinfo WHERE OrderNo IN ({placeholders})"
                        await cur.execute(sql, tuple(order_nos))
                        rows = await cur.fetchall()
                        for row in rows:
                            found_docs.append({
                                "order_no": row[0],
                                "reconc_state": row[1],
                                "invoice_state": row[2],
                                "receipt_state": row[3],
                                "promotion_state": row[4],
                            })
                        found_nos = [doc["order_no"] for doc in found_docs]
                        not_found_docs = [no for no in order_nos if no not in found_nos]

                    # 按订单Id查询
                    if order_ids:
                        placeholders = ",".join(["%s"] * len(order_ids))
                        sql = f"SELECT OrderId, ReconcState, InvoiceState, ReceiptState, PromotionState FROM finance_basic.basic_orderinfo WHERE OrderId IN ({placeholders})"
                        await cur.execute(sql, tuple(order_ids))
                        rows = await cur.fetchall()
                        for row in rows:
                            found_docs.append({
                                "order_id": row[0],
                                "reconc_state": row[1],
                                "invoice_state": row[2],
                                "receipt_state": row[3],
                                "promotion_state": row[4],
                            })
        else:
            raise ValueError("不支持的连接池类型")

        # 验证状态是否允许删除
        invalid_docs = []
        for doc in found_docs:
            invalid_reasons = []
            if doc.get("reconc_state") is not None and doc["reconc_state"] != 0:
                invalid_reasons.append(f"对账状态为{doc['reconc_state']}（需为0未提交）")
            if doc.get("invoice_state") is not None and doc["invoice_state"] != 0:
                invalid_reasons.append(f"开票状态为{doc['invoice_state']}（需为0待申请）")
            if doc.get("receipt_state") is not None and doc["receipt_state"] != 0:
                invalid_reasons.append(f"回款状态为{doc['receipt_state']}（需为0未回款）")
            if doc.get("promotion_state") is not None and doc["promotion_state"] != 0:
                invalid_reasons.append(f"推广费状态为{doc['promotion_state']}（需为0待申请）")
            if invalid_reasons:
                doc["invalid_reasons"] = invalid_reasons
                invalid_docs.append(doc)

        return {
            "success": len(invalid_docs) == 0,
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "invalid_count": len(invalid_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "invalid_docs": invalid_docs,
            "message": f"查询到 {len(found_docs)} 条，{len(not_found_docs)} 条未同步，{len(invalid_docs)} 条状态不符合" if (not_found_docs or invalid_docs) else "所有订单状态均符合删除条件",
        }

    async def delete_gfs_order(self, order_id: str) -> bool:
        """调用GFS存储过程删除订单"""
        await db_pool.ensure_pool(await _get_gfs_conn_id())
        pool = db_pool.get_pool(await _get_gfs_conn_id())
        if pool is None:
            raise ValueError("GFS连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("CALL finance_basic.proc_DeleteOrderById(%s)", (order_id,))
                    return True
        else:
            raise ValueError("不支持的连接池类型")

    async def delete_check_record(self, order_id: str) -> bool:
        """删除校验记录"""
        await db_pool.ensure_pool(await _get_mallcenter_conn_id())
        pool = db_pool.get_pool(await _get_mallcenter_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM mallcenter.sys_reoperatecheck WHERE Id=%s", (order_id,))
                    return True
        else:
            raise ValueError("不支持的连接池类型")


order_service = OrderService()
