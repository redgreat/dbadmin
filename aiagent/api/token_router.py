from fastapi import APIRouter, Query
from aiagent.models.ai_token import AiToken
from pydantic import BaseModel
from app.schemas.base import Success, SuccessExtra

token_router = APIRouter()

class TokenCreate(BaseModel):
    name: str
    description: str = ""
    allow_write: bool = False
    
@token_router.get("/")
async def list_tokens(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1)):
    total = await AiToken.all().count()
    tokens = await AiToken.all().order_by("-id").offset((page - 1) * page_size).limit(page_size).values()
    return SuccessExtra(data=list(tokens), total=total, page=page, page_size=page_size)

@token_router.post("/")
async def create_token(req: TokenCreate):
    import secrets
    token_val = "sk-" + secrets.token_hex(16)
    obj = await AiToken.create(name=req.name, token=token_val, description=req.description, allow_write=req.allow_write)
    return Success(data={"id": obj.id, "token": token_val})
