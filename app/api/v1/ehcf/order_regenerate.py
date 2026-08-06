import logging

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.utils.audit_log import create_operation_audit_log
from app.schemas.base import Fail, Success
from app.schemas.ehcf import WorkorderQueryIn, FixDetailIdIn, RegenerateOrderIn
from app.services.ehcf_service import ehcf_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/order-regenerate/query_workorder", summary="查询工单基础信息")
async def query_workorder(body: WorkorderQueryIn):
    """根据工单AppCode或Id查询基础信息"""
    try:
        result = await ehcf_service.query_workorder(body.keyword)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询工单失败: {e}")
        return Fail(code=500, msg=f"查询失败: {str(e)}")


@router.post("/order-regenerate/query_details", summary="查询明细Id列表")
async def query_details(body: FixDetailIdIn):
    """查询需要修复的明细Id列表"""
    try:
        result = await ehcf_service.query_detail_ids(body.workorder_id)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询明细失败: {e}")
        return Fail(code=500, msg=f"查询失败: {str(e)}")


@router.post("/order-regenerate/fix_detail", summary="修复订单明细Id")
async def fix_detail(req: Request, body: FixDetailIdIn):
    """生成新OE编号并更新明细Id"""
    try:
        result = await ehcf_service.fix_order_detail_ids(body.workorder_id)

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
                module="EHCF",
                summary=f"修复订单明细Id: workorder_id={body.workorder_id}, 成功{result['updated_count']}条",
                method="POST",
                path="/api/v1/ehcf/order-regenerate/fix_detail",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"success": result["success"], "updated": result["updated_count"]},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"修复明细Id失败: {e}")
        return Fail(code=500, msg=f"修复失败: {str(e)}")


@router.post("/order-regenerate/regenerate_order", summary="重新生成订单Id和明细Id")
async def regenerate_order(req: Request, body: RegenerateOrderIn):
    """重新生成OI订单编号和订单编码，并更新所有关联表"""
    try:
        result = await ehcf_service.regenerate_order_ids(body.workorder_id)

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
                module="EHCF",
                summary=f"重新生成订单Id: workorder_id={body.workorder_id}, 新OI={result.get('summary', {}).get('new_oi_id', '')}",
                method="POST",
                path="/api/v1/ehcf/order-regenerate/regenerate_order",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"success": result["success"], "updated": result["updated_count"]},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"重新生成订单Id失败: {e}")
        return Fail(code=500, msg=f"重新生成失败: {str(e)}")
