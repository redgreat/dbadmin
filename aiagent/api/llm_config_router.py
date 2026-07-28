
from fastapi import APIRouter, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from aiagent.models.ai_llm_config import AiLlmConfig
from app.schemas.base import Fail, Success, SuccessExtra

llm_config_router = APIRouter()

class LlmConfigCreate(BaseModel):
    provider: str
    name: str
    base_url: str | None = None
    api_key_enc: str | None = None
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.2
    is_active: bool = False

class LlmConfigUpdate(BaseModel):
    id: int
    provider: str | None = None
    name: str | None = None
    base_url: str | None = None
    api_key_enc: str | None = None
    model_name: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    is_active: bool | None = None

@llm_config_router.get("/")
async def list_configs(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1)):
    total = await AiLlmConfig.all().count()
    configs = await AiLlmConfig.all().order_by("-id").offset((page - 1) * page_size).limit(page_size).values()
    return SuccessExtra(data=jsonable_encoder(list(configs)), total=total, page=page, page_size=page_size)


@llm_config_router.post("/")
async def create_config(req: LlmConfigCreate):
    if req.is_active:
        await AiLlmConfig.filter(is_active=True).update(is_active=False)
    obj = await AiLlmConfig.create(**req.model_dump())
    return Success(data={"id": obj.id})

@llm_config_router.post("/update")
async def update_config(req: LlmConfigUpdate):
    obj = await AiLlmConfig.get_or_none(id=req.id)
    if not obj:
        return Fail(msg="配置不存在")
    if req.is_active:
        await AiLlmConfig.filter(is_active=True).update(is_active=False)

    update_data = req.model_dump(exclude_unset=True)
    update_data.pop('id', None)
    for k, v in update_data.items():
        setattr(obj, k, v)
    await obj.save()
    return Success()
