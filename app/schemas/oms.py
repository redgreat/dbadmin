from datetime import datetime

from pydantic import BaseModel, Field


class UpdateAuditTimeBatchIn(BaseModel):
    """批量更新审核时间入参"""
    order_nos: list[str] = Field(default_factory=list, description="订单编码或订单Id列表，逗号分隔后端已拆分")
    audit_time: datetime = Field(..., description="目标审核时间")
    remark: str = Field(default="", description="运维备注（非必填，用于审计日志）")


class DeleteBatchIn(BaseModel):
    """批量删除入参"""
    order_nos: list[str] = Field(default_factory=list, description="订单编码或订单Id列表，逗号分隔后端已拆分")
    operator_id: str = Field(default="", description="删除人Id（GUID格式，逻辑删除时需要）")
    remark: str = Field(default="", description="运维备注（非必填，用于审计日志）")


class OrderQueryIn(BaseModel):
    """查询订单状态入参"""
    order_nos: list[str] = Field(default_factory=list, description="订单编码或订单Id列表")


class RestoreLogicalIn(BaseModel):
    """逻辑删除恢复入参"""
    order_no: str = Field(..., description="订单编码或订单Id")
    operator_id: str = Field(..., description="删除人Id（GUID格式）")
    remark: str = Field(default="", description="运维备注（非必填，用于审计日志）")


class GfsQueryIn(BaseModel):
    """GFS订单状态查询入参"""
    order_nos: list[str] = Field(default_factory=list, description="订单编码列表")
    order_ids: list[str] = Field(default_factory=list, description="订单Id列表")


class GfsDeleteIn(BaseModel):
    """GFS订单删除入参"""
    order_id: str = Field(..., description="订单Id")


class CheckRecordDeleteIn(BaseModel):
    """校验记录删除入参"""
    order_id: str = Field(..., description="订单Id")


class ReturnOriginQueryIn(BaseModel):
    """退货单原单查询入参"""
    return_order_no: str = Field(..., description="退货单Id或编码")


class ReturnOriginUpdateIn(BaseModel):
    """退货单原单更新入参"""
    return_order_no: str = Field(..., description="退货单Id或编码")
    new_origin_order_no: str = Field(..., description="变更原订单Id或订单编码")
    updated_by_id: str = Field(..., description="数据更新人Id")
    remark: str = Field(default="", description="运维备注（非必填，用于审计日志）")
