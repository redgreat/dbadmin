from pydantic import BaseModel, Field
from .base import mcp_tool, _ok, _err
from aiagent.models.ai_approval import AiApproval

class QueryApprovalStatusInput(BaseModel):
    approval_no: str = Field(..., description="审批单号")

@mcp_tool(
    name="query_approval_status",
    description="查询审批单当前状态",
    input_model=QueryApprovalStatusInput,
    is_write=False
)
async def query_approval_status(args: QueryApprovalStatusInput):
    approval = await AiApproval.filter(approval_no=args.approval_no).first()
    if not approval:
        return _err("未找到该审批单")
    return _ok({"status": approval.status, "reviewer_name": approval.reviewer_name}, "查询成功")
