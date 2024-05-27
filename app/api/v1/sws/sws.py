#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @author by wangcw 
# @generate at 2024/5/27 上午11:26


import logging

from fastapi import APIRouter, Query
from fastapi.exceptions import HTTPException
import tortoise.Tortoise as T

from app.controllers import role_controller
from app.schemas.base import Success, SuccessExtra
from app.schemas.roles import *

logger = logging.getLogger(__name__)
router = APIRouter()


# @router.get("/sws/", summary="查看角色列表")
# async def list_role(
#     page: int = Query(1, description="页码"),
#     page_size: int = Query(10, description="每页数量"),
#     role_name: str = Query("", description="角色名称，用于查询"),
# ):
#     q = Q()
#     if role_name:
#         q = Q(name__contains=role_name)
#     total, role_objs = await role_controller.list(page=page, page_size=page_size, search=q)
#     data = [await obj.to_dict() for obj in role_objs]
#     return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


