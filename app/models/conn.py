from tortoise import fields

from .base import BaseModel, TimestampMixin


class DBType:
    """数据库类型常量"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"


class DBConnection(BaseModel, TimestampMixin):
    """数据库连接模型"""
    name = fields.CharField(max_length=100, description="连接名称", index=True)
    db_type = fields.CharField(max_length=20, description="数据库类型", index=True)
    host = fields.CharField(max_length=200, description="主机地址")
    port = fields.IntField(description="端口")
    username = fields.CharField(max_length=100, description="用户名")
    password = fields.CharField(max_length=200, description="密码(加密)")
    database = fields.CharField(max_length=100, description="数据库名")
    params = fields.TextField(description="连接参数", null=True)
    status = fields.BooleanField(description="连接状态", default=False, index=True)
    remark = fields.TextField(description="备注", null=True)

    class Meta:
        table = "conn"
        description = "数据库连接表"

    def __str__(self):
        return f"{self.name} ({self.id})"
