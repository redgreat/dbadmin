from pydantic import BaseModel, Field


class WorkorderQueryIn(BaseModel):
    """工单查询入参"""
    keyword: str = Field(..., description="工单AppCode或Id")


class FixDetailIdIn(BaseModel):
    """修复明细Id入参"""
    workorder_id: str = Field(..., description="工单Id")


class RegenerateOrderIn(BaseModel):
    """重新生成订单Id入参"""
    workorder_id: str = Field(..., description="工单Id")
