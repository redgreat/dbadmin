from tortoise import fields

from app.models.base import BaseModel, TimestampMixin


class ImpTask(BaseModel, TimestampMixin):
    """Excel导入任务模型"""

    # 任务基本信息
    task_name = fields.CharField(max_length=100, description="任务名称", index=True)
    filename = fields.CharField(max_length=255, description="原始文件名")
    file_path = fields.CharField(max_length=500, description="文件存储路径")
    file_size = fields.BigIntField(description="文件大小(字节)")

    # 数据库配置
    db_type = fields.CharField(max_length=20, description="数据库类型(mysql/postgresql)")

    # 任务状态
    status = fields.CharField(
        max_length=20,
        default="pending",
        description="任务状态(pending/processing/completed/failed)",
        index=True
    )
    progress = fields.IntField(default=0, description="进度百分比(0-100)")
    message = fields.CharField(max_length=500, null=True, description="进度消息")

    # 结果文件
    sql_file_path = fields.CharField(max_length=500, null=True, description="生成的SQL文件路径")
    sql_file_size = fields.BigIntField(null=True, description="SQL文件大小(字节)")

    # 错误信息
    error_message = fields.TextField(null=True, description="错误信息")

    # 时间信息
    started_at = fields.DatetimeField(null=True, description="开始处理时间", index=True)
    completed_at = fields.DatetimeField(null=True, description="完成时间", index=True)

    # 用户信息
    user_id = fields.BigIntField(null=True, description="创建用户ID", index=True)
    username = fields.CharField(max_length=50, null=True, description="创建用户名")

    class Meta:
        table = "imptask"
        # 添加索引以优化查询
        indexes = [
            ["status", "created_at"],
            ["user_id", "status"],
        ]
