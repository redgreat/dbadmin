from datetime import datetime
from tortoise import fields
from .base import BaseModel, TimestampMixin


class SoftDeleteMixin:
    """软删除混入类"""
    deleted = fields.SmallIntField(description="删除标记: 0-未删除, 1-已删除", default=0, index=True)
    deleted_at = fields.DatetimeField(description="删除时间", null=True)

    async def soft_delete(self):
        """执行软删除"""
        self.deleted = 1
        self.deleted_at = datetime.now()
        await self.save(update_fields=["deleted", "deleted_at"])

    @classmethod
    def filter_active(cls):
        """过滤未删除的记录"""
        return cls.filter(deleted=0)


class ReportConfig(BaseModel, TimestampMixin, SoftDeleteMixin):
    """报表配置模型"""
    system_name = fields.CharField(max_length=100, description="系统名称", index=True)
    report_name = fields.CharField(max_length=100, description="报表名称", index=True)
    sql_statement = fields.TextField(description="SQL语句")
    db_connection = fields.ForeignKeyField(
        "models.DBConnection",
        related_name="reports",
        description="数据库连接ID",
        on_delete=fields.CASCADE
    )
    maintainer = fields.CharField(max_length=100, description="维护人", index=True)

    class Meta:
        table = "report_config"
        description = "报表配置表"

    def __str__(self):
        return f"{self.system_name} - {self.report_name} ({self.id})"


class ReportGeneration(BaseModel, SoftDeleteMixin):
    """报表生成记录模型"""
    report_name = fields.CharField(max_length=200, description="报表名称", index=True)
    report_config = fields.ForeignKeyField(
        "models.ReportConfig",
        related_name="generations",
        description="报表配置ID",
        on_delete=fields.CASCADE
    )
    generator = fields.CharField(max_length=100, description="生成人", index=True)
    generated_at = fields.DatetimeField(description="生成时间", auto_now_add=True, index=True)
    completed_at = fields.DatetimeField(description="完成时间", null=True)
    status = fields.CharField(
        max_length=20,
        description="报表状态: exporting-导出中, completed-已完成, failed-失败",
        default="exporting",
        index=True
    )
    file_path = fields.CharField(max_length=500, description="文件路径", null=True)
    execution_json = fields.JSONField(description="执行日志(SQL语句、数据库连接等)", null=True)

    class Meta:
        table = "report_generation"
        description = "报表生成记录表"

    def __str__(self):
        return f"{self.report_name} ({self.id})"
