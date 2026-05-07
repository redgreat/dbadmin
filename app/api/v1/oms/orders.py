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


@router.post("/update_audit_time_batch", summary="批量更新审核时间（支持订单编码或订单Id）")
async def update_audit_time_batch(req: Request, body: UpdateAuditTimeBatchIn):
    """批量更新订单审核时间，支持传入订单编码或订单Id"""
    try:
        order_nos: List[str] = [s.strip() for s in body.order_nos if s and s.strip()]
        if not order_nos:
            return Fail(code=400, msg="订单编码或订单Id不能为空")

        if not body.audit_time:
            return Fail(code=400, msg="修改时间不能为空")

        new_time: datetime = body.audit_time

        try:
            # 先通过订单编码获取对应的Id
            order_no_id_map = await order_service.fetch_order_ids_by_nos(order_nos)
            
            # 找出未找到的订单编码
            not_found_nos = [no for no in order_nos if no not in order_no_id_map]
            if not_found_nos:
                logger.warning(f"以下订单编码未找到: {not_found_nos}")
            
            if not order_no_id_map:
                return Success(msg=f"未找到对应的订单，订单编码: {', '.join(not_found_nos)}", data={"success_count": 0, "failed_ids": not_found_nos})

            # 使用获取到的Id进行更新
            order_ids = list(order_no_id_map.values())
            old_map = await order_service.fetch_audit_time_map(order_nos)
            affected = await order_service.update_audit_time_batch(order_ids, new_time)
            new_map = await order_service.fetch_audit_time_map(order_nos)
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

        for order_no in order_nos:
            before = old_map.get(order_no)
            after = new_map.get(order_no)
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单审核时间更新: orderNo={order_no}, 原={before}, 新={after}",
                    method="POST",
                    path="/api/v1/oms/orders/update_audit_time_batch",
                    status=200,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        if not_found_nos:
            return Success(
                msg=f"部分订单更新失败，成功 {affected} 条，失败 {len(not_found_nos)} 条。失败订单: {', '.join(not_found_nos)}",
                data={"success_count": affected, "failed_ids": not_found_nos}
            )
        
        return Success(msg=f"更新成功，共 {affected} 条", data={"success_count": affected, "failed_ids": []})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/delete_logical_batch", summary="批量逻辑删除（支持订单编码或订单Id）")
async def delete_logical_batch(req: Request, body: DeleteBatchIn):
    """批量逻辑删除订单，支持传入订单编码或订单Id"""
    try:
        order_nos: List[str] = [s.strip() for s in body.order_nos if s and s.strip()]
        if not order_nos:
            return Fail(code=400, msg="订单编码或订单Id不能为空")

        try:
            # 先通过订单编码获取对应的Id
            order_no_id_map = await order_service.fetch_order_ids_by_nos(order_nos)
            
            # 找出未找到的订单编码
            not_found_nos = [no for no in order_nos if no not in order_no_id_map]
            if not_found_nos:
                logger.warning(f"以下订单编码未找到: {not_found_nos}")
            
            if not order_no_id_map:
                return Success(msg=f"未找到对应的订单，订单编码: {', '.join(not_found_nos)}", data={"success_count": 0, "failed_ids": not_found_nos})

            # 使用获取到的Id进行删除
            order_ids = list(order_no_id_map.values())
            success_count, failed_ids = await order_service.delete_logical_batch(order_ids)
            # 将失败的Id转换回订单编码
            id_order_no_map = {v: k for k, v in order_no_id_map.items()}
            failed_nos = [id_order_no_map[fid] for fid in failed_ids if fid in id_order_no_map]
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

        for order_no in order_nos:
            order_id = order_no_id_map.get(order_no)
            status = 200 if order_id not in failed_ids else 500
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单逻辑删除: orderNo={order_no}, id={order_id}",
                    method="POST",
                    path="/api/v1/oms/orders/delete_logical_batch",
                    status=status,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        # 汇总所有失败的订单编码
        all_failed_nos = not_found_nos + failed_nos
        
        if all_failed_nos:
            return Success(
                msg=f"部分订单删除失败，成功 {success_count} 条，失败 {len(all_failed_nos)} 条。失败订单: {', '.join(all_failed_nos)}",
                data={"success_count": success_count, "failed_ids": all_failed_nos}
            )
        
        return Success(msg=f"删除成功，共 {success_count} 条", data={"success_count": success_count, "failed_ids": []})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/delete_physical_batch", summary="批量物理删除（支持订单编码或订单Id）")
async def delete_physical_batch(req: Request, body: DeleteBatchIn):
    """批量物理删除订单，支持传入订单编码或订单Id"""
    try:
        order_nos: List[str] = [s.strip() for s in body.order_nos if s and s.strip()]
        if not order_nos:
            return Fail(code=400, msg="订单编码或订单Id不能为空")

        try:
            # 先通过订单编码获取对应的Id
            order_no_id_map = await order_service.fetch_order_ids_by_nos(order_nos)
            
            # 找出未找到的订单编码
            not_found_nos = [no for no in order_nos if no not in order_no_id_map]
            if not_found_nos:
                logger.warning(f"以下订单编码未找到: {not_found_nos}")
            
            if not order_no_id_map:
                return Success(msg=f"未找到对应的订单，订单编码: {', '.join(not_found_nos)}", data={"success_count": 0, "failed_ids": not_found_nos})

            # 使用获取到的Id进行删除
            order_ids = list(order_no_id_map.values())
            success_count, failed_ids = await order_service.delete_physical_batch(order_ids)
            # 将失败的Id转换回订单编码
            id_order_no_map = {v: k for k, v in order_no_id_map.items()}
            failed_nos = [id_order_no_map[fid] for fid in failed_ids if fid in id_order_no_map]
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

        for order_no in order_nos:
            order_id = order_no_id_map.get(order_no)
            status = 200 if order_id not in failed_ids else 500
            try:
                await AuditLog.create(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单物理删除: orderNo={order_no}, id={order_id}",
                    method="POST",
                    path="/api/v1/oms/orders/delete_physical_batch",
                    status=status,
                    response_time=0,
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        # 汇总所有失败的订单编码
        all_failed_nos = not_found_nos + failed_nos
        
        if all_failed_nos:
            return Success(
                msg=f"部分订单删除失败，成功 {success_count} 条，失败 {len(all_failed_nos)} 条。失败订单: {', '.join(all_failed_nos)}",
                data={"success_count": success_count, "failed_ids": all_failed_nos}
            )
        
        return Success(msg=f"删除成功，共 {success_count} 条", data={"success_count": success_count, "failed_ids": []})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/restore_logical", summary="订单逻辑删除恢复（支持订单编码或订单Id）")
async def restore_logical(req: Request, body: RestoreLogicalIn):
    """恢复被逻辑删除的订单，支持传入订单编码或订单Id"""
    try:
        # 先查询订单是否已删除（Deleted=1），同时验证 DeletedById
        deleted_order = await order_service.fetch_deleted_order_by_no(body.order_no, body.operator_id)
        
        if not deleted_order:
            # 检查订单是否存在但未删除
            order_no_id_map = await order_service.fetch_order_ids_by_nos([body.order_no])
            if order_no_id_map:
                return Success(msg="该订单未删除，无需恢复", data={"order_no": body.order_no, "restored": False})
            return Success(msg=f"未找到订单 {body.order_no} 且删除人为 {body.operator_id} 的已删除订单", data={"order_no": body.order_no, "restored": False})
        
        order_id = deleted_order["id"]

        try:
            await order_service.restore_logical(order_id=order_id, operator_id=body.operator_id)
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
                summary=f"订单逻辑删除恢复: orderNo={body.order_no}, id={order_id}, 操作人={body.operator_id}",
                method="POST",
                path="/api/v1/oms/orders/restore_logical",
                status=200,
                response_time=0,
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="恢复成功", data={"order_no": body.order_no, "restored": True})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")
