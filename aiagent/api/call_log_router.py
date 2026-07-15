from fastapi import APIRouter

call_log_router = APIRouter()

@call_log_router.get("/")
async def list_logs():
    return {"success": True, "data": []}
