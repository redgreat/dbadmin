import logging
from datetime import datetime

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.schemas.oms import (
    CheckRecordDeleteIn,
    DeleteBatchIn,
    GfsDeleteIn,
    GfsQueryIn,
    OrderQueryIn,
    RestoreLogicalIn,
    ReturnOriginQueryIn,
    ReturnOriginUpdateIn,
    UpdateAuditTimeBatchIn,
)
from app.services.order_service import order_service
from app.utils.audit_log import create_operation_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/update_audit_time_batch", summary="批量更新审核时间（支持订单编码或订单Id）")
async def update_audit_time_batch(req: Request, body: UpdateAuditTimeBatchIn):
    """批量更新订单审核时间，支持传入订单编码或订单Id"""
    try:
        order_nos: list[str] = [s.strip() for s in body.order_nos if s and s.strip()]
        if not order_nos:
            return Fail(code=400, msg="订单编码或订单Id不能为空")

        if not body.audit_time:
            return Fail(code=400, msg="修改时间不能为空")

        new_time: datetime = body.audit_time

        try:
            # 先通过订单编码获取对应的Id
            order_result = await order_service.fetch_order_ids_by_nos(order_nos)
            order_no_id_map = order_result.get("order_id_map", {})
            not_found_nos = order_result.get("not_found_docs", [])

            if not_found_nos:
                logger.warning(f"以下订单编码未找到: {not_found_nos}")

            if not order_no_id_map:
                return Success(msg=f"未找到对应的订单，订单编码: {', '.join(not_found_nos)}", data={"success_count": 0, "failed_ids": not_found_nos})

            # 使用获取到的Id进行更新
            order_ids = list(order_no_id_map.values())
            audit_time_result = await order_service.fetch_audit_time_map(order_nos)
            old_map = audit_time_result.get("audit_time_map", {})
            affected = await order_service.update_audit_time_batch(order_ids, new_time)
            new_audit_time_result = await order_service.fetch_audit_time_map(order_nos)
            new_map = new_audit_time_result.get("audit_time_map", {})
        except Exception as e:
            logger.error(f"执行更新失败: {e}")
            return Fail(code=500, msg=f"执行失败: {e!s}")

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
                await create_operation_audit_log(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单审核时间更新: orderNo={order_no}, 原={before}, 新={after}" + (f", 备注={body.remark}" if body.remark else ""),
                    method="POST",
                    path="/api/v1/oms/orders/update_audit_time_batch",
                    status=200,
                    request_body=body.model_dump(mode="json"),
                    response_body={"order_no": order_no, "before": str(before), "after": str(after)},
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
        order_nos: list[str] = [s.strip() for s in body.order_nos if s and s.strip()]
        if not order_nos:
            return Fail(code=400, msg="订单编码或订单Id不能为空")

        try:
            # 先通过订单编码获取对应的Id
            order_result = await order_service.fetch_order_ids_by_nos(order_nos)
            order_no_id_map = order_result.get("order_id_map", {})
            not_found_nos = order_result.get("not_found_docs", [])

            if not_found_nos:
                logger.warning(f"以下订单编码未找到: {not_found_nos}")

            if not order_no_id_map:
                return Success(msg=f"未找到对应的订单，订单编码: {', '.join(not_found_nos)}", data={"success_count": 0, "failed_ids": not_found_nos})

            # 使用获取到的Id进行删除
            order_ids = list(order_no_id_map.values())
            success_count, failed_ids = await order_service.delete_logical_batch(order_ids, body.operator_id)
            # 将失败的Id转换回订单编码
            id_order_no_map = {v: k for k, v in order_no_id_map.items()}
            failed_nos = [id_order_no_map[fid] for fid in failed_ids if fid in id_order_no_map]
        except Exception as e:
            logger.error(f"逻辑删除失败: {e}")
            return Fail(code=500, msg=f"执行失败: {e!s}")

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
                await create_operation_audit_log(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单逻辑删除: orderNo={order_no}, id={order_id}" + (f", 备注={body.remark}" if body.remark else ""),
                    method="POST",
                    path="/api/v1/oms/orders/delete_logical_batch",
                    status=status,
                    request_body=body.model_dump(mode="json"),
                    response_body={
                        "order_no": order_no,
                        "order_id": order_id,
                        "failed": order_no in not_found_nos or order_no in failed_nos,
                    },
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
        order_nos: list[str] = [s.strip() for s in body.order_nos if s and s.strip()]
        if not order_nos:
            return Fail(code=400, msg="订单编码或订单Id不能为空")

        try:
            # 先通过订单编码获取对应的Id
            order_result = await order_service.fetch_order_ids_by_nos(order_nos)
            order_no_id_map = order_result.get("order_id_map", {})
            not_found_nos = order_result.get("not_found_docs", [])

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
            return Fail(code=500, msg=f"执行失败: {e!s}")

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
                await create_operation_audit_log(
                    user_id=user_id,
                    username=username,
                    module="OMS",
                    summary=f"订单物理删除: orderNo={order_no}, id={order_id}" + (f", 备注={body.remark}" if body.remark else ""),
                    method="POST",
                    path="/api/v1/oms/orders/delete_physical_batch",
                    status=status,
                    request_body=body.model_dump(mode="json"),
                    response_body={
                        "order_no": order_no,
                        "order_id": order_id,
                        "failed": order_no in not_found_nos or order_no in failed_nos,
                    },
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
            order_result = await order_service.fetch_order_ids_by_nos([body.order_no])
            order_no_id_map = order_result.get("order_id_map", {})
            if order_no_id_map:
                return Success(msg="该订单未删除，无需恢复", data={"order_no": body.order_no, "restored": False})
            return Success(msg=f"未找到订单 {body.order_no} 且删除人为 {body.operator_id} 的已删除订单", data={"order_no": body.order_no, "restored": False})

        order_id = deleted_order["id"]

        try:
            await order_service.restore_logical(order_id=order_id, operator_id=body.operator_id)
        except Exception as e:
            logger.error(f"恢复失败: {e}")
            return Fail(code=500, msg=f"执行失败: {e!s}")

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
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="OMS",
                summary=f"订单逻辑删除恢复: orderNo={body.order_no}, id={order_id}, 操作人={body.operator_id}" + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/oms/orders/restore_logical",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"order_no": body.order_no, "order_id": order_id, "restored": True},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="恢复成功", data={"order_no": body.order_no, "restored": True})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/query_status", summary="查询订单状态（Id、OrderNo、AuditTime、Deleted、DeletedById、DeletedAt、删除人姓名）")
async def query_order_status(body: OrderQueryIn):
    """查询订单状态信息，支持传入订单编码或订单Id，返回删除状态和删除人姓名"""
    try:
        order_nos: list[str] = [s.strip() for s in body.order_nos if s and s.strip()]
        if not order_nos:
            return Fail(code=400, msg="订单编码或订单Id不能为空")

        result = await order_service.query_order_status(order_nos)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询订单状态失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/query_gfs_status", summary="查询GFS订单状态（验证对账、开票、回款、推广费状态）")
async def query_gfs_status(body: GfsQueryIn):
    """查询GFS订单状态，验证是否允许删除"""
    try:
        result = await order_service.query_gfs_order_status(
            order_nos=body.order_nos,
            order_ids=body.order_ids,
        )
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询GFS订单状态失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/delete_gfs_order", summary="调用GFS存储过程删除订单")
async def delete_gfs_order(req: Request, body: GfsDeleteIn):
    """调用GFS存储过程删除订单"""
    try:
        await order_service.delete_gfs_order(body.order_id)

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
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="OMS",
                summary=f"GFS订单删除: order_id={body.order_id}",
                method="POST",
                path="/api/v1/oms/orders/delete_gfs_order",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"order_id": body.order_id, "deleted": True},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="GFS订单删除成功", data={"order_id": body.order_id, "deleted": True})
    except Exception as e:
        logger.error(f"GFS订单删除失败: {e}")
        return Fail(code=500, msg=f"删除失败: {e!s}")


@router.post("/delete_check_record", summary="删除校验记录")
async def delete_check_record(req: Request, body: CheckRecordDeleteIn):
    """删除校验记录（mallcenter.sys_reoperatecheck）"""
    try:
        await order_service.delete_check_record(body.order_id)

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
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="OMS",
                summary=f"删除校验记录: order_id={body.order_id}",
                method="POST",
                path="/api/v1/oms/orders/delete_check_record",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"order_id": body.order_id, "deleted": True},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="校验记录删除成功", data={"order_id": body.order_id, "deleted": True})
    except Exception as e:
        logger.error(f"删除校验记录失败: {e}")
        return Fail(code=500, msg=f"删除失败: {e!s}")


@router.post("/query_return_order_origin", summary="查询退货单原单信息")
async def query_return_order_origin(body: ReturnOriginQueryIn):
    """查询退货单原单信息，通过退货单Id或编码关联查询订单和原单信息"""
    try:
        return_order_no = body.return_order_no.strip()
        if not return_order_no:
            return Fail(code=400, msg="退货单Id或编码不能为空")

        result = await order_service.query_return_order_origin(return_order_no)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询退货单原单信息失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/query_origin_order_info", summary="查询原订单信息（用于变更退货单原单）")
async def query_origin_order_info(body: ReturnOriginQueryIn):
    """查询原订单信息，用于变更退货单原单时验证目标订单是否存在"""
    try:
        origin_order_no = body.return_order_no.strip()
        if not origin_order_no:
            return Fail(code=400, msg="原订单Id或编码不能为空")

        result = await order_service.query_origin_order_info(origin_order_no)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询原订单信息失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/update_return_order_origin", summary="更新退货单原单信息")
async def update_return_order_origin(req: Request, body: ReturnOriginUpdateIn):
    """更新退货单的原单信息，变更tb_orderdetail的OriginOrderId和OriginOrderNo"""
    try:
        return_order_no = body.return_order_no.strip()
        new_origin_order_no = body.new_origin_order_no.strip()
        if not return_order_no:
            return Fail(code=400, msg="退货单Id或编码不能为空")
        if not new_origin_order_no:
            return Fail(code=400, msg="变更原订单Id或编码不能为空")
        if not body.updated_by_id:
            return Fail(code=400, msg="数据更新人不能为空")

        # 1. 查询退货单信息，获取退货单Id
        return_result = await order_service.query_return_order_origin(return_order_no)
        if not return_result["found_docs"]:
            return Fail(code=400, msg=f"未找到退货单: {return_order_no}")
        return_order_id = return_result["found_docs"][0]["order_id"]

        # 2. 查询目标原订单信息，获取原订单Id和编码
        origin_result = await order_service.query_origin_order_info(new_origin_order_no)
        if not origin_result["found_docs"]:
            return Fail(code=400, msg=f"未找到原订单: {new_origin_order_no}")
        origin_order_id = origin_result["found_docs"][0]["id"]
        origin_order_no_actual = origin_result["found_docs"][0]["order_no"]

        # 3. 执行更新
        updated = await order_service.update_return_order_origin(
            return_order_id=return_order_id,
            origin_order_id=origin_order_id,
            origin_order_no=origin_order_no_actual,
            updated_by_id=body.updated_by_id,
        )
        if not updated:
            return Fail(code=500, msg="更新失败，未影响任何记录")

        # 4. 记录审计日志
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
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="OMS",
                summary=f"退货单原单更新: 退货单={return_order_no}, 新原单={new_origin_order_no}, 更新人={body.updated_by_id}"
                + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/oms/orders/update_return_order_origin",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={
                    "return_order_id": return_order_id,
                    "origin_order_id": origin_order_id,
                    "origin_order_no": origin_order_no_actual,
                },
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(
            msg="退货单原单更新成功",
            data={
                "return_order_id": return_order_id,
                "origin_order_id": origin_order_id,
                "origin_order_no": origin_order_no_actual,
            },
        )
    except Exception as e:
        logger.error(f"更新退货单原单失败: {e}")
        return Fail(code=500, msg=f"更新失败: {e!s}")
