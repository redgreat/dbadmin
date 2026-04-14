from typing import List, Dict, Any, Optional, Tuple
import asyncpg
import aiomysql


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
                    charset='utf8mb4',
                    connect_timeout=30,
                    autocommit=True,
                )
                logger.info("MySQL连接成功")
                return conn
            elif conn_info["db_type"] == "postgresql":
                conn = await asyncpg.connect(
                    host=conn_info["host"],
                    port=conn_info["port"],
                    user=conn_info["username"],
                    password=conn_info["password"],
                    database=conn_info["database"],
                    # 长查询优化（硬编码，避免配置复杂化）
                    command_timeout=7200,  # 2小时命令超时（适合大多数场景）
                    statement_cache_size=0,  # 禁用语句缓存
                    max_cached_statement_lifetime=0,
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
    async def execute_query_page(
        db_conn: DBConnection,
        sql: str,
        offset: int = 0,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        执行SQL分页查询（不统计总数，供大报表导出使用）
        :param db_conn: 数据库连接对象
        :param sql: SQL语句
        :param offset: 偏移量
        :param limit: 限制数量
        :return: 数据列表
        """
        conn = None
        try:
            conn = await SQLExecutionService.get_connection(db_conn)

            # 移除SQL末尾的分号，避免语法错误
            sql = sql.strip().rstrip(';')

            if db_conn.db_type == "mysql":
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    data_sql = f"{sql} LIMIT {offset}, {limit}"
                    await cursor.execute(data_sql)
                    rows = await cursor.fetchall()
                    return list(rows)

            if db_conn.db_type == "postgresql":
                # 设置会话级超时参数（硬编码，避免配置复杂化）
                await conn.execute("SET statement_timeout = '2 hours'")
                await conn.execute("SET idle_in_transaction_session_timeout = '2 hours'")
                data_sql = f"{sql} OFFSET {offset} LIMIT {limit}"
                rows = await conn.fetch(data_sql)
                return [dict(row) for row in rows]

            raise ValueError(f"不支持的数据库类型: {db_conn.db_type}")

        except Exception as e:
            logger.error(f"执行SQL分页查询失败: {str(e)}")
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

    @staticmethod
    async def execute_query_stream_mysql(
        db_conn: DBConnection,
        sql: str,
        batch_size: int = 1000,
    ):
        """
        MySQL流式查询（单次执行SQL，按批次拉取，避免深分页性能问题）
        :yield: 每批数据列表
        """
        if db_conn.db_type != "mysql":
            raise ValueError("execute_query_stream_mysql 仅支持 MySQL 连接")

        conn = None
        try:
            conn = await SQLExecutionService.get_connection(db_conn)
            sql = sql.strip().rstrip(';')
            async with conn.cursor(aiomysql.SSDictCursor) as cursor:
                # 长查询场景下尽量放宽会话级超时，避免中途断流（硬编码）
                try:
                    await cursor.execute("SET SESSION wait_timeout=7200")  # 2小时
                    await cursor.execute("SET SESSION interactive_timeout=7200")  # 2小时
                    await cursor.execute("SET SESSION net_read_timeout=600")  # 10分钟
                    await cursor.execute("SET SESSION net_write_timeout=600")  # 10分钟
                    await cursor.execute("SET SESSION max_execution_time=7200000")  # 2小时（毫秒）
                except Exception as timeout_set_err:
                    logger.warning(f"设置MySQL会话超时参数失败(忽略): {timeout_set_err}")

                await cursor.execute(sql)
                while True:
                    rows = await cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    yield list(rows)
        except Exception as e:
            logger.error(f"MySQL流式查询失败: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
