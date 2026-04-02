from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UpdateAuditTimeBatchIn(BaseModel):
    """批量更新审核时间入参"""
    order_nos: List[str] = Field(default_factory=list, description="订单编码列表，逗号分隔后端已拆分")
    audit_time: datetime = Field(..., description="目标审核时间")


class DeleteBatchIn(BaseModel):
    """批量删除入参"""
    order_nos: List[str] = Field(default_factory=list, description="订单编码列表，逗号分隔后端已拆分")


class RestoreLogicalIn(BaseModel):
    """逻辑删除恢复入参"""
    order_no: str = Field(..., description="订单编码")
    operator_id: str = Field(..., description="删除人Id（GUID格式）")
