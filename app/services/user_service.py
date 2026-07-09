"""OA用户信息服务 - 从OA数据库查询人员信息（仅内勤人员）"""
from typing import Dict, List
import aiomysql
import logging

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

# OA固定连接的Id（延迟获取，避免模块加载时Tortoise未初始化）
_user_conn_id = None


async def _get_conn_id() -> int:
    """获取OA连接ID"""
    global _user_conn_id
    if _user_conn_id is None:
        _user_conn_id = await settings.USER_CONN_ID()
    return _user_conn_id


class UserService:
    """OA用户信息服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is not None:
            return
        from app.controllers.conn import conn_controller
        conn = await conn_controller.get_decrypted_connection(await _get_conn_id())
        if not conn:
            raise ValueError("OA连接池不存在")
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
        """根据关键字模糊查询 OA 内勤人员

        Args:
            keyword: 姓名/编码/UserCenterUserId 任意字段
            limit: 最多返回条数

        Returns:
            [{user_center_user_id, user_name, code}, ...]
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("OA连接池不存在")

        results: List[Dict] = []
        keyword = (keyword or "").strip()
        if not keyword:
            return results

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    sql = """
                        SELECT UserName, Code, UserCenterUserId
                        FROM membership_userbaseinfo
                        WHERE Deleted=0
                          AND UserType <> 'DT0000000501'
                          AND (UserName LIKE %s OR Code LIKE %s OR UserCenterUserId LIKE %s)
                        ORDER BY CreatedAt
                        LIMIT %s
                    """
                    like_kw = f"%{keyword}%"
                    await cur.execute(sql, (like_kw, like_kw, like_kw, limit))
                    rows = await cur.fetchall()
                    for row in rows:
                        results.append({
                            "user_name": str(row[0]) if row[0] is not None else "",
                            "code": str(row[1]) if row[1] is not None else "",
                            "user_center_user_id": str(row[2]) if row[2] is not None else "",
                        })
        else:
            raise ValueError("不支持的连接池类型")

        return results


user_service = UserService()
