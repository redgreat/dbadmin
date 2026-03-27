"""
FCC报销单关联API接口
"""
import logging
from fastapi import APIRouter, Request

from app.core.dependency import AuthControl
from app.models.admin import AuditLog, User
from app.schemas.base import Fail, Success
from app.schemas.wms import FccParseIn, FccValidateIn, FccSubmitIn
from app.services.fcc_relation_service import fcc_relation_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/fcc/parse", summary="解析输入文本")
async def parse_input(body: FccParseIn):
    """
    解析批量输入文本
    
    格式规则：
    - 每行一个FCC报销单与多个仓储对账单的关联
    - 格式：FCC报销单号:仓储对账单1,仓储对账单2,...;
    - 示例：J202512250009:ZD20260325153906B413D18,ZD202603251538028DCFA89;
    """
    try:
        result = fcc_relation_service.parse_input_text(body.input_text)
        return Success(data=result)
    except Exception as e:
        logger.error(f"解析失败: {e}")
        return Fail(code=500, msg=f"解析失败: {str(e)}")


@router.post("/fcc/validate", summary="验证单据存在性")
async def validate_codenumber(body: FccValidateIn):
    """
    验证单据存在性
    
    验证FCC报销单和仓储对账单在数据库中是否存在
    """
    try:
        relations = [r.dict() for r in body.relations]
        result = await fcc_relation_service.validate_codenumber(relations)
        return Success(data=result)
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return Fail(code=500, msg=f"验证失败: {str(e)}")


@router.post("/fcc/submit", summary="提交关联任务")
async def submit_task(req: Request, body: FccSubmitIn):
    """
    提交关联任务
    
    创建异步任务执行关联操作
    """
    try:
        relations = [r.dict() for r in body.relations]
        task_id = await fcc_relation_service.submit_task(relations)
        
        # 记录审计日志
        current_user = req.state.user
        if current_user:
            await AuditLog.create(
                user_id=current_user.id,
                module="wms_fcc",
                action="submit",
                content=f"提交FCC关联任务，任务ID: {task_id}，关联数量: {len(relations)}",
            )
        
        return Success(data={'task_id': task_id})
    except Exception as e:
        logger.error(f"提交失败: {e}")
        return Fail(code=500, msg=f"提交失败: {str(e)}")


@router.get("/fcc/task/{task_id}", summary="查询任务状态")
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    查询异步任务的执行状态和结果
    """
    try:
        result = fcc_relation_service.query_task_status(task_id)
        if not result:
            return Fail(code=404, msg="任务不存在")
        return Success(data=result)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        return Fail(code=500, msg=f"查询失败: {str(e)}")
