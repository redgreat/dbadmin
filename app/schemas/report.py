from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ==================== 报表配置相关 Schema ====================

class ReportConfigBase(BaseModel):
    """报表配置基础模式"""
    system_name: str = Field(..., description="系统名称")
    report_name: str = Field(..., description="报表名称")
    sql_statement: str = Field(..., description="SQL语句")
    db_connection_id: int = Field(..., description="数据库连接ID")


class ReportConfigCreate(ReportConfigBase):
    """创建报表配置请求模式"""
    pass


class ReportConfigUpdate(BaseModel):
    """更新报表配置请求模式"""
    id: int
    system_name: Optional[str] = Field(None, description="系统名称")
    report_name: Optional[str] = Field(None, description="报表名称")
    sql_statement: Optional[str] = Field(None, description="SQL语句")
    db_connection_id: Optional[int] = Field(None, description="数据库连接ID")


class ReportConfigInDB(BaseModel):
    """数据库中的报表配置模式"""
    id: int
    system_name: str
    report_name: str
    sql_statement: str
    db_connection_id: int
    maintainer: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportConfigList(BaseModel):
    """报表配置列表响应模式"""
    items: List[ReportConfigInDB]
    total: int


# ==================== 报表生成相关 Schema ====================

class ReportGenerateRequest(BaseModel):
    """报表生成请求模式"""
    config_id: int = Field(..., description="报表配置ID")


class ReportGenerationInDB(BaseModel):
    """数据库中的报表生成记录模式"""
    id: int
    report_name: str
    report_config_id: int
    generator: str
    generated_at: datetime
    completed_at: Optional[datetime]
    status: str
    file_path: Optional[str]
    execution_json: Optional[dict]

    class Config:
        from_attributes = True


class ReportGenerationList(BaseModel):
    """报表生成记录列表响应模式"""
    items: List[ReportGenerationInDB]
    total: int


# ==================== 系统名称选项 Schema ====================

class SystemNameOption(BaseModel):
    """系统名称选项"""
    label: str = Field(..., description="显示名称")
    value: str = Field(..., description="值")


class SystemNameOptions(BaseModel):
    """系统名称选项列表"""
    options: List[SystemNameOption]
