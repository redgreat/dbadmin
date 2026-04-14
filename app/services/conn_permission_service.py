from fastapi import HTTPException
from tortoise.expressions import Q

from app.models.admin import User

ADMIN_ROLE_NAMES = {"admin", "管理员"}


async def is_admin_user(user: User) -> bool:
    if not user:
        return False
    if user.is_superuser:
        return True
    role_names = await user.roles.all().values_list("name", flat=True)
    return any((name or "").strip().lower() == "admin" or name in ADMIN_ROLE_NAMES for name in role_names)


async def get_authorized_conn_ids(user: User):
    if await is_admin_user(user):
        return None
    conn_ids = await user.conn_permissions.all().values_list("id", flat=True)
    return set(int(conn_id) for conn_id in conn_ids)


async def apply_conn_permission_filter(search_q: Q, user: User) -> Q:
    conn_ids = await get_authorized_conn_ids(user)
    if conn_ids is None:
        return search_q
    if not conn_ids:
        return search_q & Q(id=-1)
    return search_q & Q(id__in=list(conn_ids))


async def ensure_conn_access(user: User, conn_id: int, action: str = "使用该连接"):
    if not conn_id:
        return
    conn_ids = await get_authorized_conn_ids(user)
    if conn_ids is None:
        return
    if int(conn_id) not in conn_ids:
        raise HTTPException(status_code=403, detail=f"无权限{action}")
