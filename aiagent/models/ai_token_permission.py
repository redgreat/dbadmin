from tortoise import fields
from tortoise.models import Model


class AiTokenPermission(Model):
    """Token 权限配置表"""
    id = fields.IntField(pk=True)
    ai_token = fields.ForeignKeyField("models.AiToken", related_name="permissions", on_delete=fields.CASCADE)
    permission_code = fields.CharField(max_length=100, description="权限代码/工具名称")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ai_token_permission"
