from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from app.schemas.base import Success, Fail
from app.core.dependency import AuthControl
from app.models.admin import User
from app.utils.audit_log import create_operation_audit_log
from app.services.simtrans_task import get_simtrans_sync_status, submit_simtrans_sync

router = APIRouter()


class SyncRequest(BaseModel):
    """同步请求体"""
    receipt_numbers: str


@router.post("/sync", summary="SIM卡同步 - 从仓储中心同步数据")
async def sync_sim_cards(req: Request, body: SyncRequest):
    """
    SIM卡同步接口
    输入入库单号（换行分隔），从仓储中心抓取数据并写入SIM卡中心
    """
    try:
        # 获取用户信息
        try:
            token = req.headers.get("token")
            user_obj: User = None
            if token:
                user_obj = await AuthControl.is_authed(token)
            user_id = user_obj.id if user_obj else 0
            username = user_obj.username if user_obj else ""
        except Exception:
            user_id = 0
            username = ""

        # 提交后台同步任务，避免大批量同步阻塞 HTTP 请求
        result = await submit_simtrans_sync(body.receipt_numbers)

        # 记录审计日志
        try:
            receipt_list = body.receipt_numbers.strip().split('\n')
            receipt_count = len([r for r in receipt_list if r.strip()])
            
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="SIM",
                summary=f"提交SIM卡同步任务: {receipt_count}个入库单, task_id={result.get('task_id')}",
                method="POST",
                path="/api/v1/sim/simtrans/sync",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body=result,
            )
        except Exception:
            pass

        return Success(data=result, msg=result.get('message', '同步任务已提交'))

    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"同步失败: {str(e)}")


@router.get("/sync/status", summary="查询SIM卡同步任务状态")
async def get_sync_status(task_id: str = Query(..., description="同步任务ID")):
    try:
        return Success(data=get_simtrans_sync_status(task_id), msg="OK")
    except Exception as e:
        return Fail(code=500, msg=f"查询同步状态失败: {str(e)}")
