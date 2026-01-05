from typing import Dict, List, Optional, Tuple
import re
import aiomysql

from app.services.db_pool import db_pool

# 订单固定连接的Id
conn_id = 4

class OrderService:
    """订单业务服务"""

    async def fetch_audit_time_map(self, order_ids: List[str]) -> Dict[str, Optional[str]]:
        """根据订单Id获取审核时间（使用指定连接池）"""
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        ids_int = [int(x) for x in order_ids]
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholder = ",".join(["%s"] * len(ids_int))
                    sql = f"SELECT id, AuditTime FROM tb_orderinfo WHERE id IN ({placeholder})"
                    await cur.execute(sql, tuple(ids_int))
                    rows = await cur.fetchall()
                    return {str(r[0]): r[1] for r in rows}
        raise ValueError("不支持的连接池类型")

    async def update_audit_time_batch(self, order_ids: List[str], new_time) -> int:
        """批量更新订单审核时间（使用指定连接池）"""
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        ids_int = [int(x) for x in order_ids]
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholder = ",".join(["%s"] * len(ids_int))
                    sql = f"UPDATE tb_orderinfo SET AuditTime = %s WHERE id IN ({placeholder})"
                    await cur.execute(sql, tuple([new_time, *ids_int]))
                    return cur.rowcount or 0
        raise ValueError("不支持的连接池类型")

    async def delete_logical_batch(self, order_ids: List[str]) -> Tuple[int, List[str]]:
        """批量逻辑删除订单（逐行调用存储过程）"""
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        for oid in order_ids:
            try:
                order_id = int(oid)
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute("CALL proc_DeleteOrderInfoById(%s)", (order_id,))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(str(oid))
        return success, failed

    async def delete_physical_batch(self, order_ids: List[str]) -> Tuple[int, List[str]]:
        """批量物理删除订单（逐行调用存储过程）"""
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        for oid in order_ids:
            try:
                order_id = int(oid)
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute("CALL proc_TruncateOrderInfoById(%s)", (order_id,))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(str(oid))
        return success, failed

    async def restore_logical(self, order_id: int, operator_id: int) -> bool:
        """恢复逻辑删除的订单"""
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("CALL proc_RestoreOrderInfoById(%s, %s)", (order_id, operator_id))
                    return True
        raise ValueError("不支持的连接池类型")


order_service = OrderService()
