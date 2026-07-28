from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# ==================== 报表配置相关 Schema ====================

class ReportConfigBase(BaseModel):
    """报表配置基础模式"""
    system_name: str = Field(..., description="系统名称")
    report_name: str = Field(..., description="报表名称")
    sql_statement: str = Field(..., description="SQL语句")
    db_connection_id: int = Field(..., description="数据库连接ID")


class ReportConfigCreate(ReportConfigBase):
    """创建报表配置请求模式"""


class ReportConfigUpdate(BaseModel):
    """更新报表配置请求模式"""
    id: int
    system_name: str | None = Field(None, description="系统名称")
    report_name: str | None = Field(None, description="报表名称")
    sql_statement: str | None = Field(None, description="SQL语句")
    db_connection_id: int | None = Field(None, description="数据库连接ID")


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

    model_config = ConfigDict(from_attributes=True)


class ReportConfigList(BaseModel):
    """报表配置列表响应模式"""
    items: list[ReportConfigInDB]
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
    completed_at: datetime | None
    status: str
    progress: int
    progress_text: str | None
    exported_rows: int
    error_message: str | None
    file_path: str | None
    execution_json: dict | None

    model_config = ConfigDict(from_attributes=True)


class ReportGenerationList(BaseModel):
    """报表生成记录列表响应模式"""
    items: list[ReportGenerationInDB]
    total: int


# ==================== 系统名称选项 Schema ====================

class SystemNameOption(BaseModel):
    """系统名称选项"""
    label: str = Field(..., description="显示名称")
    value: str = Field(..., description="值")


class SystemNameOptions(BaseModel):
    """系统名称选项列表"""
    options: list[SystemNameOption]
