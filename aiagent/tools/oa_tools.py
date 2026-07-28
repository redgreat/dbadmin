from pydantic import BaseModel, Field

from .base import _create_approval, _notify_dba_wecom, _ok, mcp_tool


class ValidateOaPositiveTimeInput(BaseModel):
    emp_id: str = Field(..., description="员工号")

@mcp_tool(
    name="validate_oa_positive_time",
    description="验证 OA 转正时间是否可修改",
    input_model=ValidateOaPositiveTimeInput,
    is_write=False
)
async def validate_oa_positive_time(args: ValidateOaPositiveTimeInput):
    return _ok({"can_update": True, "emp_id": args.emp_id}, "可以修改")


class SubmitUpdateOaPositiveTimeInput(BaseModel):
    emp_id: str = Field(..., description="员工号")
    new_time: str = Field(..., description="新的转正时间")
    operator_id: str = Field(..., description="申请人工号")
    remark: str = Field(default="", description="修改备注")

@mcp_tool(
    name="submit_update_oa_positive_time",
    description="提交修改 OA 转正时间审批申请",
    input_model=SubmitUpdateOaPositiveTimeInput,
    is_write=True
)
async def submit_update_oa_positive_time(args: SubmitUpdateOaPositiveTimeInput):
    approval = await _create_approval("update_oa_positive_time", args.model_dump(), args.operator_id, args.remark, "OA")
    await _notify_dba_wecom(approval)
    return _ok(
        data={"approval_no": approval.approval_no},
        message=f"已提交审批单 {approval.approval_no}，请联系 {approval.reviewer_name} 审核。"
    )
