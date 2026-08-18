import logging

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.schemas.wms import (
    OwingStatusQueryIn,
    OwingStatusUpdateIn,
    OwingValidateIn,
    PriceModifyIn,
    PriceQueryIn,
    WmsDeleteBatchIn,
    WmsQueryIn,
    WmsRestoreLogicalIn,
    WmsValidateRequest,
)
from app.services.wms_service import wms_service
from app.utils.audit_log import create_operation_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/wms_curd/validate_stock", summary="验证单据状态（支持单据编码或单据Id）")
async def validate_stock(body: WmsValidateRequest):
    """验证单据状态，支持传入单据编码或单据Id"""
    try:
        nos: list[str] = [s.strip() for s in body.stock_nos if s and s.strip()]
        if not nos:
            return Fail(code=400, msg="单据编码或单据Id不能为空")

        result = await wms_service.validate_stock(nos, body.validate_type, body.operator_id)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"验证单据失败: {e}")
        return Fail(code=500, msg=f"验证失败: {e!s}")


@router.post("/wms_curd/query_status", summary="查询单据状态（Id、单号、AuditTime、Deleted、DeletedById、DeletedAt、删除人姓名）")
async def query_stock_status(body: WmsQueryIn):
    """查询单据状态信息，支持传入单据编码或单据Id

    返回字段：Id、单据编码、AuditTime、Deleted、DeletedById、DeletedAt、删除人姓名、删除人编码
    删除人通过 OA membership_userbaseinfo.UserCenterUserId 关联获取
    """
    try:
        nos: list[str] = [s.strip() for s in body.stock_nos if s and s.strip()]
        if not nos:
            return Fail(code=400, msg="单据编码或单据Id不能为空")

        result = await wms_service.query_stock_status(nos)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询单据状态失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/wms_curd/delete_logical_batch", summary="批量逻辑删除（支持单据编码或单据Id）")
async def delete_logical_batch(req: Request, body: WmsDeleteBatchIn):
    """批量逻辑删除单据，支持传入单据编码或单据Id"""
    try:
        nos: list[str] = [s.strip() for s in body.stock_nos if s and s.strip()]
        if not nos:
            return Fail(code=400, msg="单据编码或单据Id不能为空")

        # 先验证单据状态
        validation = await wms_service.validate_stock(nos, "logical_delete")
        if not validation["success"]:
            return Success(
                msg=f"验证失败: {validation['message']}",
                data={
                    "success_count": 0,
                    "failed_ids": validation["not_found_docs"] + [d["stock_no"] for d in validation["invalid_docs"]]
                }
            )

        try:
            success_count, failed_ids = await wms_service.delete_logical_batch(nos, body.operator_id)
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

        for dno in nos:
            status = 200 if dno not in failed_ids else 500
            try:
                await create_operation_audit_log(
                    user_id=user_id,
                    username=username,
                    module="WMS",
                    summary=f"单据逻辑删除: stock_no={dno}" + (f", 备注={body.remark}" if body.remark else ""),
                    method="POST",
                    path="/api/v1/wms/wms_curd/delete_logical_batch",
                    status=status,
                    request_body=body.model_dump(mode="json"),
                    response_body={"stock_no": dno, "failed": dno in failed_ids},
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        if failed_ids:
            return Success(msg=f"部分删除失败，成功 {success_count} 条，失败 {len(failed_ids)} 条", data={"success_count": success_count, "failed_ids": failed_ids})
        return Success(msg=f"删除成功，共 {success_count} 条", data={"success_count": success_count, "failed_ids": []})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/wms_curd/delete_physical_batch", summary="批量物理删除（支持单据编码或单据Id）")
async def delete_physical_batch(req: Request, body: WmsDeleteBatchIn):
    """批量物理删除单据，支持传入单据编码或单据Id"""
    try:
        nos: list[str] = [s.strip() for s in body.stock_nos if s and s.strip()]
        if not nos:
            return Fail(code=400, msg="单据编码或单据Id不能为空")

        # 先验证单据是否存在
        validation = await wms_service.validate_stock(nos, "physical_delete")
        if not validation["success"]:
            return Success(
                msg=f"验证失败: {validation['message']}",
                data={
                    "success_count": 0,
                    "failed_ids": validation["not_found_docs"]
                }
            )

        try:
            success_count, failed_ids = await wms_service.delete_physical_batch(nos, body.operator_id)
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

        for dno in nos:
            status = 200 if dno not in failed_ids else 500
            try:
                await create_operation_audit_log(
                    user_id=user_id,
                    username=username,
                    module="WMS",
                    summary=f"单据物理删除: stock_no={dno}" + (f", 备注={body.remark}" if body.remark else ""),
                    method="POST",
                    path="/api/v1/wms/wms_curd/delete_physical_batch",
                    status=status,
                    request_body=body.model_dump(mode="json"),
                    response_body={"stock_no": dno, "failed": dno in failed_ids},
                )
            except Exception as e:
                logger.warning(f"审计日志记录失败: {e}")

        if failed_ids:
            return Success(msg=f"部分删除失败，成功 {success_count} 条，失败 {len(failed_ids)} 条", data={"success_count": success_count, "failed_ids": failed_ids})
        return Success(msg=f"删除成功，共 {success_count} 条", data={"success_count": success_count, "failed_ids": []})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/wms_curd/restore_logical", summary="单据逻辑删除恢复（支持单据编码或单据Id）")
async def restore_logical(req: Request, body: WmsRestoreLogicalIn):
    """恢复被逻辑删除的单据，支持传入单据编码或单据Id"""
    try:
        # 先验证单据状态
        validation = await wms_service.validate_stock([body.stock_no], "restore", body.operator_id)
        if not validation["success"]:
            return Success(msg=validation["message"], data={"stock_no": body.stock_no, "restored": False})

        try:
            await wms_service.restore_logical(stock_no=body.stock_no, operator_id=body.operator_id)
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
                module="WMS",
                summary=f"单据逻辑删除恢复: stock_no={body.stock_no}, 操作人={body.operator_id}" + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/wms/wms_curd/restore_logical",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"stock_no": body.stock_no, "restored": True},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="恢复成功", data={"stock_no": body.stock_no, "restored": True})
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/wms_curd/price_query", summary="价格查询")
async def price_query(body: PriceQueryIn):
    """查询价格信息"""
    try:
        results = await wms_service.query_price(
            stock_code=body.stock_code,
            material_name=body.material_name,
            new_price=body.new_price
        )
        return Success(data=results, msg=f"查询到 {len(results)} 条记录")
    except Exception as e:
        logger.error(f"价格查询失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/wms_curd/price_modify", summary="价格修改")
async def price_modify(req: Request, body: PriceModifyIn):
    """修改价格"""
    try:
        try:
            await wms_service.modify_price(
                detail_id=body.detail_id,
                new_price=body.new_price
            )
        except Exception as e:
            logger.error(f"价格修改失败: {e}")
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
                module="WMS",
                summary=f"价格修改: detail_id={body.detail_id}, new_price={body.new_price}" + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/wms/wms_curd/price_modify",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"detail_id": body.detail_id, "new_price": body.new_price},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="价格修改成功")
    except Exception as e:
        logger.error(f"接口异常: {e}")
        return Fail(code=500, msg="服务异常")


@router.post("/wms_curd/validate_owing", summary="验证应付单是否对账")
async def validate_owing(body: OwingValidateIn):
    """验证应付单是否对账，有记录时ReconcStatus必须为0"""
    try:
        result = await wms_service.validate_owing_status(body.stock_id)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"应付单验证失败: {e}")
        return Fail(code=500, msg=f"验证失败: {e!s}")


@router.post("/wms_curd/owing_status_query", summary="查询出库单应收状态")
async def owing_status_query(body: OwingStatusQueryIn):
    """查询出库单应收状态信息"""
    try:
        result = await wms_service.query_owing_status(
            out_stock_no=body.out_stock_no,
            stock_id=body.stock_id
        )
        if result["success"]:
            return Success(data=result["data"], msg=result["message"])
        else:
            return Fail(code=400, msg=result["message"])
    except Exception as e:
        logger.error(f"应收状态查询失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/wms_curd/owing_status_update", summary="修改出库单应收状态")
async def owing_status_update(req: Request, body: OwingStatusUpdateIn):
    """修改出库单IsReceive字段"""
    try:
        result = await wms_service.update_receive_status(
            stock_id=body.stock_id,
            is_receive=body.is_receive,
            operator_id=body.operator_id,
            source_table=body.source_table
        )

        # 记录审计日志
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
                module="WMS",
                summary=f"应收状态修改: stock_id={body.stock_id}, is_receive={body.is_receive}, 操作人={body.operator_id}" + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/wms/wms_curd/owing_status_update",
                status=200 if result["success"] else 500,
                request_body=body.model_dump(mode="json"),
                response_body={"stock_id": body.stock_id, "success": result["success"]},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        if result["success"]:
            return Success(msg=result["message"])
        else:
            return Fail(code=400, msg=result["message"])
    except Exception as e:
        logger.error(f"应收状态修改失败: {e}")
        return Fail(code=500, msg=f"修改失败: {e!s}")
