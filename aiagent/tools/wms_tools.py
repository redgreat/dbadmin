from pydantic import BaseModel, Field
from typing import List
from .base import mcp_tool, _ok, _err, _create_approval, _notify_dba_wecom

class QueryStockStatusInput(BaseModel):
    stock_nos: List[str] = Field(..., description="仓储单据编码列表")

@mcp_tool(
    name="query_stock_status",
    description="查询仓储单据状态",
    input_model=QueryStockStatusInput,
    is_write=False
)
async def query_stock_status(args: QueryStockStatusInput):
    return _ok({"found_docs": []}, "查询成功")

class SubmitDeleteStockInput(BaseModel):
    stock_nos: List[str] = Field(..., description="要删除的仓储单据编码列表")
    operator_id: str = Field(..., description="申请人工号")
    remark: str = Field(default="", description="备注")

@mcp_tool(
    name="submit_delete_stock_logical",
    description="提交仓储单据逻辑删除审批申请",
    input_model=SubmitDeleteStockInput,
    is_write=True
)
async def submit_delete_stock_logical(args: SubmitDeleteStockInput):
    approval = await _create_approval("delete_stock_logical", args.model_dump(), args.operator_id, args.remark, "WMS")
    await _notify_dba_wecom(approval)
    return _ok(
        data={"approval_no": approval.approval_no},
        message=f"已提交审批单 {approval.approval_no}，请联系 {approval.reviewer_name} 审核。"
    )
