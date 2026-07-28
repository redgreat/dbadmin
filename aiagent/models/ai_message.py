from tortoise import fields
from tortoise.models import Model


class AiMessage(Model):
    """对话消息"""
    id = fields.BigIntField(pk=True)
    session = fields.ForeignKeyField("models.AiSession", related_name="messages")
    seq = fields.IntField(description="消息序号")
    role = fields.CharField(max_length=20, description="user/assistant/tool")
    content = fields.TextField()
    tool_name = fields.CharField(max_length=100, null=True)
    tool_input = fields.JSONField(null=True)
    tool_output = fields.JSONField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ai_message"
