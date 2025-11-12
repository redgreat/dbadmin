from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class UpdateAuditTimeBatchIn(BaseModel):
    """批量更新审核时间入参"""
    order_ids: List[str] = Field(default_factory=list, description="订单Id列表，逗号分隔后端已拆分")
    audit_time: datetime = Field(..., description="目标审核时间")


class DeleteBatchIn(BaseModel):
    """批量删除入参"""
    order_ids: List[str] = Field(default_factory=list, description="订单Id列表，逗号分隔后端已拆分")
