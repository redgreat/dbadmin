from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder

from aiagent.models.ai_tool_call_log import AiToolCallLog
from app.schemas.base import SuccessExtra

call_log_router = APIRouter()

@call_log_router.get("/")
async def list_logs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1)):
    total = await AiToolCallLog.all().count()
    logs = await AiToolCallLog.all().order_by("-id").offset((page - 1) * page_size).limit(page_size).values()
    return SuccessExtra(data=jsonable_encoder(list(logs)), total=total, page=page, page_size=page_size)

