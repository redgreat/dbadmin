from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UpdateAuditTimeBatchIn(BaseModel):
    """批量更新审核时间入参"""
    order_nos: List[str] = Field(default_factory=list, description="订单编码或订单Id列表，逗号分隔后端已拆分")
    audit_time: datetime = Field(..., description="目标审核时间")
    remark: str = Field(default="", description="运维备注（非必填，用于审计日志）")


class DeleteBatchIn(BaseModel):
    """批量删除入参"""
    order_nos: List[str] = Field(default_factory=list, description="订单编码或订单Id列表，逗号分隔后端已拆分")
    operator_id: str = Field(default="", description="删除人Id（GUID格式，逻辑删除时需要）")
    remark: str = Field(default="", description="运维备注（非必填，用于审计日志）")


class OrderQueryIn(BaseModel):
    """查询订单状态入参"""
    order_nos: List[str] = Field(default_factory=list, description="订单编码或订单Id列表")


class RestoreLogicalIn(BaseModel):
    """逻辑删除恢复入参"""
    order_no: str = Field(..., description="订单编码或订单Id")
    operator_id: str = Field(..., description="删除人Id（GUID格式）")
    remark: str = Field(default="", description="运维备注（非必填，用于审计日志）")
