import asyncio
import logging
from typing import Dict, Optional, Union

import asyncpg
import aiomysql
import aioodbc

logger = logging.getLogger(__name__)


class DBPoolManager:
    """数据库连接池管理服务"""

    def __init__(self):
        self._pools: Dict[int, Union[asyncpg.Pool, aiomysql.Pool, aioodbc.Pool]] = {}
        self._configs: Dict[int, dict] = {}
        self._locks: Dict[int, asyncio.Lock] = {}

    def _get_lock(self, conn_id: int) -> asyncio.Lock:
        if conn_id not in self._locks:
            self._locks[conn_id] = asyncio.Lock()
        return self._locks[conn_id]

    async def register_pool(
        self,
        conn_id: int,
        db_type: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database: str,
        params: Optional[str] = None,
        min_size: int = 1,
        max_size: int = 10,
    ):
        """创建并注册连接池"""
        self._configs[conn_id] = {
            "conn_id": conn_id,
            "db_type": db_type,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
            "params": params,
            "min_size": min_size,
            "max_size": max_size,
        }

        old_pool = self._pools.pop(conn_id, None)
        if old_pool:
            await self._close_pool_obj(old_pool)

        if db_type == "postgresql":
            pool = await asyncpg.create_pool(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                min_size=min_size,
                max_size=max_size,
                max_inactive_connection_lifetime=300,
            )
            self._pools[conn_id] = pool
            return pool
        if db_type == "mysql":
            pool = await aiomysql.create_pool(
                host=host,
                port=port,
                user=username,
                password=password,
                db=database,
                minsize=min_size,
                maxsize=max_size,
                autocommit=True,
                pool_recycle=1800,
            )
            self._pools[conn_id] = pool
            return pool
        if db_type == "sqlserver":
            # SQL Server使用ODBC连接字符串
            # 格式: DRIVER={ODBC Driver 18 for SQL Server};SERVER=host,port;DATABASE=database;UID=username;PWD=password
            # Encrypt=no 和 TrustServerCertificate=yes 用于解决 ODBC Driver 18 的 SSL 证书验证问题
            conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={host},{port};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                f"Encrypt=no;"
                f"TrustServerCertificate=yes"
            )
            if params:
                conn_str += f";{params}"
            
            pool = await aioodbc.create_pool(
                dsn=conn_str,
                minsize=min_size,
                maxsize=max_size,
            )
            self._pools[conn_id] = pool
            return pool
        raise ValueError("不支持的数据库类型")

    def get_pool(self, conn_id: int) -> Optional[Union[asyncpg.Pool, aiomysql.Pool, aioodbc.Pool]]:
        """获取已注册连接池"""
        return self._pools.get(conn_id)

    async def ensure_pool(self, conn_id: int) -> Union[asyncpg.Pool, aiomysql.Pool, aioodbc.Pool]:
        """获取连接池；不存在或已关闭时按连接表配置自动重建。"""
        pool = self._pools.get(conn_id)
        if pool and not self._is_pool_closed(pool):
            return pool

        async with self._get_lock(conn_id):
            pool = self._pools.get(conn_id)
            if pool and not self._is_pool_closed(pool):
                return pool

            config = self._configs.get(conn_id)
            if not config:
                config = await self._load_config_from_db(conn_id)
            if not config:
                raise ValueError(f"数据库连接 {conn_id} 不存在或密码无法解密")

            logger.info(f"[连接池] 自动创建数据库连接池: conn_id={conn_id}")
            return await self.register_pool(**config)

    async def reconnect_pool(self, conn_id: int) -> Union[asyncpg.Pool, aiomysql.Pool, aioodbc.Pool]:
        """强制关闭旧连接池并重建，用于处理 MySQL/PG 空闲连接被服务端断开。"""
        async with self._get_lock(conn_id):
            await self.close_pool(conn_id, keep_config=True)
            config = self._configs.get(conn_id)
            if not config:
                config = await self._load_config_from_db(conn_id)
            if not config:
                raise ValueError(f"数据库连接 {conn_id} 不存在或密码无法解密")

            logger.info(f"[连接池] 自动重连数据库: conn_id={conn_id}")
            return await self.register_pool(**config)

    async def close_pool(self, conn_id: int, keep_config: bool = False):
        """关闭并移除连接池"""
        pool = self._pools.get(conn_id)
        if pool:
            try:
                await self._close_pool_obj(pool)
            finally:
                self._pools.pop(conn_id, None)
        if not keep_config:
            self._configs.pop(conn_id, None)

    def _is_pool_closed(self, pool) -> bool:
        closed = getattr(pool, "closed", None)
        if closed is not None:
            return bool(closed)
        return False

    async def _close_pool_obj(self, pool):
        close = getattr(pool, "close", None)
        if not close:
            return
        result = close()
        if asyncio.iscoroutine(result):
            await result
        wait_closed = getattr(pool, "wait_closed", None)
        if wait_closed:
            result = wait_closed()
            if asyncio.iscoroutine(result):
                await result

    async def _load_config_from_db(self, conn_id: int) -> Optional[dict]:
        from app.controllers.conn import conn_controller

        conn = await conn_controller.get_decrypted_connection(conn_id)
        if not conn:
            return None
        return {
            "conn_id": conn["id"],
            "db_type": conn["db_type"],
            "host": conn["host"],
            "port": conn["port"],
            "username": conn["username"],
            "password": conn["password"],
            "database": conn["database"],
            "params": conn["params"],
        }


def is_connection_error(exc: Exception) -> bool:
    """判断是否为可通过重连恢复的数据库连接异常。"""
    connection_error_types = tuple(t for t in (
        aiomysql.OperationalError,
        aiomysql.InterfaceError,
        getattr(asyncpg, "PostgresConnectionError", None),
        getattr(asyncpg, "InterfaceError", None),
        OSError,
    ) if t is not None)
    if isinstance(exc, connection_error_types):
        return True

    msg = str(exc).lower()
    return any(
        marker in msg
        for marker in (
            "server has gone away",
            "lost connection",
            "connection reset",
            "connection closed",
            "closed connection",
            "connection refused",
            "terminating connection",
        )
    )


db_pool = DBPoolManager()
