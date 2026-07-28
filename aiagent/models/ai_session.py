from tortoise import fields
from tortoise.models import Model


class AiSession(Model):
    """对话会话"""
    id = fields.BigIntField(pk=True)
    session_id = fields.CharField(max_length=64, unique=True, index=True)
    user = fields.ForeignKeyField("models.User", null=True, on_delete=fields.SET_NULL, related_name="ai_sessions")
    ai_token = fields.ForeignKeyField("models.AiToken", null=True, on_delete=fields.SET_NULL,
                                       description="外部 Agent 使用的 Token")
    title = fields.CharField(max_length=200, null=True, description="会话标题（首条消息摘要）")
    summary = fields.TextField(null=True, description="LLM 自动生成的阶段摘要")
    total_turns = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "ai_session"
