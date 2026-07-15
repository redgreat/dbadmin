from fastapi import APIRouter
from aiagent.api.token_router import token_router
from aiagent.api.llm_config_router import llm_config_router
from aiagent.api.chat_router import chat_router
from aiagent.api.session_router import session_router
from aiagent.api.call_log_router import call_log_router
from aiagent.api.approval_router import approval_router

ai_router = APIRouter()

ai_router.include_router(token_router, prefix="/token", tags=["AI Token"])
ai_router.include_router(llm_config_router, prefix="/llm-config", tags=["AI LLM Config"])
ai_router.include_router(chat_router, prefix="/chat", tags=["AI Chat"])
ai_router.include_router(session_router, prefix="/session", tags=["AI Session"])
ai_router.include_router(call_log_router, prefix="/call-log", tags=["AI Call Log"])
ai_router.include_router(approval_router, prefix="/approval", tags=["AI Approval"])
