"""OA人员信息查询接口"""
import logging

from fastapi import APIRouter, Query

from app.schemas.base import Fail, Success
from app.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", summary="根据关键字模糊查询OA内勤人员")
async def search_users(
    keyword: str = Query("", description="姓名/编码/UserCenterUserId 任意字段"),
    limit: int = Query(20, ge=1, le=100, description="最多返回条数"),
):
    """从OA库 membership_userbaseinfo 模糊查询人员，返回 [{user_center_user_id, user_name, code}]"""
    try:
        keyword = (keyword or "").strip()
        if not keyword:
            return Success(data=[], msg="请输入筛选值")
        users = await user_service.search_users(keyword, limit=limit)
        return Success(data=users, msg=f"查询到 {len(users)} 条记录")
    except Exception as e:
        logger.error(f"查询OA人员失败: {e}")
        return Fail(code=500, msg=f"查询失败: {str(e)}")
