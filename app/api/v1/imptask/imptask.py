"""
Excel导入任务API接口
"""
import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Query, Request, HTTPException, Depends
from fastapi.responses import FileResponse

from app.schemas.base import Success, Fail
from app.schemas.imptask import ImpTaskOut, ImpTaskList
from app.controllers.imptask import imptask_controller
from app.services.imptask_processor import submit_imptask
from app.models.admin import User
from app.core.dependency import AuthControl, DependAuth
from app.settings.config import settings

router = APIRouter()

# 文件存储目录
UPLOAD_DIR = "data/excel_import"
SQL_DIR = "data/sql_files"

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SQL_DIR, exist_ok=True)


@router.get("/list", summary="获取Excel导入任务列表")
async def get_task_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    task_name: Optional[str] = Query(None, description="任务名称筛选"),
    status: Optional[str] = Query(None, description="任务状态筛选"),
):
    """获取Excel导入任务列表"""
    items, total = await imptask_controller.get_list(
        page=page, page_size=page_size, task_name=task_name, status=status
    )

    # 转换为输出格式
    items_out = []
    for item in items:
        item_dict = await item.to_dict()
        items_out.append(ImpTaskOut(**item_dict))

    return Success(data={
        "items": [item.model_dump(mode='json') for item in items_out],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/create", summary="创建Excel导入任务")
async def create_task(
    req: Request,
    file: UploadFile = File(...),
    task_name: str = Form(...),
    db_type: str = Form(...),
):
    """创建Excel导入任务"""
    # 验证文件
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 和 .xls 格式的Excel文件")

    # 读取文件内容
    content = await file.read()

    # 验证文件大小
    max_size = 100 * 1024 * 1024  # 100MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大100MB），当前文件大小: {len(content) / 1024 / 1024:.2f}MB"
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 获取用户信息
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

    # 生成文件存储路径
    file_ext = file.filename.split('.')[-1]
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.{file_ext}")

    # 保存文件
    with open(file_path, 'wb') as f:
        f.write(content)

    # 创建任务记录
    task = await imptask_controller.create({
        "task_name": task_name,
        "filename": file.filename,
        "file_path": file_path,
        "file_size": len(content),
        "db_type": db_type,
        "status": "pending",
        "progress": 0,
        "message": "任务已创建，等待处理",
        "user_id": user_id,
        "username": username,
    })

    # 提交后台任务
    await submit_imptask(task.id)

    return Success(data={"task_id": task.id}, msg="任务创建成功，正在后台处理")


@router.get("/detail/{task_id}", summary="获取任务详情")
async def get_task_detail(task_id: int):
    """获取任务详情"""
    task = await imptask_controller.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_dict = await task.to_dict()
    return Success(data=task_dict)


@router.get("/download/{task_id}", summary="下载SQL文件")
async def download_sql_file(task_id: int):
    """下载生成的SQL文件"""
    task = await imptask_controller.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    if not task.sql_file_path or not os.path.exists(task.sql_file_path):
        raise HTTPException(status_code=404, detail="SQL文件不存在")

    # 生成下载文件名
    download_name = f"{task.task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    return FileResponse(
        path=task.sql_file_path,
        filename=download_name,
        media_type="application/octet-stream"
    )


@router.delete("/delete/{task_id}", summary="删除任务")
async def delete_task(task_id: int, current_user: User = DependAuth):
    """删除任务及其相关文件（仅管理员可操作）"""
    # 检查是否为管理员
    is_admin = current_user.is_superuser or any(role.name == "admin" for role in await current_user.roles)
    if not is_admin:
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可删除任务")

    task = await imptask_controller.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除Excel文件
    if task.file_path and os.path.exists(task.file_path):
        try:
            os.remove(task.file_path)
        except Exception:
            pass

    # 删除SQL文件
    if task.sql_file_path and os.path.exists(task.sql_file_path):
        try:
            os.remove(task.sql_file_path)
        except Exception:
            pass

    # 删除任务记录
    await imptask_controller.remove(task_id)

    return Success(msg="任务删除成功")
