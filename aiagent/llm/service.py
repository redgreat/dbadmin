import logging
import time

from openai import APIConnectionError, APITimeoutError, AuthenticationError

from aiagent.llm.client import LLMClient
from aiagent.models.ai_llm_call_log import AiLlmCallLog
from aiagent.models.ai_token import AiToken

logger = logging.getLogger(__name__)

async def llm_ask_stream(
    system_prompt: str,
    user_message: str,
    session_id: str,
    available_tools: list = None,
    ai_token: AiToken | None = None
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
    except APITimeoutError as e:
        logger.error(f"LLM 调用超时: provider={client.provider}, model={client.model_name}, base_url={client.base_url}, error={e}")
        await AiLlmCallLog.create(
            llm_config_id=client.config_id,
            provider=client.provider,
            model_name=client.model_name,
            ai_token_id=ai_token.id if ai_token else None,
            call_source="chat",
            session_id=session_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status="error",
            error_message=f"LLM 调用超时: {e!s}"
        )
        yield {"type": "text", "delta": "\n\n[生成失败：大模型调用超时，请检查服务端日志或稍后重试]"}
    except APIConnectionError as e:
        logger.error(f"LLM 连接失败: provider={client.provider}, model={client.model_name}, base_url={client.base_url}, error={e}")
        await AiLlmCallLog.create(
            llm_config_id=client.config_id,
            provider=client.provider,
            model_name=client.model_name,
            ai_token_id=ai_token.id if ai_token else None,
            call_source="chat",
            session_id=session_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status="error",
            error_message=f"LLM 连接失败: {e!s}"
        )
        yield {"type": "text", "delta": f"\n\n[生成失败：无法连接到大模型服务，请检查 base_url={client.base_url} 是否可达]"}
    except AuthenticationError as e:
        logger.error(f"LLM 鉴权失败: provider={client.provider}, model={client.model_name}, error={e}")
        await AiLlmCallLog.create(
            llm_config_id=client.config_id,
            provider=client.provider,
            model_name=client.model_name,
            ai_token_id=ai_token.id if ai_token else None,
            call_source="chat",
            session_id=session_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status="error",
            error_message=f"LLM 鉴权失败: {e!s}"
        )
        yield {"type": "text", "delta": "\n\n[生成失败：API Key 无效或未配置，请检查大模型配置]"}
    except Exception as e:
        logger.error(f"LLM Stream Error: provider={client.provider}, model={client.model_name}, base_url={client.base_url}, error={e}", exc_info=True)
        await AiLlmCallLog.create(
            llm_config_id=client.config_id,
            provider=client.provider,
            model_name=client.model_name,
            ai_token_id=ai_token.id if ai_token else None,
            call_source="chat",
            session_id=session_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status="error",
            error_message=str(e)
        )
        yield {"type": "text", "delta": f"\n\n[生成失败：{e!s}]"}
