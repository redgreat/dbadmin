from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.schemas.base import Success, Fail
from app.core.dependency import AuthControl
from app.models.admin import User
from app.utils.audit_log import create_operation_audit_log
from app.services.simtrans import sim_trans_service

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

        # 执行同步
        result = await sim_trans_service.sync_sim_cards(body.receipt_numbers)

        # 记录审计日志
        try:
            receipt_list = body.receipt_numbers.strip().split('\n')
            receipt_count = len([r for r in receipt_list if r.strip()])
            
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="SIM",
                summary=f"SIM卡同步: {receipt_count}个入库单, 结果: {result.get('message', '未知')}",
                method="POST",
                path="/api/v1/sim/simtrans/sync",
                status=200 if result.get('success') else 400,
                request_body=body.model_dump(mode="json"),
                response_body=result,
            )
        except Exception:
            pass

        if result.get('success'):
            return Success(data=result, msg=result.get('message', '同步成功'))
        else:
            return Fail(code=400, msg=result.get('message', '同步失败'), data=result)

    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"同步失败: {str(e)}")
