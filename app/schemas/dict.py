from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DictCreate(BaseModel):
    """字典创建Schema"""
    name: str = Field(..., description="字典名称", max_length=100)
    parent_code: str | None = Field(None, description="父级编码", max_length=100)


class DictUpdate(BaseModel):
    """字典更新Schema"""
    id: int = Field(..., description="字典ID")
    name: str | None = Field(None, description="字典名称", max_length=100)


class DictResponse(BaseModel):
    """字典响应Schema"""
    id: int
    name: str
    code: str
    parent_code: str | None
    created_at: datetime
    updated_at: datetime
    deleted: bool
    deleted_at: datetime | None
    children: list["DictResponse"] | None = None

    model_config = ConfigDict(from_attributes=True)


class DictOption(BaseModel):
    """字典选项Schema（用于下拉框）"""
    label: str
    value: str
    children: list["DictOption"] | None = None
