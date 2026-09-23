from tortoise import fields

from .base import BaseModel, TimestampMixin


class SimDupVerifyRecord(BaseModel, TimestampMixin):
    """SIM卡重复入库验证记录（主表）"""

    batch_no = fields.CharField(
        max_length=50, unique=True, description="验证批次号（写入WMS临时表tm_remano的ImpStamp）", index=True
    )
    source = fields.CharField(
        max_length=20, default="web", description="验证来源: web-页面导入, api-对外接口", index=True
    )
    status = fields.CharField(
        max_length=20, default="processing", description="验证状态: processing-进行中, completed-已完成, failed-失败", index=True
    )
    filename = fields.CharField(max_length=255, default="", description="导入文件名（api来源为空）")
    total_count = fields.IntField(default=0, description="导入的SimNumber总数")
    duplicate_count = fields.IntField(default=0, description="重复入库的SimNumber数量")
    message = fields.TextField(null=True, description="验证结果/失败原因")
    result_file_path = fields.CharField(max_length=500, null=True, description="重复编码导出文件路径")
    user_id = fields.BigIntField(null=True, description="操作人ID（api来源为0）", index=True)
    username = fields.CharField(max_length=64, default="", description="操作人名称")
    api_caller = fields.CharField(max_length=100, default="", description="对外API调用方标识（X-App-Name）")
    started_at = fields.DatetimeField(null=True, description="开始验证时间", index=True)
    finished_at = fields.DatetimeField(null=True, description="完成验证时间")

    class Meta:
        table = "sys_simdupverify_record"
        description = "SIM卡重复入库验证记录表"
        indexes = [["status", "created_at"], ["user_id", "created_at"]]

    def __str__(self):
        return f"SimDupVerifyRecord({self.batch_no}, {self.status})"


class SimDupVerifyResult(BaseModel, TimestampMixin):
    """SIM卡重复入库验证结果（子表，每次验证命中的重复卡号）"""

    record = fields.ForeignKeyField(
        "models.SimDupVerifyRecord",
        related_name="results",
        on_delete=fields.CASCADE,
        description="验证记录",
    )
    sim_number = fields.CharField(max_length=200, description="重复入库的SimNumber（物料编码）", index=True)

    class Meta:
        table = "sys_simdupverify_result"
        description = "SIM卡重复入库验证结果表"
        indexes = [["sim_number"], ["record_id", "sim_number"]]

    def __str__(self):
        return f"SimDupVerifyResult({self.sim_number})"
