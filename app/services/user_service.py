"""用户中心服务 - 从用户中心数据库查询用户信息"""
from typing import Dict, List, Optional
import aiomysql
import logging

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

# 用户中心固定连接的Id（延迟获取，避免模块加载时Tortoise未初始化）
_user_conn_id = None


async def _get_conn_id() -> int:
    """获取用户中心连接ID"""
    global _user_conn_id
    if _user_conn_id is None:
        _user_conn_id = await settings.USER_CONN_ID()
    return _user_conn_id


class UserService:
    """用户中心服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is not None:
            return
        from app.controllers.conn import conn_controller
        conn = await conn_controller.get_decrypted_connection(await _get_conn_id())
        if not conn:
            raise ValueError("用户中心连接池不存在")
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

    async def search_users(self, keyword: str, limit: int = 20) -> List[Dict]:
        """根据姓名模糊查询用户列表

        Args:
            keyword: 姓名筛选值（前缀/包含匹配）
            limit: 最多返回条数

        Returns:
            用户列表 [{id, name}, ...]
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("用户中心连接池不存在")

        results: List[Dict] = []
        keyword = (keyword or "").strip()
        if not keyword:
            return results

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = """
                        SELECT Id, Name FROM basic_userinfo
                        WHERE Name LIKE %s
                        ORDER BY Name
                        LIMIT %s
                    """
                    await cur.execute(sql, (f"%{keyword}%", limit))
                    rows = await cur.fetchall()
                    for row in rows:
                        results.append({
                            "id": str(row[0]),
                            "name": str(row[1]) if row[1] is not None else "",
                        })
        else:
            raise ValueError("不支持的连接池类型")

        return results

    async def get_user_by_name(self, name: str) -> Optional[Dict]:
        """根据姓名精确查询用户

        Args:
            name: 姓名精确值

        Returns:
            用户信息 {id, name}，未找到返回 None
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("用户中心连接池不存在")

        name = (name or "").strip()
        if not name:
            return None

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = "SELECT Id, Name FROM basic_userinfo WHERE Name=%s LIMIT 1"
                    await cur.execute(sql, (name,))
                    row = await cur.fetchone()
                    if row:
                        return {
                            "id": str(row[0]),
                            "name": str(row[1]) if row[1] is not None else "",
                        }
        else:
            raise ValueError("不支持的连接池类型")

        return None


user_service = UserService()
