from pydantic import BaseModel, Field


class WorkorderQueryIn(BaseModel):
    """工单查询入参"""
    keyword: str = Field(..., description="工单AppCode或Id")


class FixDetailIdIn(BaseModel):
    """修复明细Id入参"""
    workorder_id: str = Field(..., description="工单Id")
    remark: str = Field(default="", description="原因备注")


class RegenerateOrderIn(BaseModel):
    """重新生成订单Id入参"""
    workorder_id: str = Field(..., description="工单Id")
    remark: str = Field(default="", description="原因备注")


class WorkorderManageQueryIn(BaseModel):
    """工单管理-查询状态入参"""
    workorder_nos: list[str] = Field(default_factory=list, description="工单编码或Id列表")


class WorkorderDeleteIn(BaseModel):
    """工单逻辑删除入参"""
    workorder_nos: list[str] = Field(default_factory=list, description="工单编码或Id列表")
    operator_id: str = Field(..., description="操作人Id（GUID格式）")
    remark: str = Field(default="", description="运维备注")


class WorkorderRestoreIn(BaseModel):
    """工单逻辑删除恢复入参"""
    workorder_no: str = Field(..., description="工单编码或Id")
    operator_id: str = Field(..., description="操作人Id（GUID格式）")
    remark: str = Field(default="", description="运维备注")


class WorkorderCloseIn(BaseModel):
    """工单关闭入参"""
    workorder_nos: list[str] = Field(default_factory=list, description="工单编码或Id列表")
    operator_id: str = Field(..., description="操作人Id（GUID格式）")
    remark: str = Field(default="", description="运维备注")
