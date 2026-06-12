from tortoise import fields

from .base import BaseModel, TimestampMixin


class PasswordHistory(BaseModel, TimestampMixin):
    password = fields.CharField(max_length=256, description="生成的密码")
    length = fields.IntField(description="密码长度")
    char_types = fields.JSONField(description="使用的字符类型", default=list)
    exclude_chars = fields.CharField(max_length=128, default="", description="排除字符")
    count = fields.IntField(default=1, description="批量数量")

    class Meta:
        table = "password_history"
        description = "密码生成历史"
