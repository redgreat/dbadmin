from tortoise import fields

from .base import BaseModel, TimestampMixin


class TaskRunStatus:
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"


class ReportSendTask(BaseModel, TimestampMixin):
    task_name = fields.CharField(max_length=100, description="任务名称", index=True)
    report_config = fields.ForeignKeyField(
        "models.ReportConfig",
        related_name="report_send_tasks",
        on_delete=fields.CASCADE,
        description="报表配置",
    )
    sender = fields.ForeignKeyField(
        "models.AlertSender",
        related_name="report_send_tasks",
        on_delete=fields.SET_NULL,
        null=True,
        description="发送人",
    )
    cron = fields.CharField(max_length=100, description="Cron表达式")
    message_template = fields.TextField(null=True, description="消息模板")
    send_attachment = fields.BooleanField(default=True, description="是否发送附件")
    status = fields.BooleanField(default=True, description="任务状态：true启用，false禁用", index=True)
    last_run_time = fields.DatetimeField(null=True, description="上次执行时间", index=True)
    next_run_time = fields.DatetimeField(null=True, description="下次执行时间", index=True)
    created_by = fields.BigIntField(null=True, description="创建人ID")
    updated_by = fields.BigIntField(null=True, description="更新人ID")
    remark = fields.CharField(max_length=200, null=True, description="备注")

    class Meta:
        table = "report_send_task"


class SqlAlertTask(BaseModel, TimestampMixin):
    task_name = fields.CharField(max_length=100, description="任务名称", index=True)
    db_connection = fields.ForeignKeyField(
        "models.DBConnection",
        related_name="sql_alert_tasks",
        on_delete=fields.CASCADE,
        description="数据库连接",
    )
    sender = fields.ForeignKeyField(
        "models.AlertSender",
        related_name="sql_alert_tasks",
        on_delete=fields.SET_NULL,
        null=True,
        description="发送人",
    )
    cron = fields.CharField(max_length=100, description="Cron表达式")
    sql_statement = fields.TextField(description="SQL语句")
    message_template = fields.TextField(description="消息模板")
    template_columns = fields.CharField(max_length=500, null=True, description="模板列，逗号分隔")
    total_placeholder = fields.CharField(max_length=50, default="{{total}}", description="总数占位符")
    send_detail_excel = fields.BooleanField(default=True, description="是否发送明细Excel")
    status = fields.BooleanField(default=True, description="任务状态：true启用，false禁用", index=True)
    last_run_time = fields.DatetimeField(null=True, description="上次执行时间", index=True)
    next_run_time = fields.DatetimeField(null=True, description="下次执行时间", index=True)
    created_by = fields.BigIntField(null=True, description="创建人ID")
    updated_by = fields.BigIntField(null=True, description="更新人ID")
    remark = fields.CharField(max_length=200, null=True, description="备注")

    class Meta:
        table = "sql_alert_task"


class NotifyTaskRunLog(BaseModel, TimestampMixin):
    task_type = fields.CharField(max_length=30, description="任务类型：report_send/sql_alert", index=True)
    task_ref_id = fields.BigIntField(description="任务ID", index=True)
    status = fields.CharField(max_length=20, description="执行状态", index=True)
    start_time = fields.DatetimeField(description="开始时间", index=True)
    end_time = fields.DatetimeField(null=True, description="结束时间")
    duration = fields.IntField(null=True, description="执行时长（秒）")
    output = fields.TextField(null=True, description="执行输出")
    error = fields.TextField(null=True, description="错误信息")
    result_json = fields.JSONField(null=True, description="执行结果JSON")

    class Meta:
        table = "notify_task_run_log"
