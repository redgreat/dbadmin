from tortoise import fields

from .base import BaseModel, TimestampMixin


class AlertSender(BaseModel, TimestampMixin):
    sender_name = fields.CharField(max_length=64, unique=True, description="发送人名称", index=True)
    channel_type = fields.CharField(max_length=32, default="wechat_group", description="发送渠道类型", index=True)
    channel_target = fields.CharField(max_length=255, description="渠道目标（群ID/邮箱/webhook）")
    app_id = fields.CharField(max_length=128, null=True, description="企业微信AppID")
    app_key = fields.CharField(max_length=255, null=True, description="企业微信AppKey")
    is_enabled = fields.BooleanField(default=True, description="是否启用", index=True)
    remark = fields.CharField(max_length=255, null=True, description="备注")
    created_by = fields.BigIntField(null=True, description="创建人ID")
    updated_by = fields.BigIntField(null=True, description="更新人ID")

    class Meta:
        table = "alert_sender"


class AlertSendLog(BaseModel, TimestampMixin):
    sender = fields.ForeignKeyField(
        "models.AlertSender",
        related_name="send_logs",
        null=True,
        on_delete=fields.SET_NULL,
        description="发送人",
    )
    sender_name = fields.CharField(max_length=64, description="发送人名称快照", index=True)
    channel_type = fields.CharField(max_length=32, description="发送渠道类型", index=True)
    channel_target = fields.CharField(max_length=255, description="渠道目标快照", index=True)
    alert_text = fields.TextField(description="预警发送文本")
    send_status = fields.IntField(default=0, description="发送状态：1成功，0失败", index=True)
    response_text = fields.TextField(null=True, description="发送响应内容")
    sent_at = fields.DatetimeField(auto_now_add=True, description="发送时间", index=True)

    class Meta:
        table = "alert_send_log"
