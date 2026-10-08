from datetime import datetime

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from app.core.ctx import CTX_USER_ID
from app.models.admin import AuditLog, User
from app.schemas import SuccessExtra
from app.schemas.apis import *

router = APIRouter()


@router.get("/list", summary="查看操作日志")
async def get_audit_log_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str | None = Query(None, description="操作人名称"),
    module: str | None = Query(None, description="功能模块"),
    method: str | None = Query(None, description="请求方法"),
    summary: str | None = Query(None, description="接口描述"),
    path: str | None = Query(None, description="请求路径"),
    status: str | None = Query(None, description="状态码"),
    start_time: str | None = Query(None, description="开始时间"),
    end_time: str | None = Query(None, description="结束时间"),
):
    def _parse_dt(v: str | None):
        # 兼容前端传空字符串 "" 的情况，避免 422
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        if isinstance(v, datetime):
            return v
        try:
            # 兼容 "YYYY-MM-DD HH:mm:ss" 与 ISO 格式
            return datetime.fromisoformat(v.replace(" ", "T") if " " in v and "T" not in v else v)
        except ValueError:
            # 回退尝试常见格式
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
            return None

    start_dt = _parse_dt(start_time)
    end_dt = _parse_dt(end_time)
    # 数据权限：超级管理员可看全部；普通用户仅能看自己的数据
    current_user = await User.filter(id=CTX_USER_ID.get()).first()
    q = Q()
    if current_user is not None and not current_user.is_superuser:
        # 普通用户强制过滤为自己的用户名，忽略前端传入的 username
        q &= Q(username=current_user.username)
    elif username:
        q &= Q(username__icontains=username)
    if module:
        q &= Q(module__icontains=module)
    if method:
        q &= Q(method__icontains=method)
    if summary:
        q &= Q(summary__icontains=summary)
    if path:
        q &= Q(path__icontains=path)
    if status is not None and (isinstance(status, int) or str(status).strip() != ""):
        try:
            q &= Q(status=int(status))
        except (TypeError, ValueError):
            pass
    if start_dt and end_dt:
        q &= Q(created_at__range=[start_dt, end_dt])
    elif start_dt:
        q &= Q(created_at__gte=start_dt)
    elif end_dt:
        q &= Q(created_at__lte=end_dt)

    audit_log_objs = await AuditLog.filter(q).offset((page - 1) * page_size).limit(page_size).order_by("-created_at")
    total = await AuditLog.filter(q).count()
    data = [await audit_log.to_dict() for audit_log in audit_log_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
