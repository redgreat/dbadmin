from typing import Dict, List, Optional, Tuple
import aiomysql

from app.services.db_pool import db_pool
from app.controllers.conn import conn_controller
from app.settings.config import settings

# 仓储中心固定连接的Id（需要用户配置）
conn_id = settings.WMS_CONN_ID


class WmsService:
    """仓储中心业务服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        pool = db_pool.get_pool(conn_id)
        if pool is not None:
            return
        conn = await conn_controller.get_decrypted_connection(conn_id)
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

    async def delete_logical_batch(self, stock_ids: List[str]) -> Tuple[int, List[str]]:
        """批量逻辑删除单据（逐行调用存储过程）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        for did in stock_ids:
            try:
                stock_id = int(did)
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 调用存储过程：逻辑删除单据，参数：stock_id
                            # 注意：存储过程名称需要用户自己编写，例如：sp_wms_delete_document_logical
                            await cur.execute("CALL sp_wms_delete_document_logical(%s)", (stock_id,))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(str(did))
        return success, failed

    async def delete_physical_batch(self, stock_ids: List[str]) -> Tuple[int, List[str]]:
        """批量物理删除单据（逐行调用存储过程）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        for did in stock_ids:
            try:
                stock_id = int(did)
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 调用存储过程：物理删除单据，参数：stock_id
                            # 注意：存储过程名称需要用户自己编写，例如：sp_wms_delete_document_physical
                            await cur.execute("CALL sp_wms_delete_document_physical(%s)", (stock_id,))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(str(did))
        return success, failed

    async def restore_logical(self, stock_id: int, operator_id: int) -> bool:
        """恢复逻辑删除的单据"""
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 调用存储过程：恢复单据，参数：stock_id, operator_id
                    # 注意：存储过程名称需要用户自己编写，例如：sp_wms_restore_document
                    await cur.execute("CALL sp_wms_restore_document(%s, %s)", (stock_id, operator_id))
                    return True
        raise ValueError("不支持的连接池类型")


wms_service = WmsService()
