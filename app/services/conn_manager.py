from typing import Dict, Optional, List, Any, Tuple
from tortoise import connections
import asyncpg
import aiomysql
from app.log import logger


class DBConnectionManager:
    """
    数据库连接管理器
    提供动态数据库连接的获取和查询执行功能
    """
    
    @staticmethod
    async def get_connection_by_id(conn_id: int):
        """
        根据连接ID获取数据库连接
        """
        try:
            return connections.get(f"conn_{conn_id}")
        except KeyError:
            logger.error(f"连接 conn_{conn_id} 不存在")
            return None
    
    @staticmethod
    def get_connection_info(conn_id: int) -> Optional[Dict[str, Any]]:
        """
        获取连接信息
        """
        return None
    
    @staticmethod
    def list_all_connections() -> Dict[str, Dict[str, Any]]:
        """
        列出所有动态连接
        """
        return {}
    
    @staticmethod
    async def execute_query(conn_id: int, sql: str, params: Optional[List] = None) -> List[Dict]:
        """
        在指定连接上执行查询
        """
        connection = await DBConnectionManager.get_connection_by_id(conn_id)
        if not connection:
            raise ValueError(f"连接ID {conn_id} 对应的数据库连接不存在")
        
        try:
            if params:
                result = await connection.execute_query(sql, params)
            else:
                result = await connection.execute_query(sql)
            return result
        except Exception as e:
            logger.error(f"执行查询失败 (连接ID: {conn_id}): {str(e)}")
            raise
    
    @staticmethod
    async def execute_update(conn_id: int, sql: str, params: Optional[List] = None) -> int:
        """
        在指定连接上执行更新操作
        """
        connection = await DBConnectionManager.get_connection_by_id(conn_id)
        if not connection:
            raise ValueError(f"连接ID {conn_id} 对应的数据库连接不存在")
        
        try:
            if params:
                result = await connection.execute_query(sql, params)
            else:
                result = await connection.execute_query(sql)
            return result[0] if isinstance(result, tuple) else result
        except Exception as e:
            logger.error(f"执行更新失败 (连接ID: {conn_id}): {str(e)}")
            raise


class DBConnector:
    """
    数据库连接器服务
    """

    @staticmethod
    async def test_postgresql_connection(
        host: str, port: int, username: str, password: str, database: str, params: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        测试PostgreSQL连接
        """
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
        """
        测试MySQL连接
        """
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
        """
        测试数据库连接
        """
        if db_type == "postgresql":
            return await DBConnector.test_postgresql_connection(host, port, username, password, database, params)
        elif db_type == "mysql":
            return await DBConnector.test_mysql_connection(host, port, username, password, database, params)
        else:
            return False, f"不支持的数据库类型: {db_type}"


# 创建全局实例
db_manager = DBConnectionManager()
db_connector = DBConnector()
