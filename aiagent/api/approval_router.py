from fastapi import APIRouter
from aiagent.models.ai_approval import AiApproval
from pydantic import BaseModel
from datetime import datetime

approval_router = APIRouter()

class ApproveRequest(BaseModel):
    comment: str = ""

@approval_router.post("/{approval_no}/approve")
async def approve(approval_no: str, req: ApproveRequest):
    approval = await AiApproval.filter(approval_no=approval_no).first()
    if not approval:
        return {"success": False, "error": "审批单不存在"}
    if approval.status != "pending":
        return {"success": False, "error": f"当前状态不可审批: {approval.status}"}
    
    # 执行实际逻辑 (占位)
    approval.status = "executed"
    approval.executed_at = datetime.now()
    approval.review_comment = req.comment
    approval.execute_result = {"status": "ok", "msg": "审批通过并执行"}
    await approval.save()
    
    return {"success": True, "message": "审批通过"}

@approval_router.post("/{approval_no}/reject")
async def reject(approval_no: str, req: ApproveRequest):
    approval = await AiApproval.filter(approval_no=approval_no).first()
    if not approval:
        return {"success": False, "error": "审批单不存在"}
    
    approval.status = "rejected"
    approval.reviewed_at = datetime.now()
    approval.review_comment = req.comment
    await approval.save()
    
    return {"success": True, "message": "审批已拒绝"}
