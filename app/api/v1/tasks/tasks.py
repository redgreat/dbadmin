from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.controllers.task import task_controller
from app.controllers.task_notify import task_notify_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependPermisson
from app.schemas.base import Success, SuccessExtra
from app.schemas.task import (
    TaskCreate,
    TaskInDB,
    TaskList,
    TaskLogInDB,
    TaskLogList,
    TaskUpdate,
)
from app.schemas.task_notify import (
    ReportSendTaskCreate,
    ReportSendTaskUpdate,
    SqlAlertTaskCreate,
    SqlAlertTaskUpdate,
)

router = APIRouter(tags=["定时任务"])


@router.get("/", response_model=TaskList, summary="获取任务列表")
async def get_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    name: Optional[str] = Query(None, description="任务名称，支持模糊搜索"),
    type: Optional[str] = Query(None, description="任务类型：shell, python, http"),
    status: Optional[bool] = Query(None, description="任务状态：true启用，false禁用"),
):
    """
    获取定时任务列表，支持分页和筛选
    """
    return await task_controller.get_tasks(page, limit, name, type, status)


@router.get("/{task_id}", response_model=TaskInDB, summary="获取任务详情")
async def get_task(task_id: int = Path(..., ge=1, description="任务ID")):
    """
    获取单个定时任务的详细信息
    """
    return await task_controller.get_task(task_id)


@router.post("/", response_model=TaskInDB, summary="创建任务")
async def create_task(task_data: TaskCreate):
    """
    创建新的定时任务
    """
    return await task_controller.create_task(task_data)


@router.put("/{task_id}", response_model=TaskInDB, summary="更新任务")
async def update_task(task_id: int = Path(..., ge=1, description="任务ID"), task_data: TaskUpdate = None):
    """
    更新定时任务信息
    """
    return await task_controller.update_task(task_id, task_data)


@router.delete("/{task_id}", summary="删除任务")
async def delete_task(task_id: int = Path(..., ge=1, description="任务ID")):
    """
    删除定时任务
    """
    await task_controller.delete_task(task_id)
    return {"message": f"任务 {task_id} 已删除"}


@router.post("/{task_id}/execute", summary="立即执行任务")
async def execute_task(task_id: int = Path(..., ge=1, description="任务ID")):
    """
    立即执行指定的定时任务
    """
    return await task_controller.execute_task(task_id)


@router.get("/logs", response_model=TaskLogList, summary="获取任务日志列表")
async def get_task_logs(
    task_id: Optional[int] = Query(None, ge=1, description="任务ID，不提供则查询所有任务的日志"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="执行状态：success, failed, timeout, running"),
):
    """
    获取任务执行日志列表，支持分页和筛选
    """
    return await task_controller.get_task_logs(task_id, page, limit, status)


@router.get("/logs/{log_id}", response_model=TaskLogInDB, summary="获取任务日志详情")
async def get_task_log(log_id: int = Path(..., ge=1, description="日志ID")):
    """
    获取单个任务执行日志的详细信息
    """
    return await task_controller.get_task_log(log_id)


@router.get("/report-send/list", summary="获取定时报表发送任务列表")
async def list_report_send_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_name: Optional[str] = Query(None, description="任务名称"),
    status: Optional[bool] = Query(None, description="任务状态"),
):
    total, data = await task_notify_controller.list_report_send_tasks(page, page_size, task_name, status)
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/report-send/create", summary="创建定时报表发送任务")
async def create_report_send_task(task_in: ReportSendTaskCreate):
    task = await task_notify_controller.create_report_send_task(task_in=task_in, user_id=CTX_USER_ID.get())
    return Success(msg="创建成功", data=await task.to_dict())


@router.post("/report-send/update", summary="更新定时报表发送任务")
async def update_report_send_task(task_in: ReportSendTaskUpdate):
    task = await task_notify_controller.update_report_send_task(task_in=task_in, user_id=CTX_USER_ID.get())
    return Success(msg="更新成功", data=await task.to_dict())


@router.delete("/report-send/delete", summary="删除定时报表发送任务")
async def delete_report_send_task(task_id: int = Query(..., description="任务ID")):
    await task_notify_controller.delete_report_send_task(task_id)
    return Success(msg="删除成功")


@router.post("/report-send/execute", summary="立即执行定时报表发送任务")
async def execute_report_send_task(task_id: int = Query(..., description="任务ID")):
    data = await task_notify_controller.execute_report_send_task(task_id)
    return Success(msg=data["message"], data=data)


@router.get("/sql-alert/list", summary="获取SQL预警任务列表")
async def list_sql_alert_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_name: Optional[str] = Query(None, description="任务名称"),
    status: Optional[bool] = Query(None, description="任务状态"),
):
    total, data = await task_notify_controller.list_sql_alert_tasks(page, page_size, task_name, status)
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/sql-alert/create", summary="创建SQL预警任务")
async def create_sql_alert_task(task_in: SqlAlertTaskCreate):
    task = await task_notify_controller.create_sql_alert_task(task_in=task_in, user_id=CTX_USER_ID.get())
    return Success(msg="创建成功", data=await task.to_dict())


@router.post("/sql-alert/update", summary="更新SQL预警任务")
async def update_sql_alert_task(task_in: SqlAlertTaskUpdate):
    task = await task_notify_controller.update_sql_alert_task(task_in=task_in, user_id=CTX_USER_ID.get())
    return Success(msg="更新成功", data=await task.to_dict())


@router.delete("/sql-alert/delete", summary="删除SQL预警任务")
async def delete_sql_alert_task(task_id: int = Query(..., description="任务ID")):
    await task_notify_controller.delete_sql_alert_task(task_id)
    return Success(msg="删除成功")


@router.post("/sql-alert/execute", summary="立即执行SQL预警任务")
async def execute_sql_alert_task(task_id: int = Query(..., description="任务ID")):
    data = await task_notify_controller.execute_sql_alert_task(task_id)
    return Success(msg=data["message"], data=data)


@router.get("/notify-log/list", summary="获取通知任务执行日志")
async def list_notify_task_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    task_type: Optional[str] = Query(None, description="任务类型"),
    task_ref_id: Optional[int] = Query(None, description="任务ID"),
    status: Optional[str] = Query(None, description="执行状态"),
):
    total, data = await task_notify_controller.list_notify_task_logs(
        page=page,
        page_size=page_size,
        task_type=task_type,
        task_ref_id=task_ref_id,
        status=status,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
