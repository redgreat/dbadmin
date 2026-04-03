from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.controllers.alert import alert_sender_controller, alert_log_controller
from app.core.ctx import CTX_USER_ID
from app.schemas.alert import AlertSenderCreate, AlertSenderUpdate, AlertLogCreate
from app.schemas.base import Fail, Success, SuccessExtra

router = APIRouter()

SUPPORTED_CHANNEL_TYPES = {"wechat_group"}


def _validate_channel_type(channel_type: str):
    if channel_type not in SUPPORTED_CHANNEL_TYPES:
        return Fail(msg="当前仅支持企业微信群发送人（wechat_group）")
    return None


@router.get("/to/list", summary="查看预警发送人列表")
async def list_alert_sender(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    sender_name: Optional[str] = Query(None, description="发送人名称"),
    channel_type: Optional[str] = Query(None, description="发送渠道类型"),
    is_enabled: Optional[bool] = Query(None, description="是否启用"),
):
    total, items = await alert_sender_controller.list_with_filter(
        page=page,
        page_size=page_size,
        sender_name=sender_name,
        channel_type=channel_type,
        is_enabled=is_enabled,
    )
    data = [await item.to_dict() for item in items]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/to/get", summary="查看预警发送人详情")
async def get_alert_sender(
    id: int = Query(..., description="发送人ID"),
):
    obj = await alert_sender_controller.get(id=id)
    return Success(data=await obj.to_dict())


@router.post("/to/create", summary="创建预警发送人")
async def create_alert_sender(sender_in: AlertSenderCreate):
    channel_error = _validate_channel_type(sender_in.channel_type.value)
    if channel_error:
        return channel_error

    if await alert_sender_controller.check_name_exists(sender_in.sender_name):
        return Fail(msg="发送人名称已存在")

    create_data = sender_in.model_dump()
    create_data["created_by"] = CTX_USER_ID.get()
    create_data["updated_by"] = CTX_USER_ID.get()
    await alert_sender_controller.create(obj_in=create_data)
    return Success(msg="创建成功")


@router.post("/to/update", summary="更新预警发送人")
async def update_alert_sender(sender_in: AlertSenderUpdate):
    old_obj = await alert_sender_controller.get(id=sender_in.id)

    next_channel_type = sender_in.channel_type.value if sender_in.channel_type else old_obj.channel_type
    channel_error = _validate_channel_type(next_channel_type)
    if channel_error:
        return channel_error

    if sender_in.sender_name and sender_in.sender_name != old_obj.sender_name:
        if await alert_sender_controller.check_name_exists(sender_in.sender_name, exclude_id=sender_in.id):
            return Fail(msg="发送人名称已存在")

    update_data = sender_in.model_dump(exclude_unset=True, exclude={"id"})
    update_data["updated_by"] = CTX_USER_ID.get()
    await alert_sender_controller.update(id=sender_in.id, obj_in=update_data)
    return Success(msg="更新成功")


@router.delete("/to/delete", summary="删除预警发送人")
async def delete_alert_sender(
    id: int = Query(..., description="发送人ID"),
):
    await alert_sender_controller.remove(id=id)
    return Success(msg="删除成功")


@router.get("/log/list", summary="查看预警日志列表")
async def list_alert_log(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    sender_id: Optional[int] = Query(None, description="发送人ID"),
    sender_name: Optional[str] = Query(None, description="发送人名称"),
    channel_type: Optional[str] = Query(None, description="发送渠道类型"),
    send_status: Optional[int] = Query(None, description="发送状态：1成功，0失败"),
    start_time: Optional[datetime] = Query(None, description="发送开始时间"),
    end_time: Optional[datetime] = Query(None, description="发送结束时间"),
):
    total, items = await alert_log_controller.list_with_filter(
        page=page,
        page_size=page_size,
        sender_id=sender_id,
        sender_name=sender_name,
        channel_type=channel_type,
        send_status=send_status,
        start_time=start_time,
        end_time=end_time,
    )
    data = [await item.to_dict() for item in items]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/log/get", summary="查看预警日志详情")
async def get_alert_log(
    id: int = Query(..., description="预警日志ID"),
):
    obj = await alert_log_controller.get(id=id)
    return Success(data=await obj.to_dict())


@router.post("/log/create", summary="创建预警日志")
async def create_alert_log(log_in: AlertLogCreate):
    obj = await alert_log_controller.create_log(log_in=log_in)
    return Success(msg="创建成功", data=await obj.to_dict())
