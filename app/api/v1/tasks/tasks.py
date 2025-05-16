from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException

from app.controllers.task import task_controller
from app.schemas.task import TaskCreate, TaskUpdate, TaskList, TaskInDB, TaskLogList, TaskLogInDB
from app.core.dependency import DependPermisson

router = APIRouter()

@router.get("/", response_model=TaskList, summary="获取任务列表")
async def get_tasks(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    name: Optional[str] = Query(None, description="任务名称，支持模糊搜索"),
    type: Optional[str] = Query(None, description="任务类型：shell, python, http"),
    status: Optional[bool] = Query(None, description="任务状态：true启用，false禁用")
):
    """
    获取定时任务列表，支持分页和筛选
    """
    return await task_controller.get_tasks(page, limit, name, type, status)

@router.get("/{task_id}", response_model=TaskInDB, summary="获取任务详情")
async def get_task(
    task_id: int = Path(..., ge=1, description="任务ID")
):
    """
    获取单个定时任务的详细信息
    """
    return await task_controller.get_task(task_id)

@router.post("/", response_model=TaskInDB, summary="创建任务")
async def create_task(
    task_data: TaskCreate
):
    """
    创建新的定时任务
    """
    return await task_controller.create_task(task_data)

@router.put("/{task_id}", response_model=TaskInDB, summary="更新任务")
async def update_task(
    task_id: int = Path(..., ge=1, description="任务ID"),
    task_data: TaskUpdate = None
):
    """
    更新定时任务信息
    """
    return await task_controller.update_task(task_id, task_data)

@router.delete("/{task_id}", summary="删除任务")
async def delete_task(
    task_id: int = Path(..., ge=1, description="任务ID")
):
    """
    删除定时任务
    """
    await task_controller.delete_task(task_id)
    return {"message": f"任务 {task_id} 已删除"}

@router.post("/{task_id}/execute", summary="立即执行任务")
async def execute_task(
    task_id: int = Path(..., ge=1, description="任务ID")
):
    """
    立即执行指定的定时任务
    """
    return await task_controller.execute_task(task_id)

@router.get("/logs", response_model=TaskLogList, summary="获取任务日志列表")
async def get_task_logs(
    task_id: Optional[int] = Query(None, ge=1, description="任务ID，不提供则查询所有任务的日志"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="执行状态：success, failed, timeout, running")
):
    """
    获取任务执行日志列表，支持分页和筛选
    """
    return await task_controller.get_task_logs(task_id, page, limit, status)

@router.get("/logs/{log_id}", response_model=TaskLogInDB, summary="获取任务日志详情")
async def get_task_log(
    log_id: int = Path(..., ge=1, description="日志ID")
):
    """
    获取单个任务执行日志的详细信息
    """
    return await task_controller.get_task_log(log_id)
