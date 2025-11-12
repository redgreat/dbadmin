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

    @staticmethod
    def build_dsn(
        db_type: str, host: str, port: int, username: str, password: str, database: str, params: Optional[str] = None
    ) -> str:
        """根据连接参数生成 DSN 连接串"""
        query = f"?{params}" if params else ""
        if db_type == "postgresql":
            return f"postgresql://{username}:{password}@{host}:{port}/{database}{query}"
        if db_type == "mysql":
            return f"mysql://{username}:{password}@{host}:{port}/{database}{query}"
        raise ValueError(f"不支持的数据库类型: {db_type}")

    @staticmethod
    async def fetch_orders_audit_time(order_ids: list[str]) -> Dict[str, Optional[str]]:
        """根据订单Id获取审核时间（占位实现，后续接入外部数据库）"""
        return {str(i): None for i in order_ids}

    @staticmethod
    async def update_orders_audit_time(order_ids: list[str], new_time) -> int:
        """批量更新订单审核时间（占位实现，后续接入外部数据库）"""
        return 0

    @staticmethod
    async def delete_orders_logical(order_ids: list[str]) -> Tuple[int, list[str]]:
        """批量逻辑删除订单（占位实现，逐行调用存储过程）"""
        success = 0
        failed: list[str] = []
        for oid in order_ids:
            try:
                # 调用逻辑删除存储过程，占位
                success += 1
            except Exception:
                failed.append(oid)
        return success, failed

    @staticmethod
    async def delete_orders_physical(order_ids: list[str]) -> Tuple[int, list[str]]:
        """批量物理删除订单（占位实现，逐行调用存储过程）"""
        success = 0
        failed: list[str] = []
        for oid in order_ids:
            try:
                # 调用物理删除存储过程，占位
                success += 1
            except Exception:
                failed.append(oid)
        return success, failed


db_connector = DBConnector()
