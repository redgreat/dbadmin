from fastapi import APIRouter

from app.core.dependency import DependPermisson

from .apis import apis_router
from .auditlog import auditlog_router
from .base import base_router
from .conns import conns_router
from .menus import menus_router
from .roles import roles_router
from .tasks import tasks_router
from .users import users_router
from .oplog import oplog_router
from .oms import oms_router

v1_router = APIRouter()

v1_router.include_router(base_router, prefix="/base", tags=["基础模块"])
v1_router.include_router(users_router, prefix="/user", tags=["用户模块"], dependencies=[DependPermisson])
v1_router.include_router(roles_router, prefix="/role", tags=["角色模块"], dependencies=[DependPermisson])
v1_router.include_router(menus_router, prefix="/menu", tags=["菜单模块"], dependencies=[DependPermisson])
v1_router.include_router(apis_router, prefix="/api", tags=["接口管理"], dependencies=[DependPermisson])
v1_router.include_router(auditlog_router, prefix="/auditlog", tags=["审计日志"], dependencies=[DependPermisson])
v1_router.include_router(tasks_router, prefix="/task", tags=["定时任务"], dependencies=[DependPermisson])
v1_router.include_router(conns_router, prefix="/conn", tags=["连接管理"], dependencies=[DependPermisson])
v1_router.include_router(oplog_router, prefix="/oplog", tags=["运维日志"], dependencies=[DependPermisson])
v1_router.include_router(oms_router, prefix="/oms", tags=["订单运维"], dependencies=[DependPermisson])
