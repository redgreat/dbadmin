from datetime import datetime

from tortoise import fields
from tortoise.models import Model


# 定义任务类型常量
class TaskType:
    SHELL = "shell"
    PYTHON = "python"
    HTTP = "http"


# 定义任务执行状态常量
class TaskStatus:
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RUNNING = "running"


class Task(Model):
    """定时任务模型"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="任务名称")
    type = fields.CharField(max_length=20, description="任务类型：shell, python, http")
    cron = fields.CharField(max_length=100, description="Cron表达式")
    command = fields.TextField(description="执行命令或函数")
    work_dir = fields.CharField(max_length=255, description="执行目录", default="/home/app")
    run_user = fields.CharField(max_length=50, description="执行用户", default="appuser")
    env_vars = fields.TextField(description="环境变量，格式：KEY=VALUE，每行一个", null=True)
    args = fields.TextField(description="参数，JSON格式", null=True)
    timeout = fields.IntField(description="超时时间(秒)，0表示不限制", default=3600)
    max_retries = fields.IntField(description="最大重试次数", default=3)
    status = fields.BooleanField(description="任务状态：true启用，false禁用", default=True)
    remark = fields.TextField(description="备注", null=True)
    last_run_time = fields.DatetimeField(description="上次执行时间", null=True)
    next_run_time = fields.DatetimeField(description="下次执行时间", null=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "task"
        description = "定时任务表"

    def __str__(self):
        return f"{self.name} ({self.id})"


class TaskLog(Model):
    """任务执行日志模型"""

    id = fields.IntField(pk=True)
    task = fields.ForeignKeyField("models.Task", related_name="logs", on_delete=fields.CASCADE, description="关联的任务")
    status = fields.CharField(max_length=20, description="执行状态：success, failed, timeout, running")
    start_time = fields.DatetimeField(description="开始时间")
    end_time = fields.DatetimeField(description="结束时间", null=True)
    duration = fields.IntField(description="执行时长(秒)", null=True)
    output = fields.TextField(description="执行输出", null=True)
    error = fields.TextField(description="错误信息", null=True)
    retry_count = fields.IntField(description="重试次数", default=0)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "task_log"
        description = "任务执行日志表"

    def __str__(self):
        return f"TaskLog {self.id} for Task {self.task_id}"
