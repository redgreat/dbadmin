import logging
from typing import List

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import AuditLog, User
from app.schemas.base import Fail, Success
from app.schemas.wms import WmsDeleteBatchIn, WmsRestoreLogicalIn
from app.services.wms_service import wms_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/wms_curd/delete_logical_batch", summary="按单据Id批量逻辑删除")
async def delete_logical_batch(req: Request, body: WmsDeleteBatchIn):
    """批量逻辑删除单据"""
    try:
        ids: List[str] = [s.strip() for s in body.stock_ids if s and s.strip()]
        if not ids:
            return Fail(code=400, msg="单据Id不能为空")

        try:
            success_count, failed_ids = await wms_service.delete_logical_batch(ids, body.operator_id)
        except Exception as e:
            logger.error(f"逻辑删除失败: {e}")
            return Fail(code=500, msg=f"执行失败: {str(e)}")

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

        for did in ids:
            status = 200 if did not in failed_ids else 500
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="WMS",
                    summary=f"单据逻辑删除: id={did}",
                    method="POST",
                    path="/api/v1/wms/wms_curd/delete_logical_batch",
                    status=status,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        return Success(data={"success_count": success_count, "failed_ids": failed_ids})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/wms_curd/delete_physical_batch", summary="按单据Id批量物理删除")
async def delete_physical_batch(req: Request, body: WmsDeleteBatchIn):
    """批量物理删除单据"""
    try:
        ids: List[str] = [s.strip() for s in body.stock_ids if s and s.strip()]
        if not ids:
            return Fail(code=400, msg="单据Id不能为空")

        try:
            success_count, failed_ids = await wms_service.delete_physical_batch(ids, body.operator_id)
        except Exception as e:
            logger.error(f"物理删除失败: {e}")
            return Fail(code=500, msg=f"执行失败: {str(e)}")

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

        for did in ids:
            status = 200 if did not in failed_ids else 500
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="WMS",
                    summary=f"单据物理删除: id={did}",
                    method="POST",
                    path="/api/v1/wms/wms_curd/delete_physical_batch",
                    status=status,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        return Success(data={"success_count": success_count, "failed_ids": failed_ids})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/wms_curd/restore_logical", summary="单据逻辑删除恢复")
async def restore_logical(req: Request, body: WmsRestoreLogicalIn):
    """恢复被逻辑删除的单据"""
    try:
        try:
            await wms_service.restore_logical(stock_id=body.stock_id, operator_id=body.operator_id)
        except Exception as e:
            logger.error(f"恢复失败: {e}")
            return Fail(code=500, msg=f"执行失败: {str(e)}")

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
                module="WMS",
                summary=f"单据逻辑删除恢复: id={body.stock_id}, 操作人={body.operator_id}",
                method="POST",
                path="/api/v1/wms/wms_curd/restore_logical",
                status=200,
                response_time=0,
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="OK")
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")
