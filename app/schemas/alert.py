from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AlertChannelType(StrEnum):
    WECHAT_GROUP = "wechat_group"
    EMAIL = "email"
    WECHAT_APP = "wechat_app"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"


class AlertSenderCreate(BaseModel):
    sender_name: str = Field(..., description="发送人名称", max_length=64)
    channel_type: AlertChannelType = Field(default=AlertChannelType.WECHAT_GROUP, description="发送渠道类型")
    channel_target: str = Field(..., description="渠道目标（当前为企业微信群ID）", max_length=255)
    app_id: str | None = Field(None, description="企业微信AppID", max_length=128)
    app_key: str | None = Field(None, description="企业微信AppKey", max_length=255)
    is_enabled: bool = Field(default=True, description="是否启用")
    remark: str | None = Field(None, description="备注", max_length=255)


class AlertSenderUpdate(BaseModel):
    id: int = Field(..., description="发送人ID")
    sender_name: str | None = Field(None, description="发送人名称", max_length=64)
    channel_type: AlertChannelType | None = Field(None, description="发送渠道类型")
    channel_target: str | None = Field(None, description="渠道目标", max_length=255)
    app_id: str | None = Field(None, description="企业微信AppID", max_length=128)
    app_key: str | None = Field(None, description="企业微信AppKey", max_length=255)
    is_enabled: bool | None = Field(None, description="是否启用")
    remark: str | None = Field(None, description="备注", max_length=255)


class AlertLogCreate(BaseModel):
    sender_id: int | None = Field(None, description="发送人ID")
    sender_name: str = Field(..., description="发送人名称快照", max_length=64)
    channel_type: AlertChannelType = Field(default=AlertChannelType.WECHAT_GROUP, description="发送渠道类型")
    channel_target: str = Field(..., description="渠道目标快照", max_length=255)
    alert_text: str = Field(..., description="预警发送文本")
    send_status: int = Field(default=0, description="发送状态：1成功，0失败")
    response_text: str | None = Field(None, description="发送响应内容")
    sent_at: datetime | None = Field(None, description="发送时间")
