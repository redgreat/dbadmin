from tortoise.models import Model
from tortoise import fields

from .base import BaseModel, TimestampMixin


class OpLog(BaseModel, TimestampMixin):
    """数据运维日志模型"""
    logger = fields.CharField(max_length=100, description="修改类型", index=True)
    chgmsg = fields.JSONField(description="运维内容")
    operater = fields.CharField(max_length=50, description="操作人", index=True)
    final_modify_time = fields.DatetimeField(description="最终修改时间")

    class Meta:
        table = "oplog"
        description = "数据运维日志"

    def __str__(self):
        return f"{self.logger} - {self.operater} ({self.id})"
