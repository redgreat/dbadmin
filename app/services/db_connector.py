import asyncio
from typing import Dict, Optional, Tuple

import asyncpg
import aiomysql


class DBConnector:
    """数据库连接器服务"""

    @staticmethod
    async def test_postgresql_connection(
        host: str, port: int, username: str, password: str, database: str, params: Optional[str] = None
    ) -> Tuple[bool, str]:
        """测试PostgreSQL连接"""
        try:
            conn = await asyncpg.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                timeout=5,
            )
            await conn.execute("SELECT 1")
            await conn.close()
            return True, "连接成功"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    @staticmethod
    async def test_mysql_connection(
        host: str, port: int, username: str, password: str, database: str, params: Optional[str] = None
    ) -> Tuple[bool, str]:
        """测试MySQL连接"""
        try:
            conn = await aiomysql.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                db=database,
                connect_timeout=5,
            )
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
            conn.close()
            return True, "连接成功"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    @staticmethod
    async def test_connection(
        db_type: str, host: str, port: int, username: str, password: str, database: str, params: Optional[str] = None
    ) -> Tuple[bool, str]:
        """测试数据库连接"""
        if db_type == "postgresql":
            return await DBConnector.test_postgresql_connection(host, port, username, password, database, params)
        elif db_type == "mysql":
            return await DBConnector.test_mysql_connection(host, port, username, password, database, params)
        else:
            return False, f"不支持的数据库类型: {db_type}"


db_connector = DBConnector()
