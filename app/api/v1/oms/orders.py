import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import AuditLog, User
from app.schemas.base import Fail, Success
from app.schemas.oms import UpdateAuditTimeBatchIn, DeleteBatchIn, RestoreLogicalIn
from app.services.order_service import order_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/update_audit_time_batch", summary="按订单Id批量更新审核时间")
async def update_audit_time_batch(req: Request, body: UpdateAuditTimeBatchIn):
    """批量更新订单审核时间"""
    try:
        ids: List[str] = [s.strip() for s in body.order_ids if s and s.strip()]
        if not ids:
            return Fail(code=400, msg="订单Id不能为空")
        try:
            _ = [int(x) for x in ids]
        except Exception:
            return Fail(code=400, msg="订单Id需为数字")

        if not body.audit_time:
            return Fail(code=400, msg="修改时间不能为空")

        new_time: datetime = body.audit_time

        try:
            old_map = await order_service.fetch_audit_time_map(ids)
            affected = await order_service.update_audit_time_batch(ids, new_time)
            new_map = await order_service.fetch_audit_time_map(ids)
        except Exception as e:
            logger.error(f"执行更新失败: {e}")
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

        for oid in ids:
            before = old_map.get(oid)
            after = new_map.get(oid)
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单审核时间更新: id={oid}, 原={before}, 新={after}",
                    method="POST",
                    path="/api/v1/oms/orders/update_audit_time_batch",
                    status=200,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        failed_ids = [oid for oid in ids if new_map.get(oid) != new_time]
        return Success(data={"success_count": affected, "failed_ids": failed_ids})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/delete_logical_batch", summary="按订单Id批量逻辑删除")
async def delete_logical_batch(req: Request, body: DeleteBatchIn):
    """批量逻辑删除订单"""
    try:
        ids: List[str] = [s.strip() for s in body.order_ids if s and s.strip()]
        if not ids:
            return Fail(code=400, msg="订单Id不能为空")
        try:
            _ = [int(x) for x in ids]
        except Exception:
            return Fail(code=400, msg="订单Id需为数字")

        try:
            success_count, failed_ids = await order_service.delete_logical_batch(ids)
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

        for oid in ids:
            status = 200 if oid not in failed_ids else 500
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单逻辑删除: id={oid}",
                    method="POST",
                    path="/api/v1/oms/orders/delete_logical_batch",
                    status=status,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        return Success(data={"success_count": success_count, "failed_ids": failed_ids})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/delete_physical_batch", summary="按订单Id批量物理删除")
async def delete_physical_batch(req: Request, body: DeleteBatchIn):
    """批量物理删除订单"""
    try:
        ids: List[str] = [s.strip() for s in body.order_ids if s and s.strip()]
        if not ids:
            return Fail(code=400, msg="订单Id不能为空")
        try:
            _ = [int(x) for x in ids]
        except Exception:
            return Fail(code=400, msg="订单Id需为数字")

        try:
            success_count, failed_ids = await order_service.delete_physical_batch(ids)
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

        for oid in ids:
            status = 200 if oid not in failed_ids else 500
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单物理删除: id={oid}",
                    method="POST",
                    path="/api/v1/oms/orders/delete_physical_batch",
                    status=status,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        return Success(data={"success_count": success_count, "failed_ids": failed_ids})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/restore_logical", summary="订单逻辑删除恢复")
async def restore_logical(req: Request, body: RestoreLogicalIn):
    """恢复被逻辑删除的订单"""
    try:
        try:
            await order_service.restore_logical(order_id=body.order_id, operator_id=body.operator_id)
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
                module="OMS",
                summary=f"订单逻辑删除恢复: id={body.order_id}, 操作人={body.operator_id}",
                method="POST",
                path="/api/v1/oms/orders/restore_logical",
                status=200,
                response_time=0,
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="OK")
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")
