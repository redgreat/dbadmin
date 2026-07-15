from fastapi import APIRouter

llm_config_router = APIRouter()

@llm_config_router.get("/")
async def list_configs():
    return {"success": True, "data": []}
