from fastapi import APIRouter
from aiagent.models.ai_token import AiToken
from pydantic import BaseModel

token_router = APIRouter()

class TokenCreate(BaseModel):
    name: str
    description: str = ""
    allow_write: bool = False
    
@token_router.post("/")
async def create_token(req: TokenCreate):
    import secrets
    token_val = "sk-" + secrets.token_hex(16)
    obj = await AiToken.create(name=req.name, token=token_val, description=req.description, allow_write=req.allow_write)
    return {"success": True, "data": {"id": obj.id, "token": token_val}}
