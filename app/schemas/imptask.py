from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ImpTaskCreate(BaseModel):
    """创建Excel导入任务"""
    task_name: str
    db_type: str


class ImpTaskOut(BaseModel):
    """Excel导入任务输出"""
    id: int
    task_name: str
    filename: str
    file_size: int
    db_type: str
    status: str
    progress: int
    message: Optional[str] = None
    sql_file_size: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    user_id: Optional[int] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


class ImpTaskList(BaseModel):
    """Excel导入任务列表"""
    items: list[ImpTaskOut]
    total: int
    page: int
    page_size: int
