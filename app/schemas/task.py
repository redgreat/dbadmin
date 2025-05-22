from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# 任务基础模型
class TaskBase(BaseModel):
    name: str = Field(..., description="任务名称")
    type: str = Field(..., description="任务类型：shell, python, http")
    cron: str = Field(..., description="Cron表达式")
    command: str = Field(..., description="执行命令或函数")
    work_dir: Optional[str] = Field("/home/app", description="执行目录")
    run_user: Optional[str] = Field("appuser", description="执行用户")
    env_vars: Optional[str] = Field(None, description="环境变量，格式：KEY=VALUE，每行一个")
    args: Optional[str] = Field(None, description="参数，JSON格式")
    timeout: Optional[int] = Field(3600, description="超时时间(秒)，0表示不限制")
    max_retries: Optional[int] = Field(3, description="最大重试次数")
    status: Optional[bool] = Field(True, description="任务状态：true启用，false禁用")
    remark: Optional[str] = Field(None, description="备注")


# 创建任务请求模型
class TaskCreate(TaskBase):
    pass


# 更新任务请求模型
class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, description="任务名称")
    type: Optional[str] = Field(None, description="任务类型：shell, python, http")
    cron: Optional[str] = Field(None, description="Cron表达式")
    command: Optional[str] = Field(None, description="执行命令或函数")
    work_dir: Optional[str] = Field(None, description="执行目录")
    run_user: Optional[str] = Field(None, description="执行用户")
    env_vars: Optional[str] = Field(None, description="环境变量，格式：KEY=VALUE，每行一个")
    args: Optional[str] = Field(None, description="参数，JSON格式")
    timeout: Optional[int] = Field(None, description="超时时间(秒)，0表示不限制")
    max_retries: Optional[int] = Field(None, description="最大重试次数")
    status: Optional[bool] = Field(None, description="任务状态：true启用，false禁用")
    remark: Optional[str] = Field(None, description="备注")


# 数据库中的任务模型
class TaskInDB(TaskBase):
    id: int
    last_run_time: Optional[datetime] = None
    next_run_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 任务列表响应模型
class TaskList(BaseModel):
    items: List[TaskInDB]
    total: int


# 任务日志基础模型
class TaskLogBase(BaseModel):
    task_id: int = Field(..., description="任务ID")
    status: str = Field(..., description="执行状态：success, failed, timeout, running")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[int] = Field(None, description="执行时长(秒)")
    output: Optional[str] = Field(None, description="执行输出")
    error: Optional[str] = Field(None, description="错误信息")
    retry_count: Optional[int] = Field(0, description="重试次数")


# 创建任务日志请求模型
class TaskLogCreate(TaskLogBase):
    pass


# 数据库中的任务日志模型
class TaskLogInDB(TaskLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# 任务日志列表响应模型
class TaskLogList(BaseModel):
    items: List[TaskLogInDB]
    total: int


# 执行任务响应模型
class TaskExecuteResponse(BaseModel):
    success: bool
    message: str
    task_log_id: Optional[int] = None
