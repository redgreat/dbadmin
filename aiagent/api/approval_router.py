from fastapi import APIRouter, Query
from aiagent.models.ai_approval import AiApproval
from pydantic import BaseModel
from datetime import datetime
from app.schemas.base import Success, SuccessExtra, Fail

approval_router = APIRouter()

class ApproveRequest(BaseModel):
    comment: str = ""

@approval_router.get("/")
async def list_approvals(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1)):
    total = await AiApproval.all().count()
    approvals = await AiApproval.all().order_by("-id").offset((page - 1) * page_size).limit(page_size).values()
    return SuccessExtra(data=list(approvals), total=total, page=page, page_size=page_size)

@approval_router.post("/{approval_no}/approve")
async def approve(approval_no: str, req: ApproveRequest):
    approval = await AiApproval.filter(approval_no=approval_no).first()
    if not approval:
        return Fail(msg="审批单不存在")
    if approval.status != "pending":
        return Fail(msg=f"当前状态不可审批: {approval.status}")
    
    # 执行实际逻辑 (占位)
    approval.status = "executed"
    approval.executed_at = datetime.now()
    approval.review_comment = req.comment
    approval.execute_result = {"status": "ok", "msg": "审批通过并执行"}
    await approval.save()
    
    return Success(msg="审批通过")

@approval_router.post("/{approval_no}/reject")
async def reject(approval_no: str, req: ApproveRequest):
    approval = await AiApproval.filter(approval_no=approval_no).first()
    if not approval:
        return Fail(msg="审批单不存在")
    
    approval.status = "rejected"
    approval.reviewed_at = datetime.now()
    approval.review_comment = req.comment
    await approval.save()
    
    return Success(msg="审批已拒绝")
