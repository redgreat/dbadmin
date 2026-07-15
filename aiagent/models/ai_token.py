from tortoise import fields
from tortoise.models import Model

class AiToken(Model):
    """MCP 访问 Token（供外部 Agent Client 调用）"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="Token 名称（如「Hermes Agent」）")
    token = fields.CharField(max_length=128, unique=True, description="Token 值（AK）")
    description = fields.TextField(null=True, description="用途描述")
    enabled = fields.BooleanField(default=True, description="是否启用")
    
    # 权限控制
    allow_write = fields.BooleanField(default=False, description="是否允许写操作（默认只读）")
    allow_tools = fields.JSONField(null=True, description="允许调用的工具名称列表，null=全部允许")
    
    # 配额控制
    daily_call_limit = fields.IntField(null=True, description="每日调用次数限制，null=不限")
    
    # 关联
    created_by = fields.ForeignKeyField("models.User", null=True, description="创建人", related_name="created_ai_tokens")
    created_at = fields.DatetimeField(auto_now_add=True)
    last_used_at = fields.DatetimeField(null=True, description="最后使用时间")

    class Meta:
        table = "ai_token"
