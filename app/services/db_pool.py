import asyncio
from typing import Dict, Optional, Union

import asyncpg
import aiomysql
import aioodbc


class DBPoolManager:
    """数据库连接池管理服务"""

    def __init__(self):
        self._pools: Dict[int, Union[asyncpg.Pool, aiomysql.Pool, aioodbc.Pool]] = {}

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
        if db_type == "postgresql":
            pool = await asyncpg.create_pool(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                min_size=min_size,
                max_size=max_size,
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

    async def close_pool(self, conn_id: int):
        """关闭并移除连接池"""
        pool = self._pools.get(conn_id)
        if pool:
            try:
                await pool.close()
            finally:
                self._pools.pop(conn_id, None)


db_pool = DBPoolManager()

