import logging
from datetime import datetime

from fastapi import APIRouter, Query

from tortoise.expressions import Q

from app.core.ctx import CTX_USER_ID
from app.models.admin import AuditLog, User
from app.schemas import SuccessExtra

logger = logging.getLogger(__name__)

router = APIRouter()

# 只统计“修改成功那刻”的写操作接口（查询类一律排除）。
# 与各 ehcf 路由中 create_operation_audit_log 的 path 保持一致（module="EHCF", status=200）。
WRITE_PATH_LABELS: dict[str, str] = {
    "/api/v1/ehcf/workorder-manage/delete_logical": "工单逻辑删除",
    "/api/v1/ehcf/workorder-manage/restore_logical": "工单逻辑删除恢复",
    "/api/v1/ehcf/workorder-manage/close": "工单关闭",
    "/api/v1/ehcf/workorder-manage/update_create_type": "修改工单单据来源",
    "/api/v1/ehcf/create-type/update": "修改单据来源(充电桩)",
    "/api/v1/ehcf/order-regenerate/fix_detail": "修复订单明细Id",
    "/api/v1/ehcf/order-regenerate/regenerate_order": "重新生成订单Id和明细Id",
    "/api/v1/ehcf/newaccept-refresh/execute": "执行车务待办人刷新",
    "/api/v1/ehcf/newaccept-refresh/refresh-by-batch": "按批次执行车务待办人刷新",
}


def _parse_dt(v: str | None):
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    if isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(v.replace(" ", "T") if " " in v and "T" not in v else v)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue
        return None


@router.get("/api-stat/list", summary="接口调用统计-成功修改")
async def get_ehcf_api_stat_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    username: str | None = Query(None, description="修改人（登录用户名）"),
    operator_id: str | None = Query(None, description="操作人Id（请求体中的 operator_id）"),
    path: str | None = Query(None, description="接口路径"),
    start_time: str | None = Query(None, description="开始时间"),
    end_time: str | None = Query(None, description="结束时间"),
):
    """只返回 module=EHCF 且 status=200 的写操作成功日志，查询类接口天然无手动审计日志故不会出现。"""
    start_dt = _parse_dt(start_time)
    end_dt = _parse_dt(end_time)

    q = Q(module="EHCF", status=200, path__in=list(WRITE_PATH_LABELS.keys()))

    # 数据权限：与审计日志保持一致，普通用户仅能看自己的数据
    current_user = await User.filter(id=CTX_USER_ID.get()).first()
    if current_user is not None and not current_user.is_superuser:
        q &= Q(username=current_user.username)
    elif username and username.strip():
        q &= Q(username__icontains=username.strip())

    if path and path.strip():
        # 前端传具体 path；非法 path 直接返回空，避免扫出查询类日志
        if path.strip() not in WRITE_PATH_LABELS:
            return SuccessExtra(data=[], total=0, page=page, page_size=page_size)
        q &= Q(path=path.strip())

    if operator_id and operator_id.strip():
        keyword = operator_id.strip()
        q &= Q(request_body__icontains=keyword) | Q(summary__icontains=keyword)

    if start_dt and end_dt:
        q &= Q(created_at__range=[start_dt, end_dt])
    elif start_dt:
        q &= Q(created_at__gte=start_dt)
    elif end_dt:
        q &= Q(created_at__lte=end_dt)

    objs = await AuditLog.filter(q).offset((page - 1) * page_size).limit(page_size).order_by("-created_at")
    total = await AuditLog.filter(q).count()
    data = []
    for obj in objs:
        row = await obj.to_dict()
        row["interface_label"] = WRITE_PATH_LABELS.get(obj.path, obj.path)
        data.append(row)
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/api-stat/interfaces", summary="接口调用统计-写操作接口下拉")
async def get_ehcf_api_stat_interfaces():
    """供前端接口筛选下拉使用。"""
    return SuccessExtra(
        data=[{"path": p, "label": label} for p, label in WRITE_PATH_LABELS.items()],
        total=len(WRITE_PATH_LABELS),
        page=1,
        page_size=len(WRITE_PATH_LABELS),
    )
