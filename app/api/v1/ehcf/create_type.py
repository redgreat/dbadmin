import logging

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.schemas.ehcf import WorkorderCreateTypeQueryIn, WorkorderCreateTypeUpdateIn
from app.services.ehcf_service import ehcf_service
from app.utils.audit_log import create_operation_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create-type/query", summary="查询工单单据来源(CreateType)")
async def query_create_type(body: WorkorderCreateTypeQueryIn):
    """查询工单单据来源，返回服务商编码与是否允许修改（仅充电桩可改）"""
    try:
        workorder_nos: list[str] = [
            s.strip() for s in body.workorder_nos if s and s.strip()
        ]
        if not workorder_nos:
            return Fail(code=400, msg="工单编码或Id不能为空")

        result = await ehcf_service.query_create_type(workorder_nos)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询工单单据来源失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/create-type/update", summary="修改工单单据来源(CreateType)")
async def update_create_type(req: Request, body: WorkorderCreateTypeUpdateIn):
    """修改工单单据来源，仅充电桩单据（ServiceProviderCode=1067）允许修改"""
    try:
        workorder_no = body.workorder_no.strip()
        if not workorder_no:
            return Fail(code=400, msg="工单编码或Id不能为空")

        result = await ehcf_service.update_create_type(
            workorder_no, body.create_type, restrict_charging_pile=True
        )

        if not result["success"]:
            return Fail(code=400, msg=result["message"])

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
                module="EHCF",
                summary=(
                    f"修改工单单据来源: {workorder_no}, CreateType {result['old_create_type']} -> {result['new_create_type']}"
                    + (f", 操作人={body.operator_id}" if body.operator_id else "")
                    + (f", 备注={body.remark}" if body.remark else "")
                ),
                method="POST",
                path="/api/v1/ehcf/create-type/update",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body=result,
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg=result["message"], data=result)
    except Exception as e:
        logger.error(f"修改工单单据来源失败: {e}")
        return Fail(code=500, msg=f"修改失败: {e!s}")
