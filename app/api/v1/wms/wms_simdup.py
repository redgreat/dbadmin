"""
仓储中心 - SIM卡重复入库验证
- 下载模板Excel
- 上传Excel验证重复入库（写临时表 + 验证SQL + 存记录 + 导出 + 审计日志）
- 导出/下载某次验证记录的重复编码
- 验证记录列表 / 详情 / 结果导出（历史可下载）
- 对外API：直接调用验证重复编码（复用平台JWT token鉴权 + 记录验证日志/审计日志）
"""
import logging
import os

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.dependency import AuthControl
from app.models.admin import User
from app.models.simdupverify import SimDupVerifyRecord, SimDupVerifyResult
from app.schemas.base import Fail, Success, SuccessExtra
from app.services.simdup_service import build_template_bytes, simdup_service
from app.utils.audit_log import create_operation_audit_log

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


# ────────────────────────── 请求模型 ──────────────────────────
class SimDupCodesIn(BaseModel):
    """对外API：直接传入SimNumber列表验证"""
    sim_numbers: list[str] = Field(..., description="SimNumber列表（物料编码）", min_length=1, max_length=20000)
    caller: str = Field(default="", description="调用方标识（可选，记入验证日志）", max_length=100)


class SimDupRecordQueryIn(BaseModel):
    """记录列表查询入参"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
    status: str = Field(default="", description="按状态筛选: processing/completed/failed")
    source: str = Field(default="", description="按来源筛选: web/api")


# ────────────────────────── 内部工具 ──────────────────────────
async def _get_user(req: Request) -> tuple[int, str]:
    token = req.headers.get("token")
    user_obj: User = None
    if token:
        user_obj = await AuthControl.is_authed(token)
    return (user_obj.id if user_obj else 0, user_obj.username if user_obj else "")


async def _audit(
    user_id: int,
    username: str,
    summary: str,
    path: str,
    request_body,
    response_body,
    status: int = 200,
):
    try:
        await create_operation_audit_log(
            user_id=user_id,
            username=username,
            module="WMS",
            summary=summary,
            method="POST",
            path=path,
            status=status,
            request_body=request_body,
            response_body=response_body,
        )
    except Exception as e:
        logger.warning(f"审计日志记录失败: {e}")


# ────────────────────────── 模板下载 ──────────────────────────
@router.get("/simdup/template", summary="下载SIM卡重复入库验证Excel模板")
async def download_template():
    """下载固定模板Excel（仅一列 SimNumber）"""
    content = build_template_bytes()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=simdup_verify_template.xlsx"},
    )


# ────────────────────────── 上传验证 ──────────────────────────
@router.post("/simdup/verify", summary="上传Excel验证SIM卡重复入库")
async def verify_upload(req: Request, file: UploadFile = File(...)):
    """上传Excel（仅一列SimNumber），验证系统内是否有重复卡号，保存验证记录并导出重复编码"""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls", ".csv")):
        return Fail(code=400, msg="仅支持 .xlsx / .xls / .csv 文件")
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return Fail(code=400, msg=f"文件大小超过限制（最大20MB），当前 {len(content)/1024/1024:.2f}MB")
    if not content:
        return Fail(code=400, msg="文件内容为空")

    user_id, username = await _get_user(req)

    try:
        record = await simdup_service.verify_from_upload(
            content=content,
            filename=file.filename,
            user_id=user_id,
            username=username,
            source="web",
        )
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"SIM重复入库验证失败: {e}", exc_info=True)
        return Fail(code=500, msg=f"验证失败: {e!s}")

    await _audit(
        user_id,
        username,
        f"SIM重复入库验证（页面导入 {file.filename}）: {record.message}",
        "/api/v1/wms/simdup/verify",
        {"filename": file.filename},
        {"batch_no": record.batch_no, "total": record.total_count, "duplicates": record.duplicate_count},
        status=200 if record.status == "completed" else 500,
    )

    return Success(
        msg=record.message,
        data={
            "record_id": record.id,
            "batch_no": record.batch_no,
            "status": record.status,
            "total_count": record.total_count,
            "duplicate_count": record.duplicate_count,
            "can_download": bool(record.result_file_path),
        },
    )


# ────────────────────────── 导出/下载某次验证的重复编码 ──────────────────────────
@router.get("/simdup/record/{record_id}/export", summary="下载某次验证记录的重复编码Excel")
async def export_record(record_id: int, req: Request):
    """下载历史验证记录的重复编码Excel（随时可下载之前的记录）"""
    record = await SimDupVerifyRecord.get_or_none(id=record_id)
    if not record:
        return Fail(code=404, msg="验证记录不存在")
    if not record.result_file_path:
        return Fail(code=400, msg="该记录没有可下载的重复编码文件（无重复或导出失败）")
    if not os.path.exists(record.result_file_path):
        # 文件丢失：尝试从结果子表重新生成
        results = await SimDupVerifyResult.filter(record_id=record.id).values("sim_number")
        dup = [r["sim_number"] for r in results]
        if dup:
            record.result_file_path = simdup_service.export_excel(record.batch_no, dup)
            await record.save(update_fields=["result_file_path"])
        else:
            return Fail(code=400, msg="该记录没有重复编码可下载")
    user_id, username = await _get_user(req)
    await _audit(
        user_id,
        username,
        f"下载SIM重复入库验证记录: batch_no={record.batch_no}",
        "/api/v1/wms/simdup/record/export",
        {"record_id": record_id},
        {"batch_no": record.batch_no},
    )
    # 先读取字节，避免StreamingResponse迭代期间文件句柄未释放
    with open(record.result_file_path, "rb") as f:
        file_bytes = f.read()
    return StreamingResponse(
        iter([file_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=simdup_{record.batch_no}.xlsx"},
    )


# ────────────────────────── 验证记录列表 ──────────────────────────
@router.post("/simdup/record/list", summary="SIM卡重复入库验证记录列表")
async def record_list(body: SimDupRecordQueryIn):
    q = SimDupVerifyRecord.all()
    if body.status:
        q = q.filter(status=body.status)
    if body.source:
        q = q.filter(source=body.source)
    total = await q.count()
    records = (
        await q.order_by("-created_at")
        .offset((body.page - 1) * body.page_size)
        .limit(body.page_size)
        .values(
            "id",
            "batch_no",
            "source",
            "status",
            "filename",
            "total_count",
            "duplicate_count",
            "message",
            "username",
            "api_caller",
            "created_at",
            "finished_at",
        )
    )
    data = [dict(r) for r in records]
    return SuccessExtra(data=data, total=total, page=body.page, page_size=body.page_size)


@router.get("/simdup/record/{record_id}", summary="查看某次验证记录的详情")
async def record_detail(record_id: int):
    record = await SimDupVerifyRecord.get_or_none(id=record_id)
    if not record:
        return Fail(code=404, msg="验证记录不存在")
    d = await record.to_dict()
    d["can_download"] = bool(d.get("result_file_path"))
    return Success(data=d)


@router.get("/simdup/record/{record_id}/results", summary="查看某次验证记录命中的重复卡号")
async def record_results(record_id: int, page: int = Query(1, ge=1), page_size: int = Query(500, ge=1, le=5000)):
    total = await SimDupVerifyResult.filter(record_id=record_id).count()
    rows = [
        dict(r)
        for r in await SimDupVerifyResult.filter(record_id=record_id)
        .order_by("sim_number")
        .offset((page - 1) * page_size)
        .limit(page_size)
        .values("id", "sim_number")
    ]
    return SuccessExtra(data=rows, total=total, page=page, page_size=page_size)


# ────────────────────────── 对外API：直接调用验证重复编码 ──────────────────────────
@router.post("/simdup/api/verify", summary="对外API-验证SimNumber是否重复入库")
async def api_verify(req: Request, body: SimDupCodesIn):
    """对外接口：传入SimNumber列表，返回其中已在系统存在的重复卡号。
    鉴权：复用平台JWT token（Header: token）；记录验证日志与审计日志。"""
    user_id, username = await _get_user(req)
    try:
        result = await simdup_service.verify_codes(
            codes=body.sim_numbers,
            user_id=user_id,
            username=username,
            api_caller=body.caller,
        )
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        logger.error(f"对外API验证失败: {e}", exc_info=True)
        return Fail(code=500, msg=f"验证失败: {e!s}")

    await _audit(
        user_id,
        username,
        f"SIM重复入库验证（对外API caller={body.caller or 'unknown'}）: {result['message']}",
        "/api/v1/wms/simdup/api/verify",
        {"caller": body.caller, "count": len(body.sim_numbers)},
        {"batch_no": result["batch_no"], "duplicate_count": result["duplicate_count"]},
        status=200 if result["success"] else 500,
    )
    return Success(msg=result["message"], data=result)
