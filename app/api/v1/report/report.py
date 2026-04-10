import hashlib
import hmac
import logging
import os
import time

import jwt
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse
from app.core.dependency import get_current_user
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.report import (
    ReportConfigCreate,
    ReportConfigUpdate,
    ReportGenerateRequest
)
from app.services.report_service import ReportService
from app.services.excel_export_service import ExcelExportService
from app.models.report import ReportConfig, ReportGeneration
from app.models.admin import User
from app.log import logger
from app.services.celery_dispatcher import dispatch_report_export
from app.settings import settings

router = APIRouter()

def _build_public_download_sig(generation_id: int, exp: int) -> str:
    """生成公开下载签名（HMAC-SHA256）。"""
    key = settings.SECRET_KEY.encode("utf-8")
    raw = f"{generation_id}:{exp}".encode("utf-8")
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


async def _file_response_from_generation(generation: ReportGeneration) -> FileResponse:
    """将报表生成记录转换为可下载的文件响应。"""
    if generation.status != "completed":
        raise HTTPException(status_code=400, detail="报表尚未生成完成")

    if not generation.file_path:
        raise HTTPException(status_code=404, detail="文件路径不存在")

    if not os.path.exists(generation.file_path):
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")

    if generation.file_path.endswith(".zip"):
        media_type = "application/zip"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=generation.file_path,
        media_type=media_type,
        filename=os.path.basename(generation.file_path),
    )


# ==================== 报表配置相关接口 ====================

@router.get("/config/list", summary="获取报表配置列表")
async def get_config_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    system_name: str = Query(None, description="系统名称"),
    report_name: str = Query(None, description="报表名称"),
    current_user: User = Depends(get_current_user)
):
    """获取报表配置列表"""
    try:
        items, total = await ReportService.get_config_list(
            page=page,
            page_size=page_size,
            system_name=system_name,
            report_name=report_name
        )

        # 转换为字典列表
        data = []
        for item in items:
            item_dict = await item.to_dict()
            # 获取关联的数据库连接名称
            db_conn = await item.db_connection
            item_dict["db_connection_name"] = db_conn.name if db_conn else ""
            # SQL语句简写（只显示前50个字符）
            if len(item_dict["sql_statement"]) > 50:
                item_dict["sql_statement_short"] = item_dict["sql_statement"][:50] + "..."
            else:
                item_dict["sql_statement_short"] = item_dict["sql_statement"]
            data.append(item_dict)

        return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"获取报表配置列表失败: {str(e)}")
        return Fail(msg=f"获取列表失败: {str(e)}")


@router.get("/config/detail", summary="获取报表配置详情")
async def get_config_detail(
    config_id: int = Query(..., description="报表配置ID"),
    current_user: User = Depends(get_current_user)
):
    """获取报表配置详情"""
    try:
        config = await ReportConfig.get_or_none(id=config_id).prefetch_related("db_connection")
        if not config:
            return Fail(msg="报表配置不存在")

        data = await config.to_dict()
        db_conn = await config.db_connection
        data["db_connection_name"] = db_conn.name if db_conn else ""

        return Success(data=data)
    except Exception as e:
        logger.error(f"获取报表配置详情失败: {str(e)}")
        return Fail(msg=f"获取详情失败: {str(e)}")


@router.post("/config/create", summary="创建报表配置")
async def create_config(
    config_in: ReportConfigCreate,
    current_user: User = Depends(get_current_user)
):
    """创建报表配置"""
    try:
        config = await ReportService.create_config(
            system_name=config_in.system_name,
            report_name=config_in.report_name,
            sql_statement=config_in.sql_statement,
            db_connection_id=config_in.db_connection_id,
            maintainer=current_user.username
        )

        return Success(msg="创建成功", data={"id": config.id})
    except ValueError as e:
        return Fail(msg=str(e))
    except Exception as e:
        logger.error(f"创建报表配置失败: {str(e)}")
        return Fail(msg=f"创建失败: {str(e)}")


@router.post("/config/update", summary="更新报表配置")
async def update_config(
    config_in: ReportConfigUpdate,
    current_user: User = Depends(get_current_user)
):
    """更新报表配置"""
    try:
        # 准备更新数据
        update_data = config_in.dict(exclude_unset=True, exclude={"id"})

        config = await ReportService.update_config(
            config_id=config_in.id,
            user=current_user.username,
            is_admin=current_user.is_superuser,
            **update_data
        )

        return Success(msg="更新成功")
    except PermissionError as e:
        return Fail(code=403, msg=str(e))
    except ValueError as e:
        return Fail(msg=str(e))
    except Exception as e:
        logger.error(f"更新报表配置失败: {str(e)}")
        return Fail(msg=f"更新失败: {str(e)}")


@router.delete("/config/delete", summary="删除报表配置")
async def delete_config(
    config_id: int = Query(..., description="报表配置ID"),
    current_user: User = Depends(get_current_user)
):
    """删除报表配置"""
    try:
        await ReportService.delete_config(
            config_id=config_id,
            user=current_user.username,
            is_admin=current_user.is_superuser
        )

        return Success(msg="删除成功")
    except PermissionError as e:
        return Fail(code=403, msg=str(e))
    except ValueError as e:
        return Fail(msg=str(e))
    except Exception as e:
        logger.error(f"删除报表配置失败: {str(e)}")
        return Fail(msg=f"删除失败: {str(e)}")


@router.get("/options/systems", summary="获取系统名称选项")
async def get_system_name_options(
    current_user: User = Depends(get_current_user)
):
    """获取系统名称选项列表"""
    try:
        options = await ReportService.get_system_name_options()
        # 转换为前端需要的格式
        data = [{"label": opt, "value": opt} for opt in options]
        return Success(data=data)
    except Exception as e:
        logger.error(f"获取系统名称选项失败: {str(e)}")
        return Fail(msg=f"获取选项失败: {str(e)}")


# ==================== 报表生成相关接口 ====================

@router.post("/generate", summary="生成报表")
async def generate_report(
    request: ReportGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    """触发生成报表"""
    try:
        # 获取报表配置
        config = await ReportConfig.get_or_none(id=request.config_id)
        if not config:
            return Fail(msg="报表配置不存在")

        # 生成报表名称（报表名称+年月日时分秒）
        from datetime import datetime
        report_name = f"{config.report_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 创建生成记录
        generation = await ReportGeneration.create(
            report_name=report_name,
            report_config_id=config.id,
            generator=current_user.username,
            status="exporting",
            progress=0,
            progress_text="排队中",
            exported_rows=0,
            error_message=None,
        )

        celery_task_id = dispatch_report_export(generation.id)
        if not celery_task_id:
            # Celery未启用时回退到应用内后台任务
            import asyncio

            asyncio.create_task(ExcelExportService().export_report(generation.id))

        logger.info(f"创建报表生成任务: {report_name}, ID: {generation.id}")

        return Success(msg="生成任务已提交", data={"generation_id": generation.id})
    except Exception as e:
        logger.error(f"生成报表失败: {str(e)}")
        return Fail(msg=f"生成失败: {str(e)}")


@router.get("/generation/list", summary="获取报表生成记录列表")
async def get_generation_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    system_name: str = Query(None, description="系统名称"),
    report_name: str = Query(None, description="报表名称"),
    status: str = Query(None, description="报表状态"),
    current_user: User = Depends(get_current_user)
):
    """获取报表生成记录列表"""
    try:
        items, total = await ReportService.get_generation_list(
            page=page,
            page_size=page_size,
            system_name=system_name,
            report_name=report_name,
            status=status
        )

        # 转换为字典列表
        data = [await item.to_dict() for item in items]

        return SuccessExtra(data=data, total=total, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"获取报表生成记录列表失败: {str(e)}")
        return Fail(msg=f"获取列表失败: {str(e)}")


@router.get("/generation/download", summary="下载报表文件")
async def download_report(
    generation_id: int = Query(..., description="报表生成记录ID"),
    current_user: User = Depends(get_current_user)
):
    """下载报表文件"""
    try:
        generation = await ReportGeneration.get_or_none(id=generation_id)
        if not generation:
            return Fail(msg="报表生成记录不存在")
        return await _file_response_from_generation(generation)
    except Exception as e:
        logger.error(f"下载报表文件失败: {str(e)}")
        return Fail(msg=f"下载失败: {str(e)}")


@router.get("/generation/download-direct/{generation_id}", summary="直接下载报表文件（支持查询参数token）")
async def download_report_direct(generation_id: int = Path(..., ge=1, description="报表生成记录ID"), req: Request = None):
    """下载报表文件（支持Header和查询参数token），用于浏览器直接接管下载流程。"""
    try:
        token = req.headers.get("token") if req else None
        if not token and req:
            token = req.query_params.get("token")
        if not token:
            raise HTTPException(status_code=401, detail="未提供认证token，请在Header或查询参数中提供token")

        try:
            decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
            user_id = decode_data.get("user_id")
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="登录已过期")

        user = await User.filter(id=user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")

        generation = await ReportGeneration.get_or_none(id=generation_id)
        if not generation:
            raise HTTPException(status_code=404, detail="报表生成记录不存在")
        return await _file_response_from_generation(generation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载报表文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/generation/public-download/{generation_id}", summary="公开下载报表文件（签名校验）")
async def download_report_public(
    generation_id: int = Path(..., ge=1, description="报表生成记录ID"),
    exp: int = Query(..., description="过期时间戳（秒）"),
    sig: str = Query(..., description="签名"),
):
    """公开下载报表文件（签名校验），用于企业微信群无法携带token的场景。"""
    now = int(time.time())
    if exp < now:
        raise HTTPException(status_code=403, detail="下载链接已过期")

    expected = _build_public_download_sig(generation_id=generation_id, exp=exp)
    if not hmac.compare_digest(expected, (sig or "").strip()):
        raise HTTPException(status_code=403, detail="下载链接签名无效")

    generation = await ReportGeneration.get_or_none(id=generation_id)
    if not generation:
        raise HTTPException(status_code=404, detail="报表生成记录不存在")
    return await _file_response_from_generation(generation)


@router.delete("/generation/delete", summary="删除报表生成记录")
async def delete_generation(
    generation_id: int = Query(..., description="报表生成记录ID"),
    current_user: User = Depends(get_current_user)
):
    """删除报表生成记录"""
    try:
        generation = await ReportGeneration.get_or_none(id=generation_id)
        if not generation:
            return Fail(msg="报表生成记录不存在")

        # 判断是否为管理员
        is_admin = current_user.is_superuser

        # 权限验证：管理员可删除所有，普通用户只能删除自己生成的
        if not is_admin and generation.generator != current_user.username:
            return Fail(code=403, msg="无权限删除此报表生成记录")

        # 删除物理文件
        if generation.file_path:
            import os
            if os.path.exists(generation.file_path):
                os.remove(generation.file_path)
                logger.info(f"删除报表文件: {generation.file_path}")

        # 软删除记录
        await generation.soft_delete()

        return Success(msg="删除成功")
    except Exception as e:
        logger.error(f"删除报表生成记录失败: {str(e)}")
        return Fail(msg=f"删除失败: {str(e)}")
