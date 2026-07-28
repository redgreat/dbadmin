from tortoise import fields
from tortoise.models import Model


class AiLlmConfig(Model):
    """大模型配置"""

    id = fields.IntField(pk=True)
    provider = fields.CharField(max_length=50, description="提供商：openai/claude/deepseek/ollama/zhipu")
    name = fields.CharField(max_length=100, description="配置名称（自定义，如「DeepSeek本地」）")
    base_url = fields.CharField(max_length=255, null=True, description="API Base URL")
    api_key_enc = fields.TextField(null=True, description="AES 加密后的 API Key")
    model_name = fields.CharField(max_length=100, description="模型名称（如 deepseek-chat）")
    is_active = fields.BooleanField(default=False, description="是否激活（全局仅一个）")
    max_tokens = fields.IntField(default=4096, description="最大输出 Token")
    temperature = fields.FloatField(default=0.2, description="采样温度")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "ai_llm_config"
