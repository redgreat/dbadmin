from tortoise import fields
from tortoise.models import Model


class PythonScript(Model):
    """Python脚本模型"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, description="脚本名称", index=True)
    code = fields.TextField(description="脚本内容")
    description = fields.TextField(description="脚本描述", null=True)
    status = fields.BooleanField(default=True, description="是否启用")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "python_script"
        description = "Python脚本表"

    def __str__(self):
        return f"{self.name} ({self.id})"


class ScriptRunLog(Model):
    """脚本执行日志模型"""

    id = fields.IntField(pk=True)
    script = fields.ForeignKeyField("models.PythonScript", related_name="run_logs", on_delete=fields.CASCADE, description="关联的脚本")
    status = fields.CharField(max_length=20, description="执行状态: success, failed, running")
    start_time = fields.DatetimeField(description="开始时间")
    end_time = fields.DatetimeField(description="结束时间", null=True)
    duration = fields.IntField(description="执行时长(秒)", null=True)
    output = fields.TextField(description="执行输出", null=True)
    error = fields.TextField(description="错误信息", null=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "script_run_log"
        description = "脚本执行日志表"

    def __str__(self):
        return f"ScriptRunLog {self.id} for Script {self.script_id}"
