from tortoise import fields
from tortoise.models import Model


class AiToolCallLog(Model):
    """MCP 工具调用日志"""

    id = fields.BigIntField(pk=True)
    timestamp = fields.DatetimeField(auto_now_add=True, index=True)

    # 调用来源
    ai_token = fields.ForeignKeyField("models.AiToken", null=True, on_delete=fields.SET_NULL, related_name="tool_call_logs")
    session_id = fields.CharField(max_length=64, null=True, index=True)
    caller_ip = fields.CharField(max_length=45, null=True)

    # 工具信息
    tool_name = fields.CharField(max_length=100, index=True)
    tool_input = fields.JSONField(null=True, description="工具入参")
    tool_output_summary = fields.TextField(null=True, description="返回结果摘要（前500字符）")

    duration_ms = fields.IntField(null=True)
    status = fields.CharField(max_length=20, index=True, description="success/error")
    error_message = fields.TextField(null=True)

    # 关联操作审计（写操作时填写）
    is_write_op = fields.BooleanField(default=False)
    oplog_id = fields.BigIntField(null=True, description="关联到现有 oplog 运维日志表的 ID")

    class Meta:
        table = "ai_tool_call_log"
