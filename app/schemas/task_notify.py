from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class ReportSendTaskCreate(BaseModel):
    task_name: str = Field(..., description="任务名称", max_length=100)
    report_config_id: int = Field(..., description="报表配置ID")
    sender_id: int = Field(..., description="发送人ID")
    cron: str = Field(..., description="Cron表达式", max_length=100)
    message_template: Optional[str] = Field(None, description="消息模板")
    status: bool = Field(default=True, description="状态")
    remark: Optional[str] = Field(None, description="备注", max_length=200)


class ReportSendTaskUpdate(BaseModel):
    id: int = Field(..., description="任务ID")
    task_name: Optional[str] = Field(None, description="任务名称", max_length=100)
    report_config_id: Optional[int] = Field(None, description="报表配置ID")
    sender_id: Optional[int] = Field(None, description="发送人ID")
    cron: Optional[str] = Field(None, description="Cron表达式", max_length=100)
    message_template: Optional[str] = Field(None, description="消息模板")
    status: Optional[bool] = Field(None, description="状态")
    remark: Optional[str] = Field(None, description="备注", max_length=200)


class SqlAlertTaskCreate(BaseModel):
    task_name: str = Field(..., description="任务名称", max_length=100)
    db_connection_id: int = Field(..., description="数据库连接ID")
    sender_id: int = Field(..., description="发送人ID")
    cron: str = Field(..., description="Cron表达式", max_length=100)
    sql_statement: str = Field(..., description="SQL语句")
    message_template: str = Field(..., description="消息模板")
    send_detail_excel: bool = Field(default=True, description="是否发送明细Excel")
    status: bool = Field(default=True, description="状态")
    remark: Optional[str] = Field(None, description="备注", max_length=200)


class SqlAlertTaskUpdate(BaseModel):
    id: int = Field(..., description="任务ID")
    task_name: Optional[str] = Field(None, description="任务名称", max_length=100)
    db_connection_id: Optional[int] = Field(None, description="数据库连接ID")
    sender_id: Optional[int] = Field(None, description="发送人ID")
    cron: Optional[str] = Field(None, description="Cron表达式", max_length=100)
    sql_statement: Optional[str] = Field(None, description="SQL语句")
    message_template: Optional[str] = Field(None, description="消息模板")
    send_detail_excel: Optional[bool] = Field(None, description="是否发送明细Excel")
    status: Optional[bool] = Field(None, description="状态")
    remark: Optional[str] = Field(None, description="备注", max_length=200)


class NotifyTaskLogInDB(BaseModel):
    id: int
    task_type: str
    task_ref_id: int
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[int]
    output: Optional[str]
    error: Optional[str]
    result_json: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotifyTaskLogList(BaseModel):
    items: List[NotifyTaskLogInDB]
    total: int
