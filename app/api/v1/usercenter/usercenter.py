"""用户中心查询接口"""
import logging

from fastapi import APIRouter, Query

from app.schemas.base import Fail, Success
from app.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", summary="根据姓名模糊查询用户中心用户")
async def search_users(
    keyword: str = Query("", description="姓名筛选值（模糊匹配）"),
    limit: int = Query(20, ge=1, le=100, description="最多返回条数"),
):
    """根据姓名模糊查询用户中心 basic_userinfo，返回 [{id, name}]"""
    try:
        keyword = (keyword or "").strip()
        if not keyword:
            return Success(data=[], msg="请输入姓名筛选值")
        users = await user_service.search_users(keyword, limit=limit)
        return Success(data=users, msg=f"查询到 {len(users)} 条记录")
    except Exception as e:
        logger.error(f"查询用户中心用户失败: {e}")
        return Fail(code=500, msg=f"查询失败: {str(e)}")


@router.get("/get_by_name", summary="根据姓名精确查询用户Id")
async def get_user_by_name(
    name: str = Query(..., description="姓名精确值"),
):
    """根据姓名精确查询用户Id，返回 {id, name}"""
    try:
        user = await user_service.get_user_by_name(name)
        if not user:
            return Success(data=None, msg=f"未找到姓名为 {name} 的用户")
        return Success(data=user, msg="查询成功")
    except Exception as e:
        logger.error(f"根据姓名查询用户失败: {e}")
        return Fail(code=500, msg=f"查询失败: {str(e)}")
