import logging
from typing import List

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.schemas.oa import PositiveTimeRequest
from app.services.oa_service import oa_positive_time_service
from app.utils.audit_log import create_operation_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


def _clean_codes(codes: List[str]) -> List[str]:
    result = []
    seen = set()
    for code in codes:
        value = (code or "").strip()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


async def _get_user(req: Request) -> tuple[int, str]:
    try:
        token = req.headers.get("token")
        user_obj: User = None
        if token:
            user_obj = await AuthControl.is_authed(token)
        if user_obj:
            return user_obj.id, user_obj.username
    except Exception:
        pass
    return 0, ""


@router.post("/validate", summary="验证转正时间")
async def validate_positive_time(req: Request, body: PositiveTimeRequest):
    try:
        codes = _clean_codes(body.codes)
        if not codes:
            return Fail(code=400, msg="人员工号不能为空")

        result = await oa_positive_time_service.validate_positive_time(codes)
        return Success(msg="验证完成", data=result)
    except Exception as e:
        logger.error(f"验证转正时间失败: {e}", exc_info=True)
        return Fail(code=500, msg=f"验证失败: {str(e)}")


@router.post("/execute", summary="修改转正时间")
async def execute_positive_time(req: Request, body: PositiveTimeRequest):
    try:
        codes = _clean_codes(body.codes)
        if not codes:
            return Fail(code=400, msg="人员工号不能为空")
        if not body.positive_time:
            return Fail(code=400, msg="修改时间不能为空")

        result = await oa_positive_time_service.update_positive_time(codes, body.positive_time)

        try:
            user_id, username = await _get_user(req)
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="OA运维",
                summary=f"转正时间修改: codes={','.join(codes)}, time={result.get('positive_time')}",
                method="POST",
                path="/api/v1/oa/positive-time/execute",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={
                    "updated_codes": result.get("updated_codes"),
                    "not_found_codes": result.get("not_found_codes"),
                    "positive_time": result.get("positive_time"),
                    "oa_affected": result.get("oa_affected"),
                    "fcc_affected": result.get("fcc_affected"),
                },
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="执行完成", data=result)
    except Exception as e:
        logger.error(f"修改转正时间失败: {e}", exc_info=True)
        return Fail(code=500, msg=f"执行失败: {str(e)}")
