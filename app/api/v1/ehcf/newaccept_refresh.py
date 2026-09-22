"""
壹好车服-车务待办人刷新
上传固定模板Excel(订单号/旧代办人工号/新代办人工号)，写入已部署的固定临时表
tm_newaccept（按批次 ImpStamp 隔离）后调用存储过程 proc_VhsAcceptRefesh 刷业务表。
"""
import logging

from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Success
from app.services.ehcf_newaccept_service import build_template_bytes, ehcf_newaccept_service
from app.utils.audit_log import create_operation_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


async def _check_excel_file(file: UploadFile) -> bytes:
    """校验并读取Excel文件，格式/大小/空文件时抛 400"""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 和 .xls 格式的Excel文件")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大20MB），当前 {len(content)/1024/1024:.2f}MB",
        )
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    return content


@router.get("/newaccept-refresh/template", summary="下载固定Excel模板")
async def newaccept_template():
    """下载固定模板Excel（表头：订单号/旧代办人工号/新代办人工号）"""
    content = build_template_bytes()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=newaccept_refresh_template.xlsx"
        },
    )


@router.post("/newaccept-refresh/preview", summary="上传预览-车务待办人刷新")
async def newaccept_preview(file: UploadFile = File(...)):
    """上传Excel预览：解析+按批次写临时表+刷新前统计（不修改业务表）"""
    content = await _check_excel_file(file)
    try:
        result = await ehcf_newaccept_service.preview(content)
        return Success(data=result, msg=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"车务待办人刷新预览失败: {e}")
        raise HTTPException(status_code=500, detail=f"预览失败: {e!s}")


@router.post("/newaccept-refresh/execute", summary="执行车务待办人刷新")
async def newaccept_execute(
    req: Request,
    file: UploadFile = File(...),
):
    """执行刷新：解析Excel写临时表后 CALL proc_VhsAcceptRefesh(批次Id) 刷业务表"""
    content = await _check_excel_file(file)
    try:
        user_id, username = await _get_user_info(req)
    except Exception:
        user_id, username = 0, ""

    try:
        result = await ehcf_newaccept_service.upload_and_refresh(content, execute=True)
        await _write_audit_log(
            user_id,
            username,
            f"车务待办人刷新（上传Excel执行，批次 {result.get('batch_id')}）："
            f"解析{result['total']}条，写入{result['written']}条，"
            + ("刷新生效成功" if result.get("success") else "刷新失败"),
            result,
            {"source": "upload", "filename": file.filename},
        )
        return Success(data=result, msg=result["message"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"车务待办人刷新执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行失败: {e!s}")


@router.post("/newaccept-refresh/refresh-by-batch", summary="按批次执行车务待办人刷新")
async def newaccept_refresh_by_batch(req: Request, batch_id: str = Body(..., embed=True)):
    """基于已写入临时表的批次Id调用存储过程刷新（预览后未重传文件的场景）"""
    try:
        user_id, username = await _get_user_info(req)
    except Exception:
        user_id, username = 0, ""

    try:
        proc_result = await ehcf_newaccept_service.refresh_only(batch_id)
        await _write_audit_log(
            user_id,
            username,
            f"车务待办人刷新（按批次 {batch_id} 执行）",
            {**proc_result, "batch_id": batch_id},
            {"source": "batch", "batch_id": batch_id},
        )
        return Success(
            data={**proc_result, "batch_id": batch_id},
            msg=proc_result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"车务待办人刷新按批次执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行失败: {e!s}")


@router.post("/newaccept-refresh/cleanup", summary="清理临时表")
async def newaccept_cleanup(payload: dict = Body(None)):
    """清理固定临时表 tm_newaccept：
    - 传 batch_id：仅删除该批次数据
    - 不传：清空全表（高危）
    """
    batch_id = str((payload or {}).get("batch_id") or "").strip()
    try:
        await ehcf_newaccept_service.drop_temp_table(batch_id or None)
        return Success(
            msg=f"批次 {batch_id} 已清理" if batch_id else "临时表已清空"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"清理临时表失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {e!s}")


async def _get_user_info(req: Request) -> tuple[int, str]:
    """从请求中提取用户信息"""
    token = req.headers.get("token")
    user_obj: User = None
    if token:
        user_obj = await AuthControl.is_authed(token)
    return (user_obj.id if user_obj else 0, user_obj.username if user_obj else "")


async def _write_audit_log(
    user_id: int, username: str, summary: str, result: dict, request_info: dict
) -> None:
    """记录审计日志（批量改派为高危操作，必须留痕）"""
    try:
        await create_operation_audit_log(
            user_id=user_id,
            username=username,
            module="EHCF",
            summary=summary,
            method="POST",
            path="/api/v1/ehcf/newaccept-refresh/execute",
            status=200,
            request_body=request_info,
            response_body=result,
        )
    except Exception as e:
        logger.warning(f"审计日志记录失败: {e}")
