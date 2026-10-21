from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.dependency import AuthControl
from app.models.admin import User
from app.schemas.base import Fail, Success
from app.services.simfill import sim_fill_service
from app.utils.audit_log import create_operation_audit_log

router = APIRouter()


class QueryPendingRequest(BaseModel):
    """查询待补录数据请求体"""
    keywords: str


class FillItem(BaseModel):
    """单卡补录项（页面可改：卡年限与省市区）"""
    sim_number: str
    sim_age: int | None = None
    pro_code: str | None = None
    pro_name: str | None = None
    city_code: str | None = None
    city_name: str | None = None


class ExecuteFillRequest(BaseModel):
    """执行补录请求体"""
    items: list[FillItem]


async def _current_user(req: Request) -> tuple[int, str]:
    """解析当前登录用户（失败时返回匿名，供审计日志使用）"""
    try:
        token = req.headers.get("token")
        if token:
            user_obj: User = await AuthControl.is_authed(token)
            return user_obj.id, user_obj.username
    except Exception:
        pass
    return 0, ""


@router.post("/query", summary="SIM卡批发补录-查询待补录数据")
async def query_pending(req: Request, body: QueryPendingRequest):
    """
    查询需要补录的数据。

    输入 SIM 卡号或仓储中心批发出库单号（OT3，换行分隔，可混合），
    从仓储中心（只读）取出库单与卡年限，从 SIM 卡中心（只读）取现状，
    按正式同步链路字段映射计算各表（tb_siminfo / tb_simwarehouse /
    tb_simstatus / tb_simfollowinfo）缺口与待写入值。
    """
    user_id, username = await _current_user(req)
    try:
        result = await sim_fill_service.query_pending(body.keywords)
        summary = result.get("summary", {})
        try:
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="SIM",
                summary=f"查询SIM卡批发补录数据: {summary.get('card_count', 0)}卡, "
                        f"待补录{summary.get('pending_count', 0)}卡",
                method="POST",
                path="/api/v1/sim/simfill/query",
                status=200,
                request_body=body.model_dump(mode="json"),
                response_body={"summary": summary},
            )
        except Exception:
            pass
        msg = (f"共命中 {summary.get('card_count', 0)} 张卡，"
               f"{summary.get('pending_count', 0)} 张待补录，"
               f"{summary.get('skipped_count', 0)} 张跳过")
        return Success(data=result, msg=msg)
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"查询失败: {e!s}")


@router.post("/execute", summary="SIM卡批发补录-执行补录")
async def execute_fill(req: Request, body: ExecuteFillRequest):
    """
    执行补录（只写 SIM 卡中心）。

    - 空值才补、幂等可重跑；每卡一个事务。
    - 已加装 / 已注销 / SIM 卡中心无此卡自动跳过。
    - 卡年限与省市区以页面提交值为准（页面可修改）。
    """
    user_id, username = await _current_user(req)
    try:
        result = await sim_fill_service.execute_fill(
            [item.model_dump() for item in body.items]
        )
        summary = result.get("summary", {})
        try:
            await create_operation_audit_log(
                user_id=user_id,
                username=username,
                module="SIM",
                summary=f"执行SIM卡批发补录: 共{summary.get('total', 0)}卡, "
                        f"成功{summary.get('success_count', 0)}, "
                        f"跳过{summary.get('skipped_count', 0)}, "
                        f"失败{summary.get('failed_count', 0)}",
                method="POST",
                path="/api/v1/sim/simfill/execute",
                status=200,
                request_body={"items": [i.sim_number for i in body.items]},
                response_body={"summary": summary},
            )
        except Exception:
            pass
        msg = (f"补录完成：成功 {summary.get('success_count', 0)} 张，"
               f"跳过 {summary.get('skipped_count', 0)} 张，"
               f"失败 {summary.get('failed_count', 0)} 张")
        return Success(data=result, msg=msg)
    except ValueError as e:
        return Fail(code=400, msg=str(e))
    except Exception as e:
        return Fail(code=500, msg=f"补录执行失败: {e!s}")
