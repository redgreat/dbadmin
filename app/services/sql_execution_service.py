from typing import List, Dict, Any, Optional, Tuple
import asyncpg
import aiomysql
from app.models.conn import DBConnection
from app.controllers.conn import conn_controller
from app.services.db_pool import db_pool
from app.log import logger


class SQLExecutionService:
    """SQL执行服务"""

    @staticmethod
    async def get_connection(db_conn: DBConnection):
        """
        获取数据库连接（密码解密后使用）
        """
        try:
            logger.info(f"获取解密连接信息, db_conn.id: {db_conn.id}")
            # 获取解密后的连接信息
            conn_info = await conn_controller.get_decrypted_connection(db_conn.id)
            logger.info(f"解密连接信息: {conn_info is not None}")
            if not conn_info:
                raise ValueError("无法解密数据库连接密码，请重新保存连接配置")

            logger.info(f"连接类型: {conn_info['db_type']}, 主机: {conn_info['host']}")
            
            if conn_info["db_type"] == "mysql":
                conn = await aiomysql.connect(
                    host=conn_info["host"],
                    port=conn_info["port"],
                    user=conn_info["username"],
                    password=conn_info["password"],
                    db=conn_info["database"],
                    charset='utf8mb4'
                )
                logger.info("MySQL连接成功")
                return conn
            elif conn_info["db_type"] == "postgresql":
                conn = await asyncpg.connect(
                    host=conn_info["host"],
                    port=conn_info["port"],
                    user=conn_info["username"],
                    password=conn_info["password"],
                    database=conn_info["database"]
                )
                logger.info("PostgreSQL连接成功")
                return conn
            else:
                raise ValueError(f"不支持的数据库类型: {conn_info['db_type']}")
        except Exception as e:
            logger.error(f"获取数据库连接失败: {str(e)}")
            raise

    @staticmethod
    async def execute_query(
        db_conn: DBConnection,
        sql: str,
        offset: int = 0,
        limit: int = 1000
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        执行SQL查询（分页）
        :param db_conn: 数据库连接对象
        :param sql: SQL语句
        :param offset: 偏移量
        :param limit: 限制数量
        :return: (数据列表, 总数)
        """
        conn = None
        try:
            conn = await SQLExecutionService.get_connection(db_conn)

            # 移除SQL末尾的分号，避免语法错误
            sql = sql.strip().rstrip(';')

            if db_conn.db_type == "mysql":
                # MySQL查询
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 获取总数
                    count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as count_table"
                    await cursor.execute(count_sql)
                    count_result = await cursor.fetchone()
                    total = count_result['total'] if count_result else 0

                    # 获取数据
                    data_sql = f"{sql} LIMIT {offset}, {limit}"
                    await cursor.execute(data_sql)
                    rows = await cursor.fetchall()

                    return list(rows), total

            elif db_conn.db_type == "postgresql":
                # PostgreSQL查询
                # 获取总数
                count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as count_table"
                count_result = await conn.fetchrow(count_sql)
                total = count_result['total'] if count_result else 0

                # 获取数据
                data_sql = f"{sql} OFFSET {offset} LIMIT {limit}"
                rows = await conn.fetch(data_sql)

                # 转换为字典列表
                result = [dict(row) for row in rows]
                return result, total

            else:
                raise ValueError(f"不支持的数据库类型: {db_conn.db_type}")

        except Exception as e:
            logger.error(f"执行SQL查询失败: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

    @staticmethod
    async def get_total_count(db_conn: DBConnection, sql: str) -> int:
        """
        获取SQL查询的总数
        """
        conn = None
        try:
            conn = await SQLExecutionService.get_connection(db_conn)

            # 移除SQL末尾的分号，避免语法错误
            sql = sql.strip().rstrip(';')

            if db_conn.db_type == "mysql":
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as count_table"
                    await cursor.execute(count_sql)
                    result = await cursor.fetchone()
                    if result is None:
                        return 0
                    return result['total']

            elif db_conn.db_type == "postgresql":
                count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as count_table"
                result = await conn.fetchrow(count_sql)
                if result is None:
                    return 0
                return result['total']

            else:
                raise ValueError(f"不支持的数据库类型: {db_conn.db_type}")

        except Exception as e:
            logger.error(f"获取总数失败: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
