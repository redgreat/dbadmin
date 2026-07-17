import json
import secrets
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from aiagent.llm.service import llm_ask_stream
from aiagent.models.ai_session import AiSession
from aiagent.models.ai_message import AiMessage

chat_router = APIRouter()

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

@chat_router.post("/")
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    if not session_id:
        session_id = "sess_" + secrets.token_hex(8)
        await AiSession.create(session_id=session_id, title=req.message[:50])
    
    # 记录用户消息
    sess_obj = await AiSession.filter(session_id=session_id).first()
    await AiMessage.create(session=sess_obj, role="user", content=req.message, seq=1)

    # 简单提取出所有工具名称，提供给 LLM
    from aiagent.tools.base import TOOL_REGISTRY
    available_tools = list(TOOL_REGISTRY.keys())

    system_prompt = "你是 dbadmin 智能运维助手。"

    async def event_generator():
        yield f"data: {json.dumps({'session_id': session_id})}\n\n"
        
        full_content = ""
        async for chunk in llm_ask_stream(system_prompt, req.message, session_id, available_tools):
            if chunk.get("type") == "text":
                text = chunk.get("delta", "")
                full_content += text
                yield f"data: {json.dumps({'text': text})}\n\n"
                
        # 保存助手消息
        await AiMessage.create(session=sess_obj, role="assistant", content=full_content, seq=2)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
