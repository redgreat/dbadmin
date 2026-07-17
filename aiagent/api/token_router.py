from fastapi import APIRouter, Query
from aiagent.models.ai_token import AiToken
from pydantic import BaseModel
from app.schemas.base import Success, SuccessExtra, Fail
from fastapi.encoders import jsonable_encoder
from typing import Optional, List

token_router = APIRouter()

class TokenCreate(BaseModel):
    name: str
    description: str = ""
    allow_write: bool = False

class TokenUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    allow_write: Optional[bool] = None
    allow_tools: Optional[list] = None

class TokenDelete(BaseModel):
    id: int

@token_router.get("/")
async def list_tokens(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1)):
    total = await AiToken.all().count()
    tokens = await AiToken.all().order_by("-id").offset((page - 1) * page_size).limit(page_size).values()
    return SuccessExtra(data=jsonable_encoder(list(tokens)), total=total, page=page, page_size=page_size)


@token_router.post("/")
async def create_token(req: TokenCreate):
    import secrets
    token_val = "sk-" + secrets.token_hex(16)
    obj = await AiToken.create(name=req.name, token=token_val, description=req.description, allow_write=req.allow_write)
    return Success(data={"id": obj.id, "token": token_val})

@token_router.post("/update")
async def update_token(req: TokenUpdate):
    obj = await AiToken.get_or_none(id=req.id)
    if not obj:
        return Fail(msg="Token 不存在")
    
    update_data = req.model_dump(exclude_unset=True)
    update_data.pop('id', None)
    for k, v in update_data.items():
        setattr(obj, k, v)
    await obj.save()
    return Success(msg="更新成功")

@token_router.post("/delete")
async def delete_token(req: TokenDelete):
    obj = await AiToken.get_or_none(id=req.id)
    if not obj:
        return Fail(msg="Token 不存在")
    await obj.delete()
    return Success(msg="删除成功")

@token_router.get("/mcp_tools")
async def list_mcp_tools():
    from aiagent.tools.base import TOOL_REGISTRY
    tools = []
    for name, entry in TOOL_REGISTRY.items():
        tool_dict = entry["definition"].to_dict()
        tool_dict["is_write"] = entry.get("is_write", False)
        tools.append(tool_dict)
    return Success(data=tools)
