"""
Excel导入任务API接口
"""
import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.controllers.conn import conn_controller
from app.controllers.imptask import imptask_controller
from app.core.dependency import DependAuth
from app.models.admin import User
from app.schemas.base import Success
from app.schemas.imptask import ImpTaskOut
from app.services.celery_dispatcher import dispatch_excelimp_execute, revoke_celery_task
from app.services.conn_permission_service import ensure_conn_access
from app.services.excelimp_service import get_progress
from app.services.imptask_processor import (
    cancel_local_imptask_execute,
    cancel_local_imptask_process,
    submit_imptask,
    submit_imptask_execute,
)
from app.services.sql_apply_service import calc_sha256

router = APIRouter()

# 文件存储目录
UPLOAD_DIR = "data/excel_import"
SQL_DIR = "data/sql_files"

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SQL_DIR, exist_ok=True)


def _extract_temp_table_name(sql_text: str) -> str | None:
    """从SQL内容中提取临时表名。"""
    if not sql_text:
        return None
    match = re.search(r"CREATE\s+TABLE\s+([a-zA-Z0-9_]+)\s*\(", sql_text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


@router.get("/list", summary="获取Excel导入任务列表")
async def get_task_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    task_name: str | None = Query(None, description="任务名称筛选"),
    status: str | None = Query(None, description="任务状态筛选"),
):
    """获取Excel导入任务列表"""
    items, total = await imptask_controller.get_list(
        page=page, page_size=page_size, task_name=task_name, status=status
    )

    # 转换为输出格式
    items_out = []
    for item in items:
        item_dict = await item.to_dict()
        temp_table_name = None
        sql_file_path = item_dict.get("sql_file_path")
        if sql_file_path and os.path.exists(sql_file_path):
            try:
                with open(sql_file_path, encoding="utf-8") as f:
                    sql_text = f.read()
                temp_table_name = _extract_temp_table_name(sql_text)
            except Exception:
                temp_table_name = None
        item_dict["temp_table_name"] = temp_table_name
        items_out.append(ImpTaskOut(**item_dict))

    return Success(data={
        "items": [item.model_dump(mode='json') for item in items_out],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/create", summary="创建Excel导入任务")
async def create_task(
    current_user: User = DependAuth,
    file: UploadFile = File(...),
    task_name: str = Form(...),
    target_conn_id: int | None = Form(None),
    db_type: str = Form("mysql"),
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

    conn_info = None
    if target_conn_id:
        await ensure_conn_access(current_user, target_conn_id, "使用该目标连接")
        # 配置了目标连接时，数据库类型由连接决定（前端不可自定义）
        conn_info = await conn_controller.get_decrypted_connection(target_conn_id)
        if not conn_info:
            raise HTTPException(status_code=400, detail="目标连接不存在或不可用")
        db_type = conn_info.get("db_type")
        if db_type not in ("mysql", "postgresql"):
            raise HTTPException(status_code=400, detail=f"目标连接类型不支持导入执行: {db_type}")
    else:
        # 未配置目标连接时，仅用于生成SQL和下载
        if db_type not in ("mysql", "postgresql"):
            db_type = "mysql"

    user_id = current_user.id
    username = current_user.username

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
        "target_conn_id": target_conn_id,
        "target_conn_name": conn_info.get("name") if conn_info else None,
        "status": "pending",
        "progress": 0,
        "message": "任务已创建，等待处理",
        "user_id": user_id,
        "username": username,
    })
    await submit_imptask(task.id)

    return Success(data={"task_id": task.id}, msg="任务创建成功，正在后台处理")


@router.post("/execute", summary="执行Excel导入SQL")
async def execute_task_sql(
    payload: dict = Body(...),
    current_user: User = DependAuth,
):
    """
    统一执行入口：
    - source_type=imptask: 通过任务ID执行任务生成的SQL文件（目标连接不可改）
    - source_type=excelimp: 通过file_key执行临时生成SQL（需传target_conn_id）
    """
    source_type = payload.get("source_type", "imptask")

    # 路由层已鉴权，直接使用当前用户
    user_id = current_user.id
    username = current_user.username

    if source_type == "imptask":
        task_id = payload.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail="task_id不能为空")
        task = await imptask_controller.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task.status != "completed":
            raise HTTPException(status_code=400, detail="任务未完成，不能执行")
        if not task.sql_file_path or not os.path.exists(task.sql_file_path):
            raise HTTPException(status_code=404, detail="SQL文件不存在")
        if not task.target_conn_id:
            return Success(
                msg="任务未配置目标连接",
                data={
                    "success": False,
                    "reason": "missing_target_conn",
                    "task_id": task.id,
                },
            )
        await ensure_conn_access(current_user, int(task.target_conn_id), "使用该任务目标连接")

        with open(task.sql_file_path, encoding="utf-8") as file_obj:
            sql_text = file_obj.read()

        # 防篡改：比对生成时哈希
        current_sha = calc_sha256(sql_text)
        if task.sql_sha256 and task.sql_sha256 != current_sha:
            raise HTTPException(status_code=400, detail="SQL文件摘要校验失败，疑似被篡改")

        await submit_imptask_execute(task.id, user_id, username)
        return Success(
            msg="导入执行任务已提交，请稍后查看执行状态",
            data={"task_id": task.id, "execute_status": "processing"},
        )

    elif source_type == "excelimp":
        file_key = payload.get("file_key")
        target_conn_id = payload.get("target_conn_id")
        if not file_key:
            raise HTTPException(status_code=400, detail="file_key不能为空")
        if not target_conn_id:
            raise HTTPException(status_code=400, detail="target_conn_id不能为空")
        await ensure_conn_access(current_user, int(target_conn_id), "使用该目标连接")

        progress = get_progress(file_key)
        if not progress or progress.get("stage") != "done":
            raise HTTPException(status_code=400, detail="该临时任务未完成，不能执行")
        sql_text = progress.get("sql")
        if not sql_text:
            raise HTTPException(status_code=400, detail="未找到可执行SQL内容")

        # 防篡改：校验缓存中的sql摘要
        current_sha = calc_sha256(sql_text)
        if progress.get("sql_sha256") and progress.get("sql_sha256") != current_sha:
            raise HTTPException(status_code=400, detail="SQL摘要校验失败，疑似被篡改")

        celery_task_id = dispatch_excelimp_execute(file_key, int(target_conn_id))
        if not celery_task_id:
            import asyncio

            from app.services.excelimp_service import execute_sql_file_task

            asyncio.create_task(execute_sql_file_task(file_key, int(target_conn_id)))

        return Success(
            msg="导入执行任务已提交，请稍后查看执行状态",
            data={"file_key": file_key, "execute_status": "processing", "celery_task_id": celery_task_id},
        )

    else:
        raise HTTPException(status_code=400, detail="source_type仅支持 imptask 或 excelimp")


@router.get("/detail/{task_id}", summary="获取任务详情")
async def get_task_detail(task_id: int):
    """获取任务详情"""
    task = await imptask_controller.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_dict = await task.to_dict()
    return Success(data=task_dict)


@router.get("/download/{task_id}", summary="下载SQL文件")
async def download_sql_file(task_id: int, req: Request):
    """下载生成的SQL文件（支持查询参数token）"""
    # 手动验证token（支持Header和查询参数两种方式）
    import jwt

    from app.settings import settings

    try:
        # 优先从Header获取token
        token = req.headers.get("token")

        # 如果Header中没有，尝试从查询参数获取
        if not token:
            token = req.query_params.get("token")

        # 如果还是没有token，返回错误
        if not token:
            raise HTTPException(status_code=401, detail="未提供认证token，请在Header或查询参数中提供token")

        # 验证token（直接解析JWT）
        try:
            decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
            user_id = decode_data.get("user_id")
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="登录已过期")

        # 验证用户是否存在
        user = await User.filter(id=user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"认证失败: {e!s}")

    # 获取任务
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


@router.post("/stop/{task_id}", summary="停止Excel导入任务")
async def stop_task(task_id: int, current_user: User = DependAuth):
    """停止Excel导入任务或其执行导入任务。"""
    task = await imptask_controller.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    is_admin = current_user.is_superuser or any(role.name == "admin" for role in await current_user.roles)
    if not is_admin and task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限停止该任务")

    if task.execute_status == "processing":
        task.execute_stop_requested = True
        task.execute_status = "manual_stopped"
        task.execute_message = "任务已手动停止"
        task.stopped_at = datetime.now()
        await task.save(update_fields=["execute_stop_requested", "execute_status", "execute_message", "stopped_at"])
        revoke_ok = revoke_celery_task(task.execute_celery_task_id, terminate=True) if task.execute_celery_task_id else False
        cancel_ok = cancel_local_imptask_execute(task.id)
        return Success(
            msg="导入执行停止请求已提交",
            data={"task_id": task.id, "target": "execute", "revoke_sent": revoke_ok, "local_cancelled": cancel_ok},
        )

    if task.status in ("pending", "processing"):
        original_status = task.status
        task.stop_requested = True
        task.status = "manual_stopped"
        task.message = "任务已手动停止"
        task.stopped_at = datetime.now()
        await task.save(update_fields=["stop_requested", "status", "message", "stopped_at"])
        revoke_ok = revoke_celery_task(task.process_celery_task_id, terminate=True) if task.process_celery_task_id else False
        cancel_ok = cancel_local_imptask_process(task.id)
        if original_status == "pending":
            task.status = "manual_stopped"
            task.message = "任务已手动停止"
            task.stop_requested = False
            task.process_celery_task_id = None
            task.stopped_at = datetime.now()
            task.completed_at = datetime.now()
            await task.save(update_fields=[
                "status",
                "message",
                "stop_requested",
                "process_celery_task_id",
                "stopped_at",
                "completed_at",
            ])
        return Success(
            msg="任务停止请求已提交",
            data={"task_id": task.id, "target": "process", "revoke_sent": revoke_ok, "local_cancelled": cancel_ok},
        )

    raise HTTPException(status_code=400, detail="当前任务没有进行中的处理或执行任务")
