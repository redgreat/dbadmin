from openai import AsyncOpenAI
from openai import APITimeoutError, APIConnectionError
from aiagent.models.ai_llm_config import AiLlmConfig

class LLMClient:
    """异步大模型调用客户端，支持 OpenAI 兼容接口"""

    _instance = None
    _config_id = None

    @classmethod
    async def get(cls) -> "LLMClient":
        active = await AiLlmConfig.filter(is_active=True).first()
        if not active:
            raise RuntimeError("大模型未配置：请在「大模型配置」菜单中激活一个提供商")
        # 配置变化时重建客户端
        if cls._instance is None or cls._config_id != active.id:
            cls._instance = cls(active)
            cls._config_id = active.id
        return cls._instance

    def __init__(self, config: AiLlmConfig):
        # TODO: 接入系统后补充正确的 AES 加解密逻辑，当前直接使用明文
        api_key = config.api_key_enc if config.api_key_enc else "no-key"
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
            timeout=60.0,
            max_retries=2,
        )
        self.model_name = config.model_name
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.provider = config.provider
        self.config_id = config.id

    async def ask(self, system_prompt: str, user_prompt: str) -> dict:
        """单次调用，返回 {content, usage}"""
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = response.usage
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            }
        }

    async def ask_stream(self, system_prompt: str, messages: list):
        """流式调用，yield 每个 chunk"""
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=self.temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield {"type": "text", "delta": delta.content}


async def reset_llm_client():
    """大模型配置切换后调用此函数清除缓存"""
    LLMClient._instance = None
    LLMClient._config_id = None
