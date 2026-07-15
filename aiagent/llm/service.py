import time
import logging
from typing import Optional
from aiagent.llm.client import LLMClient
from aiagent.models.ai_llm_call_log import AiLlmCallLog
from aiagent.models.ai_token import AiToken

logger = logging.getLogger(__name__)

async def llm_ask_stream(
    system_prompt: str,
    user_message: str,
    session_id: str,
    available_tools: list = None,
    ai_token: Optional[AiToken] = None
):
    """
    流式调用大模型
    这里组装 messages，并附加可用工具列表等信息到 system_prompt，然后调用客户端
    """
    client = await LLMClient.get()
    
    # 构建消息列表
    messages = [
        {"role": "user", "content": user_message}
    ]
    
    # TODO: 后续可以加入历史消息

    # 如果有工具，加到 system prompt 里
    if available_tools:
        system_prompt += "\n\n你可以使用的工具有：\n" + "\n".join([f"- {t}" for t in available_tools])
        
    start_time = time.time()
    
    try:
        async for chunk in client.ask_stream(system_prompt, messages):
            yield chunk
            
        duration_ms = int((time.time() - start_time) * 1000)
        # 流式调用暂无法直接获取 token usage，可做粗略计算或单独请求，这里简单记录
        await AiLlmCallLog.create(
            llm_config_id=client.config_id,
            provider=client.provider,
            model_name=client.model_name,
            ai_token_id=ai_token.id if ai_token else None,
            call_source="chat",
            session_id=session_id,
            duration_ms=duration_ms,
            status="success"
        )
    except Exception as e:
        logger.error(f"LLM Stream Error: {e}")
        duration_ms = int((time.time() - start_time) * 1000)
        await AiLlmCallLog.create(
            llm_config_id=client.config_id,
            provider=client.provider,
            model_name=client.model_name,
            ai_token_id=ai_token.id if ai_token else None,
            call_source="chat",
            session_id=session_id,
            duration_ms=duration_ms,
            status="error",
            error_message=str(e)
        )
        yield {"type": "text", "delta": f"\n\n[生成失败：{str(e)}]"}
