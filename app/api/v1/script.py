from fastapi import APIRouter, Path, Query

from app.controllers.script import script_controller
from app.schemas.base import Success, SuccessExtra
from app.schemas.script import (
    PythonScriptCreate,
    PythonScriptUpdate,
    ScriptRunLogList,
)

router = APIRouter(tags=["Python脚本"])


@router.get("/", summary="获取脚本列表")
async def get_scripts(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    name: str | None = Query(None, description="脚本名称"),
    status: bool | None = Query(None, description="是否启用"),
):
    """获取Python脚本列表"""
    data = await script_controller.get_scripts(page, limit, name, status)
    return SuccessExtra(data=data["data"], total=data["total"], page=page, page_size=limit)


@router.get("/{script_id:int}", summary="获取脚本详情")
async def get_script(script_id: int = Path(..., ge=1, description="脚本ID")):
    """获取单个脚本详情"""
    data = await script_controller.get_script(script_id)
    return Success(data=data)


@router.post("/", summary="创建脚本")
async def create_script(script_data: PythonScriptCreate):
    """创建新的Python脚本"""
    data = await script_controller.create_script(script_data.model_dump())
    return Success(msg="创建成功", data=data)


@router.put("/{script_id:int}", summary="更新脚本")
async def update_script(
    script_id: int = Path(..., ge=1, description="脚本ID"),
    script_data: PythonScriptUpdate = None,
):
    """更新Python脚本"""
    data = await script_controller.update_script(script_id, script_data.model_dump())
    return Success(msg="更新成功", data=data)


@router.delete("/{script_id:int}", summary="删除脚本")
async def delete_script(script_id: int = Path(..., ge=1, description="脚本ID")):
    """删除Python脚本"""
    await script_controller.delete_script(script_id)
    return Success(msg="删除成功")


@router.post("/{script_id:int}/execute", summary="执行脚本")
async def execute_script(script_id: int = Path(..., ge=1, description="脚本ID")):
    """立即执行Python脚本"""
    data = await script_controller.execute_script(script_id)
    return Success(msg=data["message"], data=data)


@router.get("/logs", summary="获取执行日志列表")
async def get_run_logs(
    script_id: int | None = Query(None, ge=1, description="脚本ID"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(10, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="执行状态"),
):
    """获取脚本执行日志列表"""
    data = await script_controller.get_run_logs(script_id, page, limit, status)
    return SuccessExtra(data=data["items"], total=data["total"], page=page, page_size=limit)


@router.get("/logs/{log_id:int}", summary="获取执行日志详情")
async def get_run_log(log_id: int = Path(..., ge=1, description="日志ID")):
    """获取单个执行日志详情"""
    data = await script_controller.get_run_log(log_id)
    return Success(data=data)
