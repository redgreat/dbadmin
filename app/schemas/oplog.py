from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class OpLogCreateRequest(BaseModel):
    """操作日志创建请求模型"""
    logger: str = Field(..., description="修改类型")
    chgmsg: Dict[str, Any] = Field(..., description="运维内容")
    operater: str = Field(..., description="操作人")
    final_modify_time: datetime = Field(..., description="最终修改时间")


class OpLogUpdateRequest(BaseModel):
    """操作日志更新请求模型"""
    logger: Optional[str] = Field(None, description="修改类型")
    chgmsg: Optional[Dict[str, Any]] = Field(None, description="运维内容")
    operater: Optional[str] = Field(None, description="操作人")
    final_modify_time: Optional[datetime] = Field(None, description="最终修改时间")


class OpLogQueryRequest(BaseModel):
    """操作日志查询请求模型"""
    logger: Optional[str] = Field(None, description="修改类型")
    operater: Optional[str] = Field(None, description="操作人")
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class OpLogResponse(BaseModel):
    """操作日志响应模型"""
    id: int = Field(..., description="日志ID")
    logger: str = Field(..., description="修改类型")
    chgmsg: Dict[str, Any] = Field(..., description="运维内容")
    operater: str = Field(..., description="操作人")
    final_modify_time: datetime = Field(..., description="最终修改时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class OpLogListResponse(BaseModel):
    """操作日志列表响应模型"""
    records: List[OpLogResponse] = Field(..., description="日志记录列表")
    pagination: Dict[str, Any] = Field(..., description="分页信息")