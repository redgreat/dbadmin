from tortoise import fields
from tortoise.models import Model


class AiApproval(Model):
    """DBA 运维操作审批单"""

    id = fields.BigIntField(pk=True)
    approval_no = fields.CharField(max_length=32, unique=True, index=True,
                                   description="审批单号，格式：OPS-YYYYMMDD-NNN")

    # 操作信息
    op_type = fields.CharField(max_length=100, index=True,
                               description="操作类型：delete_orders_logical / update_oa_time 等")
    op_module = fields.CharField(max_length=50, description="业务模块：OMS / WMS / OA")
    op_params = fields.JSONField(description="操作参数（完整入参，用于审批通过后执行）")
    op_description = fields.TextField(description="AI 生成的操作描述（给 DBA 看）")

    # 申请信息
    applicant_id = fields.CharField(max_length=50, description="申请人工号")
    applicant_name = fields.CharField(max_length=100, null=True, description="申请人姓名")
    ai_session_id = fields.CharField(max_length=64, null=True, index=True,
                                     description="来源会话 ID")
    remark = fields.TextField(null=True, description="申请备注")

    # 审批信息（从公司用户中心获取，预留）
    reviewer_id = fields.CharField(max_length=50, null=True, description="审批人工号")
    reviewer_name = fields.CharField(max_length=100, null=True, description="审批人姓名")
    reviewer_contact = fields.CharField(max_length=100, null=True,
                                        description="联系方式（企业微信ID/手机/邮箱）")
    wecom_message_id = fields.CharField(max_length=200, null=True,
                                        description="企业微信消息ID（用于后续回调）")

    # 状态流转
    status = fields.CharField(max_length=20, default="pending", index=True,
                              description="pending/approved/rejected/expired/executed")
    reviewed_at = fields.DatetimeField(null=True)
    review_comment = fields.TextField(null=True, description="审批意见")
    executed_at = fields.DatetimeField(null=True, description="实际执行时间")
    execute_result = fields.JSONField(null=True, description="执行结果")

    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField(null=True, description="审批超时时间，默认24小时")

    class Meta:
        table = "ai_approval"
