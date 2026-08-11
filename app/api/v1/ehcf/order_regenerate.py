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


async def _check_workorder_not_completed(workorder_id: str):
    """检查工单是否已完成（WorkStatus=9），已完成则抛出异常"""
    status_result = await ehcf_service.query_workorder(workorder_id)
    if not status_result.get("found"):
        raise ValueError(f"未找到工单: {workorder_id}")
    wo = status_result["workorder"]
    if wo.get("work_status") == 9:
        raise ValueError(f"工单 {wo.get('app_code', workorder_id)} 已完成（WorkStatus=9），不可操作")


async def _get_user_info(req: Request):
    """从请求中提取用户信息"""
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
    return user_id, username


def _build_change_summary(results: dict, max_items: int = 10) -> str:
    """构建旧值→新值的摘要"""
    updated = results.get("updated", [])
    if not updated:
        return ""
    parts = []
    for item in updated[:max_items]:
        tbl = item.get("table", "?")
        old = item.get("old", "?")
        new = item.get("new", "?")
        field = item.get("field", "")
        label = f"{tbl}.{field}" if field else tbl
        parts.append(f"{label}: {old}→{new}")
    if len(updated) > max_items:
        parts.append(f"...共{len(updated)}条")
    return "; ".join(parts)


@router.post("/order-regenerate/fix_detail", summary="修复订单明细Id")
async def fix_detail(req: Request, body: FixDetailIdIn):
    """生成新OE编号并更新明细Id，不可逆操作"""
    try:
        # 检查工单状态
        await _check_workorder_not_completed(body.workorder_id)

        result = await ehcf_service.fix_order_detail_ids(body.workorder_id)

        user_id, username = await _get_user_info(req)
        change_summary = _build_change_summary(result.get("results", {}))

        try:
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="EHCF",
                summary=f"修复订单明细Id: workorder_id={body.workorder_id}, 成功{result['updated_count']}条"
                        + (f", 变更: {change_summary}" if change_summary else "")
                        + (f", 备注: {body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/ehcf/order-regenerate/fix_detail",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={
                    "success": result["success"],
                    "updated": result["updated_count"],
                    "changes": change_summary,
                },
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(data=result, msg=result["message"])
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"修复明细Id失败: {e}")
        return Fail(code=500, msg=f"修复失败: {str(e)}")


@router.post("/order-regenerate/regenerate_order", summary="重新生成订单Id和明细Id")
async def regenerate_order(req: Request, body: RegenerateOrderIn):
    """重新生成OI订单编号和订单编码，并更新所有关联表，不可逆操作"""
    try:
        # 检查工单状态
        await _check_workorder_not_completed(body.workorder_id)

        result = await ehcf_service.regenerate_order_ids(body.workorder_id)

        user_id, username = await _get_user_info(req)
        change_summary = _build_change_summary(result.get("results", {}))
        summary_info = result.get("summary", {})
        new_oi = summary_info.get("new_oi_id", "?")
        new_on = summary_info.get("new_order_no", "?")

        try:
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="EHCF",
                summary=f"[不可逆]重新生成订单Id: workorder_id={body.workorder_id}, "
                        + f"新OI={new_oi}, 新编码={new_on}, 成功{result['updated_count']}条"
                        + (f", 变更: {change_summary}" if change_summary else "")
                        + (f", 备注: {body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/ehcf/order-regenerate/regenerate_order",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={
                    "success": result["success"],
                    "updated": result["updated_count"],
                    "new_oi": new_oi,
                    "new_order_no": new_on,
                    "changes": change_summary,
                },
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(data=result, msg=result["message"])
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"重新生成订单Id失败: {e}")
        return Fail(code=500, msg=f"重新生成失败: {str(e)}")
