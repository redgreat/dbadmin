from typing import Dict, List, Optional, Tuple
import re
import aiomysql

from app.services.db_pool import db_pool
from app.controllers.conn import conn_controller
from app.settings.config import settings

# 订单固定连接的Id（延迟获取，避免模块加载时Tortoise未初始化）
_order_conn_id = None

async def _get_conn_id():
    global _order_conn_id
    if _order_conn_id is None:
        _order_conn_id = await settings.ORDER_CONN_ID()
    return _order_conn_id

class OrderService:
    """订单业务服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is not None:
            return
        conn = await conn_controller.get_decrypted_connection(await _get_conn_id())
        if not conn:
            raise ValueError("连接池不存在")
        await db_pool.register_pool(
            conn_id=conn["id"],
            db_type=conn["db_type"],
            host=conn["host"],
            port=conn["port"],
            username=conn["username"],
            password=conn["password"],
            database=conn["database"],
            params=conn["params"],
        )

    async def fetch_audit_time_map(self, order_nos: List[str]) -> Dict[str, Optional[str]]:
        """根据订单编码获取审核时间（使用指定连接池）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholder = ",".join(["%s"] * len(order_nos))
                    sql = f"SELECT OrderNo, AuditTime FROM tb_orderinfo WHERE OrderNo IN ({placeholder}) AND Deleted=0"
                    await cur.execute(sql, tuple(order_nos))
                    rows = await cur.fetchall()
                    return {r[0]: r[1] for r in rows}
        raise ValueError("不支持的连接池类型")

    async def fetch_order_ids_by_nos(self, order_nos: List[str]) -> Dict[str, int]:
        """根据订单编码获取对应的Id（使用指定连接池）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholder = ",".join(["%s"] * len(order_nos))
                    sql = f"SELECT OrderNo, Id FROM tb_orderinfo WHERE OrderNo IN ({placeholder}) AND Deleted=0"
                    await cur.execute(sql, tuple(order_nos))
                    rows = await cur.fetchall()
                    return {r[0]: r[1] for r in rows}
        raise ValueError("不支持的连接池类型")

    async def fetch_deleted_order_by_no(self, order_no: str, deleted_by_id: str = None) -> Optional[Dict]:
        """根据订单编码查询已删除的订单（Deleted=1），验证唯一性"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 构建查询条件
                    if deleted_by_id:
                        count_sql = "SELECT COUNT(*) FROM tb_orderinfo WHERE OrderNo = %s AND Deleted=1 AND DeletedById = %s"
                        await cur.execute(count_sql, (order_no, deleted_by_id))
                    else:
                        count_sql = "SELECT COUNT(*) FROM tb_orderinfo WHERE OrderNo = %s AND Deleted=1"
                        await cur.execute(count_sql, (order_no,))
                    
                    count_row = await cur.fetchone()
                    count = count_row[0] if count_row else 0
                    
                    # 如果不是恰好1条，返回None表示验证失败
                    if count != 1:
                        return None
                    
                    # 查询唯一的那条记录
                    if deleted_by_id:
                        sql = "SELECT Id, OrderNo, Deleted, DeletedById FROM tb_orderinfo WHERE OrderNo = %s AND Deleted=1 AND DeletedById = %s"
                        await cur.execute(sql, (order_no, deleted_by_id))
                    else:
                        sql = "SELECT Id, OrderNo, Deleted, DeletedById FROM tb_orderinfo WHERE OrderNo = %s AND Deleted=1"
                        await cur.execute(sql, (order_no,))
                    
                    row = await cur.fetchone()
                    if row:
                        return {"id": row[0], "order_no": row[1], "deleted": row[2], "deleted_by_id": row[3] if len(row) > 3 else None}
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


order_service = OrderService()
