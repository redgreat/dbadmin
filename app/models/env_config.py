from tortoise import fields, models


class EnvConfig(models.Model):
    """环境变量配置"""
    id = fields.IntField(pk=True)
    key = fields.CharField(max_length=100, unique=True, description="变量名")
    value = fields.TextField(description="变量值")
    description = fields.CharField(max_length=255, null=True, description="描述")
    is_sensitive = fields.BooleanField(default=False, description="是否敏感（如密码）")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "env_config"
        ordering = ["key"]

    def __str__(self):
        return self.key


class PythonPackage(models.Model):
    """Python包管理"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True, description="包名")
    version = fields.CharField(max_length=50, null=True, description="版本号")
    description = fields.CharField(max_length=255, null=True, description="描述")
    is_installed = fields.BooleanField(default=False, description="是否已安装")
    installed_at = fields.DatetimeField(null=True, description="安装时间")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "python_package"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}=={self.version}" if self.version else self.name
