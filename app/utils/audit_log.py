import json
import re
from typing import Any

from fastapi import Request
from starlette.responses import Response

from app.models.admin import AuditLog

MAX_AUDIT_BODY_LEN = 32 * 1024

# 文件上传类接口：不记录请求体
SKIP_REQUEST_BODY_PATH_RE = re.compile(
    r"(/upload\b|/excelimp/|/imptask/create|/sim/simiccid/)",
    re.I,
)

# 文件/SQL 下载或大段 SQL 返回：不记录响应体
SKIP_RESPONSE_BODY_PATH_RE = re.compile(
    r"(/download|public-download|download-direct|/excelimp/generate)",
    re.I,
)

BINARY_RESPONSE_CONTENT_TYPE_RE = re.compile(
    r"(application/octet-stream|spreadsheetml|ms-excel|vnd\.|application/zip|/sql\b)",
    re.I,
)


def should_skip_request_body(request: Request) -> bool:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        return True
    return bool(SKIP_REQUEST_BODY_PATH_RE.search(request.url.path))


def should_skip_response_body(request: Request, response: Response) -> bool:
    if SKIP_RESPONSE_BODY_PATH_RE.search(request.url.path):
        return True
    content_disposition = response.headers.get("content-disposition", "")
    if "attachment" in content_disposition.lower():
        return True
    content_type = response.headers.get("content-type", "")
    if content_type and BINARY_RESPONSE_CONTENT_TYPE_RE.search(content_type):
        return True
    return False


def serialize_for_audit(data: Any, max_len: int = MAX_AUDIT_BODY_LEN) -> str:
    """将对象序列化为审计日志可存储的字符串，超长则截断。"""
    if data is None:
        return ""
    if isinstance(data, str):
        text = data
    else:
        try:
            text = json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(data)
    if len(text) > max_len:
        return text[:max_len] + f"...(truncated, total {len(text)} chars)"
    return text


def truncate_body_text(text: str) -> str:
    if len(text) <= MAX_AUDIT_BODY_LEN:
        return text
    return text[:MAX_AUDIT_BODY_LEN] + f"...(truncated, total {len(text)} chars)"


async def create_operation_audit_log(
    *,
    user_id: int,
    username: str,
    module: str,
    summary: str,
    method: str,
    path: str,
    status: int,
    request_body: Any = None,
    response_body: Any = None,
    response_time: int = 0,
    skip_request_body: bool = False,
    skip_response_body: bool = False,
) -> None:
    """运维类接口的手动审计日志（批量操作按条记录时使用）。"""
    req_text = "" if skip_request_body else serialize_for_audit(request_body)
    resp_text = "" if skip_response_body else serialize_for_audit(response_body)
    await AuditLog.create(
        user_id=user_id,
        username=username,
        module=module,
        summary=summary,
        method=method,
        path=path,
        status=status,
        request_body=req_text,
        response_body=resp_text,
        response_time=response_time,
    )
