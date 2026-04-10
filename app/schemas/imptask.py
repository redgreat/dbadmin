from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ImpTaskCreate(BaseModel):
    """创建Excel导入任务"""
    task_name: str
    target_conn_id: Optional[int] = None


class ImpTaskOut(BaseModel):
    """Excel导入任务输出"""
    id: int
    task_name: str
    filename: str
    file_size: int
    db_type: str
    target_conn_id: Optional[int] = None
    target_conn_name: Optional[str] = None
    temp_table_name: Optional[str] = None
    status: str
    progress: int
    message: Optional[str] = None
    sql_file_size: Optional[int] = None
    execute_status: Optional[str] = None
    execute_message: Optional[str] = None
    executed_at: Optional[datetime] = None
    executor_user_id: Optional[int] = None
    executor_username: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    user_id: Optional[int] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ImpTaskList(BaseModel):
    """Excel导入任务列表"""
    items: list[ImpTaskOut]
    total: int
    page: int
    page_size: int
