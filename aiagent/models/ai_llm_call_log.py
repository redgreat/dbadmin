from tortoise import fields
from tortoise.models import Model

class AiLlmCallLog(Model):
    """大模型调用日志（Token 消耗追踪）"""

    id = fields.BigIntField(pk=True)
    timestamp = fields.DatetimeField(auto_now_add=True, index=True)
    llm_config = fields.ForeignKeyField("models.AiLlmConfig", null=True, on_delete=fields.SET_NULL, related_name="call_logs")
    provider = fields.CharField(max_length=50, index=True)
    model_name = fields.CharField(max_length=100)
    
    # 调用来源
    ai_token = fields.ForeignKeyField("models.AiToken", null=True, on_delete=fields.SET_NULL,
                                       description="调用方 Token（若来自外部 MCP 调用）", related_name="llm_call_logs")
    call_source = fields.CharField(max_length=64, default="internal",
                                   description="调用来源: chat/tool/summarize/internal")
    session_id = fields.CharField(max_length=64, null=True, index=True)
    tool_name = fields.CharField(max_length=100, null=True, description="触发的工具名")
    
    # Token 消耗
    prompt_tokens = fields.IntField(default=0)
    completion_tokens = fields.IntField(default=0)
    total_tokens = fields.IntField(default=0, index=True)
    duration_ms = fields.IntField(null=True)
    
    status = fields.CharField(max_length=20, index=True, description="success/error")
    error_message = fields.TextField(null=True)

    class Meta:
        table = "ai_llm_call_log"
