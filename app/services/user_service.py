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

    async def batch_get_by_user_center_ids(self, user_center_user_ids: List[str]) -> Dict[str, Dict]:
        """根据多个 UserCenterUserId 批量查询 OA 人员信息

        Args:
            user_center_user_ids: UserCenterUserId 列表

        Returns:
            {user_center_user_id: {user_name, code, user_center_user_id}, ...}
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("OA连接池不存在")

        result: Dict[str, Dict] = {}
        ids = [str(i).strip() for i in (user_center_user_ids or []) if i and str(i).strip()]
        if not ids:
            return result

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(ids))
                    sql = f"""
                        SELECT UserName, Code, UserCenterUserId
                        FROM membership_userbaseinfo
                        WHERE Deleted=0
                          AND UserType <> 'DT0000000501'
                          AND UserCenterUserId IN ({placeholders})
                    """
                    await cur.execute(sql, tuple(ids))
                    rows = await cur.fetchall()
                    for row in rows:
                        ucu_id = str(row[2]) if row[2] is not None else ""
                        if ucu_id:
                            result[ucu_id] = {
                                "user_name": str(row[0]) if row[0] is not None else "",
                                "code": str(row[1]) if row[1] is not None else "",
                                "user_center_user_id": ucu_id,
                            }
        else:
            raise ValueError("不支持的连接池类型")

        return result

    async def get_user_names_by_user_center_ids(self, user_center_ids: List[str]) -> Dict[str, str]:
        """根据UserCenterUserId批量获取用户姓名，返回 {user_center_user_id: user_name}"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("OA连接池不存在")

        result: Dict[str, str] = {}
        valid_ids = list(set(uid for uid in user_center_ids if uid))
        if not valid_ids:
            return result

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(valid_ids))
                    sql = f"""
                        SELECT UserCenterUserId, UserName
                        FROM membership_userbaseinfo
                        WHERE UserCenterUserId IN ({placeholders})
                    """
                    await cur.execute(sql, valid_ids)
                    rows = await cur.fetchall()
                    for row in rows:
                        uid = str(row[0]) if row[0] is not None else ""
                        name = str(row[1]) if row[1] is not None else ""
                        if uid:
                            result[uid] = name
        else:
            raise ValueError("不支持的连接池类型")

        return result

    async def get_local_user_display_names(self, user_ids: List[str]) -> Dict[str, str]:
        """从本库 user 表查询用户姓名，作为 OA 查不到的降级

        DeletedById 实际存的是本库 membership_user / user 表的 Id，
        当 OA 中查不到对应记录时，用此方法从本库获取 DisplayName(alias)

        Args:
            user_ids: 用户 Id 列表（来自 DeletedById）

        Returns:
            {user_id: display_name, ...}
        """
        from app.models.admin import User

        result: Dict[str, str] = {}
        int_ids = []
        for uid in user_ids:
            try:
                int_ids.append(int(uid))
            except (ValueError, TypeError):
                pass
        if not int_ids:
            return result

        try:
            users = await User.filter(id__in=int_ids).values("id", "alias")
            for u in users:
                uid = str(u["id"]) if u["id"] is not None else ""
                name = u.get("alias") or ""
                if uid:
                    result[uid] = name
        except Exception as e:
            logger.warning(f"本库用户查询降级失败: {e}")

        return result


user_service = UserService()
