from typing import List

from pydantic import BaseModel, Field


class WmsDeleteBatchIn(BaseModel):
    """批量删除入参"""
    stock_ids: List[str] = Field(default_factory=list, description="单据Id列表，逗号分隔后端已拆分")
    operator_id: str = Field(..., description="操作人Id（GUID格式）")


class WmsRestoreLogicalIn(BaseModel):
    """逻辑删除恢复入参"""
    stock_id: str = Field(..., description="单据Id")
    operator_id: str = Field(..., description="删除人Id（GUID格式）")
