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
    workorder_ids: list[str] = Field(default_factory=list, description="指定删除的工单Id列表（同一编码对应多条记录且不全部删除时必填）")
    delete_all: bool = Field(default=False, description="是否全部删除（同一编码对应多条记录时，确认全部删除传True）")


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
