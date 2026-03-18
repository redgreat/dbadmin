from tortoise import fields

from .base import BaseModel, TimestampMixin


class Dict(BaseModel, TimestampMixin):
    """字典管理模型"""
    name = fields.CharField(max_length=100, description="字典名称", index=True)
    code = fields.CharField(max_length=100, unique=True, description="字典编码", index=True)
    parent_code = fields.CharField(max_length=100, null=True, description="父级编码", index=True)
    deleted = fields.BooleanField(default=False, description="逻辑删除标记", index=True)
    deleted_at = fields.DatetimeField(null=True, description="删除时间")

    class Meta:
        table = "sys_dict"

    def __str__(self):
        return f"<Dict {self.name}>"
