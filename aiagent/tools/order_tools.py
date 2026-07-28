
from pydantic import BaseModel, Field

from .base import _create_approval, _notify_dba_wecom, _ok, mcp_tool


class QueryOrderStatusInput(BaseModel):
    order_nos: list[str] = Field(..., description="订单编码或ID列表（支持混合）")

@mcp_tool(
    name="query_order_status",
    description=(
        "查询订单状态，返回审核时间、删除状态等信息。\n"
        "适用场景：在执行写操作前先确认订单当前状态。\n"
        "副作用：只读，不修改数据。"
    ),
    input_model=QueryOrderStatusInput,
    is_write=False,
)
async def query_order_status(args: QueryOrderStatusInput):
    # from app.services.order_service import order_service
    # result = await order_service.fetch_audit_time_map(args.order_nos)
    result = {"found_docs": [], "missing_docs": args.order_nos}
    return _ok(result, f"查询到 {len(result.get('found_docs', []))} 条订单")


class SubmitDeleteOrdersInput(BaseModel):
    order_nos: list[str] = Field(..., description="要删除的订单编码或ID列表")
    operator_id: str = Field(..., description="申请人工号")
    remark: str = Field(default="", description="删除原因和备注")

@mcp_tool(
    name="submit_delete_orders_logical",
    description=(
        "提交订单逻辑删除审批申请（不直接执行删除）。\n"
        "⚠️ 前置要求：必须先调用 query_order_status 确认订单存在且状态正常。\n"
        "执行流程：AI 提交申请 → 系统创建审批单 → 企业微信通知 DBA 审核 → DBA 确认后执行。\n"
        "返回：审批单号 + 负责 DBA 的联系方式。"
    ),
    input_model=SubmitDeleteOrdersInput,
    is_write=True,
)
async def submit_delete_orders_logical(args: SubmitDeleteOrdersInput):
    # 创建审批单（不执行实际操作）
    approval = await _create_approval(
        op_type="delete_orders_logical",
        op_params=args.model_dump(),
        applicant_id=args.operator_id,
        remark=args.remark,
    )
    # 发送企业微信通知（预留接口）
    await _notify_dba_wecom(approval)

    return _ok(
        data={
            "approval_no": approval.approval_no,
            "status": "pending",
            "op_type": "订单逻辑删除",
            "targets": args.order_nos,
            "reviewer": approval.reviewer_name,
            "reviewer_contact": approval.reviewer_contact,
        },
        message=(
            f"已提交审批单 {approval.approval_no}，"
            f"请联系 {approval.reviewer_name}（{approval.reviewer_contact}）审核后执行操作。"
        )
    )
