from fastapi import APIRouter, UploadFile, File, Request, Query
import asyncio
from pydantic import BaseModel
from app.schemas.base import Success, Fail
from app.core.dependency import AuthControl
from app.models.admin import AuditLog, User
from app.services.sim_service import sim_service

router = APIRouter()


@router.post("/upload", summary="上传SIM-ICCID Excel并写入临时表")
async def upload_sim_iccid(req: Request, file: UploadFile = File(...)):
    """上传文件并写入临时表"""
    try:
        content = await file.read()
        filename = file.filename or "upload.xlsx"
        file_key = await sim_service.upload_excel(content, filename)
        try:
            token = req.headers.get("token")
            user_obj: User = None
            if token:
                user_obj = await AuthControl.is_authed(token)
            user_id = user_obj.id if user_obj else 0
            username = user_obj.username if user_obj else ""
        except Exception:
            user_id = 0
            username = ""
        try:
            await AuditLog.create(
                user_id=user_id,
                username=username,
                module="SIM",
                summary=f"SIM-ICCID文件上传: {filename}",
                method="POST",
                path="/api/v1/sim/simiccid/upload",
                status=200,
                response_time=0,
            )
        except Exception:
            pass
        return Success(data={"file_key": file_key}, msg="上传成功")
    except Exception as e:
        return Fail(code=400, msg=f"上传失败: {str(e)}")


class ProcessBody(BaseModel):
    """处理请求体"""
    file_key: str


@router.post("/process", summary="处理SIM-ICCID临时表数据")
async def process_sim_iccid(req: Request, body: ProcessBody):
    """调用存储过程处理临时表数据"""
    try:
        await sim_service.process_tmp(stamp=body.file_key)
        try:
            token = req.headers.get("token")
            user_obj: User = None
            if token:
                user_obj = await AuthControl.is_authed(token)
            user_id = user_obj.id if user_obj else 0
            username = user_obj.username if user_obj else ""
        except Exception:
            user_id = 0
            username = ""
        try:
            await AuditLog.create(
                user_id=user_id,
                username=username,
                module="SIM",
                summary="SIM-ICCID处理完成",
                method="POST",
                path="/api/v1/sim/simiccid/process",
                status=200,
                response_time=0,
            )
        except Exception:
            pass
        return Success(msg="处理成功")
    except Exception as e:
        return Fail(code=500, msg=f"处理失败: {str(e)}")


@router.post("/submit", summary="上传并处理SIM-ICCID数据")
async def submit_sim_iccid(req: Request, file: UploadFile = File(...)):
    """上传Excel并立即处理（异步），返回本次导入的临时标识"""
    try:
        content = await file.read()
        filename = file.filename or "upload.xlsx"
        # 预生成批次号并启动后台任务
        import uuid
        file_key = str(uuid.uuid4())
        async def _runner():
            try:
                await sim_service.submit_and_process(content, filename, stamp=file_key)
            except Exception:
                return
        asyncio.create_task(_runner())
        try:
            token = req.headers.get("token")
            user_obj: User = None
            if token:
                user_obj = await AuthControl.is_authed(token)
            user_id = user_obj.id if user_obj else 0
            username = user_obj.username if user_obj else ""
        except Exception:
            user_id = 0
            username = ""
        try:
            await AuditLog.create(
                user_id=user_id,
                username=username,
                module="SIM",
                summary=f"SIM-ICCID一次性提交处理完成: {filename} ({file_key})",
                method="POST",
                path="/api/v1/sim/simiccid/submit",
                status=200,
                response_time=0,
            )
        except Exception:
            pass
        return Success(data={"file_key": file_key}, msg="处理成功")
    except Exception as e:
        return Fail(code=500, msg=f"提交处理失败: {str(e)}")


@router.get("/progress", summary="查询SIM-ICCID导入进度")
async def progress_sim_iccid(file_key: str = Query(..., description="导入批次号")):
    """查询导入任务进度"""
    data = sim_service.get_progress(file_key)
    return Success(data=data)
