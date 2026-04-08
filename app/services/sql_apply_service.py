import hashlib
from typing import List

import aiomysql
import asyncpg
import sqlparse

from app.controllers.conn import conn_controller


ALLOWED_SQL_PREFIXES = (
    "CREATE TABLE",
    "INSERT INTO",
    "CREATE INDEX",
)


def calc_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _strip_leading_comments(stmt: str) -> str:
    """移除语句前置注释，避免白名单匹配被注释头干扰。"""
    s = stmt.lstrip()
    while s:
        if s.startswith("--"):
            nl = s.find("\n")
            if nl == -1:
                return ""
            s = s[nl + 1 :].lstrip()
            continue
        if s.startswith("/*"):
            end = s.find("*/")
            if end == -1:
                return ""
            s = s[end + 2 :].lstrip()
            continue
        break
    return s


def validate_excel_generated_sql(sql_text: str) -> List[str]:
    if not sql_text:
        raise ValueError("SQL内容为空")
    if "-- GENERATED_BY:EXCELIMP" not in sql_text:
        raise ValueError("仅允许执行Excel生成的SQL文件")

    statements = [stmt.strip() for stmt in sqlparse.split(sql_text) if stmt.strip()]
    if not statements:
        raise ValueError("未解析到可执行SQL语句")

    for stmt in statements:
        normalized = _strip_leading_comments(stmt)
        if not normalized:
            continue
        upper_stmt = normalized.upper()
        if not upper_stmt.startswith(ALLOWED_SQL_PREFIXES):
            raise ValueError(f"检测到不允许的SQL语句: {stmt[:80]}")
    return [s for s in statements if _strip_leading_comments(s)]


async def execute_sql_on_connection(conn_id: int, sql_text: str) -> dict:
    conn_info = await conn_controller.get_decrypted_connection(conn_id)
    if not conn_info:
        raise ValueError("目标连接不存在或密码不可用")

    statements = validate_excel_generated_sql(sql_text)
    db_type = conn_info["db_type"]
    executed = 0

    if db_type == "mysql":
        conn = await aiomysql.connect(
            host=conn_info["host"],
            port=conn_info["port"],
            user=conn_info["username"],
            password=conn_info["password"],
            db=conn_info["database"],
            charset="utf8mb4",
            autocommit=False,
        )
        try:
            async with conn.cursor() as cur:
                for stmt in statements:
                    await cur.execute(stmt)
                    executed += 1
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            conn.close()
    elif db_type == "postgresql":
        conn = await asyncpg.connect(
            host=conn_info["host"],
            port=conn_info["port"],
            user=conn_info["username"],
            password=conn_info["password"],
            database=conn_info["database"],
        )
        try:
            async with conn.transaction():
                for stmt in statements:
                    await conn.execute(stmt)
                    executed += 1
        finally:
            await conn.close()
    else:
        raise ValueError(f"暂不支持该连接类型执行导入: {db_type}")

    return {"executed_count": executed, "db_type": db_type}
