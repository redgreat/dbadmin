import logging

from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import User
from app.utils.audit_log import create_operation_audit_log
from app.schemas.base import Fail, Success
from app.schemas.ehcf import (
    WorkorderManageQueryIn,
    WorkorderDeleteIn,
    WorkorderRestoreIn,
    WorkorderCloseIn,
)
from app.services.ehcf_service import ehcf_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/workorder-manage/query_status", summary="查询工单状态")
async def query_workorder_status(body: WorkorderManageQueryIn):
    """查询工单删除状态、工作状态等信息"""
    try:
        workorder_nos: list[str] = [s.strip() for s in body.workorder_nos if s and s.strip()]
        if not workorder_nos:
            return Fail(code=400, msg="工单编码或Id不能为空")

        result = await ehcf_service.query_workorder_status(workorder_nos)
        return Success(data=result, msg=result["message"])
    except Exception as e:
        logger.error(f"查询工单状态失败: {e}")
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/workorder-manage/delete_logical", summary="工单逻辑删除")
async def delete_logical_workorder(req: Request, body: WorkorderDeleteIn):
    """批量逻辑删除工单"""
    try:
        workorder_nos: list[str] = [s.strip() for s in body.workorder_nos if s and s.strip()]
        if not workorder_nos:
            return Fail(code=400, msg="工单编码或Id不能为空")

        # 先查询工单Id（同一编码可能对应多条工单，如加装/检修）
        id_result = await ehcf_service.fetch_workorder_ids_by_nos(workorder_nos)
        found_docs = id_result.get("found_docs", [])
        not_found_nos = id_result.get("not_found_docs", [])

        if not found_docs:
            return Success(msg=f"未找到对应工单: {', '.join(not_found_nos)}", data={"success_count": 0, "failed_ids": not_found_nos})

        # 按输入编码分组，识别一对多的工单
        grouped: dict[str, list[dict]] = {}
        for doc in found_docs:
            grouped.setdefault(doc["input"], []).append(doc)
        multi_docs = [{"input": k, "docs": v} for k, v in grouped.items() if len(v) > 1]
        all_ids = list(dict.fromkeys(str(doc["workorder_id"]) for doc in found_docs))

        if body.workorder_ids:
            # 用户指定了具体工单Id（不全部删除）
            valid_ids = set(all_ids)
            invalid_ids = [wid for wid in body.workorder_ids if wid not in valid_ids]
            if invalid_ids:
                return Fail(code=400, msg=f"以下工单Id不在本次查询结果中: {', '.join(invalid_ids)}")
            workorder_ids = list(dict.fromkeys(body.workorder_ids))
        elif body.delete_all:
            # 确认全部删除
            workorder_ids = all_ids
        elif multi_docs:
            # 同一编码对应多条工单，需要前端弹窗确认删除范围
            return Success(
                msg="存在工单编码对应多条记录，请确认是否全部删除",
                data={
                    "need_confirm": True,
                    "multi_docs": multi_docs,
                    "all_ids": all_ids,
                },
            )
        else:
            workorder_ids = all_ids

        success_count, failed_ids = await ehcf_service.delete_logical_workorder(workorder_ids, body.operator_id)

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
                summary=f"工单逻辑删除: {', '.join(workorder_nos)}" + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/ehcf/workorder-manage/delete_logical",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"success_count": success_count, "failed_ids": failed_ids},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(
            msg=f"删除完成: 成功 {success_count} 条" + (f", 失败 {len(failed_ids)} 条" if failed_ids else ""),
            data={"success_count": success_count, "failed_ids": failed_ids},
        )
    except Exception as e:
        logger.error(f"工单逻辑删除失败: {e}")
        return Fail(code=500, msg=f"删除失败: {e!s}")


@router.post("/workorder-manage/restore_logical", summary="工单逻辑删除恢复")
async def restore_logical_workorder(req: Request, body: WorkorderRestoreIn):
    """恢复被逻辑删除的工单"""
    try:
        workorder_no = body.workorder_no.strip()
        if not workorder_no:
            return Fail(code=400, msg="工单编码或Id不能为空")

        # 先查询工单Id
        id_result = await ehcf_service.fetch_workorder_ids_by_nos([workorder_no])
        id_map = id_result.get("workorder_id_map", {})
        if not id_map:
            return Success(msg=f"未找到工单 {workorder_no}", data={"restored": False})

        workorder_id = id_map[workorder_no]

        try:
            await ehcf_service.restore_logical_workorder(workorder_id, body.operator_id)
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
                module="EHCF",
                summary=f"工单逻辑删除恢复: {workorder_no}" + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/ehcf/workorder-manage/restore_logical",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"workorder_no": workorder_no, "restored": True},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(msg="恢复成功", data={"workorder_no": workorder_no, "restored": True})
    except Exception as e:
        logger.error(f"工单恢复失败: {e}")
        return Fail(code=500, msg=f"恢复失败: {e!s}")


@router.post("/workorder-manage/close", summary="关闭工单")
async def close_workorder(req: Request, body: WorkorderCloseIn):
    """批量关闭工单，设置 WorkStatus=10"""
    try:
        workorder_nos: list[str] = [s.strip() for s in body.workorder_nos if s and s.strip()]
        if not workorder_nos:
            return Fail(code=400, msg="工单编码或Id不能为空")

        # 先查询工单Id
        id_result = await ehcf_service.fetch_workorder_ids_by_nos(workorder_nos)
        id_map = id_result.get("workorder_id_map", {})
        not_found_nos = id_result.get("not_found_docs", [])

        if not id_map:
            return Success(msg=f"未找到对应工单: {', '.join(not_found_nos)}", data={"success_count": 0, "failed_ids": not_found_nos})

        workorder_ids = list(id_map.values())
        success_count, failed_ids = await ehcf_service.close_workorder_batch(workorder_ids)

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
                summary=f"工单关闭: {', '.join(workorder_nos)}" + (f", 备注={body.remark}" if body.remark else ""),
                method="POST",
                path="/api/v1/ehcf/workorder-manage/close",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"success_count": success_count, "failed_ids": failed_ids},
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")

        return Success(
            msg=f"关闭完成: 成功 {success_count} 条" + (f", 失败 {len(failed_ids)} 条" if failed_ids else ""),
            data={"success_count": success_count, "failed_ids": failed_ids},
        )
    except Exception as e:
        logger.error(f"工单关闭失败: {e}")
        return Fail(code=500, msg=f"关闭失败: {e!s}")
