from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


class DictCreate(BaseModel):
    """字典创建Schema"""
    name: str = Field(..., description="字典名称", max_length=100)
    parent_code: Optional[str] = Field(None, description="父级编码", max_length=100)


class DictUpdate(BaseModel):
    """字典更新Schema"""
    id: int = Field(..., description="字典ID")
    name: Optional[str] = Field(None, description="字典名称", max_length=100)


class DictResponse(BaseModel):
    """字典响应Schema"""
    id: int
    name: str
    code: str
    parent_code: Optional[str]
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_at: Optional[datetime]
    children: Optional[List["DictResponse"]] = None

    class Config:
        from_attributes = True


class DictOption(BaseModel):
    """字典选项Schema（用于下拉框）"""
    label: str
    value: str
    children: Optional[List["DictOption"]] = None
