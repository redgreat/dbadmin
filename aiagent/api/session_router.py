from fastapi import APIRouter

from aiagent.models.ai_session import AiSession

session_router = APIRouter()

@session_router.get("/")
async def list_sessions():
    sessions = await AiSession.all().order_by("-updated_at").limit(50)
    return {"success": True, "data": [{"session_id": s.session_id, "title": s.title} for s in sessions]}
