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
    workorder_ids: list[str] = Field(
        default_factory=list, description="指定删除的工单Id列表（同一编码对应多条记录且不全部删除时必填）"
    )
    delete_all: bool = Field(
        default=False, description="是否全部删除（同一编码对应多条记录时，确认全部删除传True）"
    )


class WorkorderRestoreIn(BaseModel):
    """工单逻辑删除恢复入参"""

    workorder_no: str = Field(..., description="工单编码或Id")
    operator_id: str = Field(..., description="操作人Id（GUID格式）")
    remark: str = Field(default="", description="运维备注")
    workorder_ids: list[str] = Field(
        default_factory=list, description="指定恢复的工单Id列表（同一编码对应多条已删除记录且不全部恢复时必填）"
    )
    restore_all: bool = Field(
        default=False, description="是否全部恢复（同一编码对应多条已删除记录时，确认全部恢复传True）"
    )


class WorkorderCloseIn(BaseModel):
    """工单关闭入参"""

    workorder_nos: list[str] = Field(default_factory=list, description="工单编码或Id列表")
    operator_id: str = Field(..., description="操作人Id（GUID格式）")
    remark: str = Field(default="", description="运维备注")
    workorder_ids: list[str] = Field(
        default_factory=list, description="指定关闭的工单Id列表（同一编码对应多条记录且不全部关闭时必填）"
    )
    close_all: bool = Field(
        default=False, description="是否全部关闭（同一编码对应多条记录时，确认全部关闭传True）"
    )


class WorkorderCreateTypeQueryIn(BaseModel):
    """查询工单CreateType入参"""

    workorder_nos: list[str] = Field(default_factory=list, description="工单Id或申请编码列表")


class WorkorderCreateTypeUpdateIn(BaseModel):
    """修改工单CreateType入参"""

    workorder_no: str = Field(..., description="工单Id或申请编码")
    create_type: int = Field(..., description="单据来源类型值")
    operator_id: str = Field(default="", description="操作人Id")
    remark: str = Field(default="", description="运维备注")


class ResourceQueryIn(BaseModel):
    """附件管理-查询入参"""

    keyword: str = Field(default="", description="工单编码或Id（非必填）")
    source_type: int | None = Field(default=None, description="附件类型（SourceType枚举值）")
    deleted_by_id: str = Field(
        default="", description="删除人用户中心Id（非必填，不填则查询所有删除人下的附件）"
    )
    include_deleted: bool = Field(default=False, description="是否包含已删除附件")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数")


class ResourceDeleteIn(BaseModel):
    """附件管理-逻辑删除入参"""

    resource_ids: list[str] = Field(..., min_length=1, description="附件Id列表")
    operator_id: str = Field(..., description="操作人Id（GUID格式，写入删除人）")
    remark: str = Field(default="", description="原因备注（非必填）")


class ResourceRestoreIn(BaseModel):
    """附件管理-恢复入参"""

    resource_ids: list[str] = Field(..., min_length=1, description="附件Id列表")
    operator_id: str = Field(
        default="", description="操作人Id（GUID格式，非必填；填写后仅恢复该删除人删除的附件）"
    )
    remark: str = Field(default="", description="原因备注（非必填）")
