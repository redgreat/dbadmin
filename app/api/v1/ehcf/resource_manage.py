import logging

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.schemas.ehcf import (
    ResourceDeleteIn,
    ResourceQueryIn,
    ResourceRestoreIn,
)
from app.services.ehcf_service import ehcf_service
from app.utils.audit_log import create_operation_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.post("/resource-manage/query", summary="附件列表查询")
async def query_resources(req: Request, body: ResourceQueryIn):
    """分页查询工单附件（支持按工单、附件类型、删除人筛选，可包含已删除）"""
    try:
        result = await ehcf_service.query_resources(
            keyword=body.keyword,
            source_type=body.source_type,
            deleted_by_id=body.deleted_by_id,
            include_deleted=body.include_deleted,
            page=body.page,
            page_size=body.page_size,
        )
        return Success(data=result, msg=result["message"])
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"附件查询失败: {e}")
        return Fail(code=500, msg=f"查询失败: {str(e)}")


@router.post("/resource-manage/delete", summary="附件逻辑删除")
async def delete_resources(req: Request, body: ResourceDeleteIn):
    """逻辑删除附件（联动删除资源文件，仅更新删除标记字段），不可逆操作"""
    try:
        result = await ehcf_service.delete_resources(
            resource_ids=body.resource_ids,
            operator_id=body.operator_id,
            remark=body.remark,
        )

        user_id, username = await _get_user_info(req)
        try:
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="EHCF",
                summary=f"附件逻辑删除: 附件Id={','.join(body.resource_ids)}, "
                        + f"成功{result['updated_count']}条"
                        + (f", 原因备注: {body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/ehcf/resource-manage/delete",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={
                    "success": result["failed_count"] == 0,
                    "updated": result["updated_count"],
                },
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(data=result, msg=result["message"])
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"附件删除失败: {e}")
        return Fail(code=500, msg=f"删除失败: {str(e)}")


@router.post("/resource-manage/restore", summary="附件恢复")
async def restore_resources(req: Request, body: ResourceRestoreIn):
    """恢复已删除附件（填写操作人时仅恢复该删除人删除的附件）"""
    try:
        result = await ehcf_service.restore_resources(
            resource_ids=body.resource_ids,
            operator_id=body.operator_id,
            remark=body.remark,
        )

        user_id, username = await _get_user_info(req)
        try:
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="EHCF",
                summary=f"附件恢复: 附件Id={','.join(body.resource_ids)}, "
                        + f"成功{result['updated_count']}条"
                        + (f", 原因备注: {body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/ehcf/resource-manage/restore",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={
                    "success": result["failed_count"] == 0,
                    "updated": result["updated_count"],
                },
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(data=result, msg=result["message"])
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"附件恢复失败: {e}")
        return Fail(code=500, msg=f"恢复失败: {str(e)}")
