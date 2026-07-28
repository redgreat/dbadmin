from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImpTaskCreate(BaseModel):
    """创建Excel导入任务"""
    task_name: str
    target_conn_id: int | None = None


class ImpTaskOut(BaseModel):
    """Excel导入任务输出"""
    id: int
    task_name: str
    filename: str
    file_size: int
    db_type: str
    target_conn_id: int | None = None
    target_conn_name: str | None = None
    temp_table_name: str | None = None
    status: str
    progress: int
    message: str | None = None
    sql_file_size: int | None = None
    execute_status: str | None = None
    execute_message: str | None = None
    executed_at: datetime | None = None
    executor_user_id: int | None = None
    executor_username: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    user_id: int | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ImpTaskList(BaseModel):
    """Excel导入任务列表"""
    items: list[ImpTaskOut]
    total: int
    page: int
    page_size: int
