from fastapi import APIRouter

from app.core.dependency import DependPermisson

from .apis import apis_router
from .auditlog import auditlog_router
from .base import base_router
from .conns import conns_router
from .dicts import dicts_router
from .menus import menus_router
from .roles import roles_router
from .tasks import tasks_router
from .users import users_router
from .oplog import oplog_router
from .oms import oms_router
from .sim import sim_router
from .tool import tool_router
from .imptask import router as imptask_router
from .report import report_router
from .wms import wms_router
from .imptask.imptask import download_sql_file

v1_router = APIRouter()

v1_router.include_router(base_router, prefix="/base", tags=["基础模块"])
v1_router.include_router(users_router, prefix="/user", tags=["用户模块"], dependencies=[DependPermisson])
v1_router.include_router(roles_router, prefix="/role", tags=["角色模块"], dependencies=[DependPermisson])
v1_router.include_router(menus_router, prefix="/menu", tags=["菜单模块"], dependencies=[DependPermisson])
v1_router.include_router(apis_router, prefix="/api", tags=["接口管理"], dependencies=[DependPermisson])
v1_router.include_router(auditlog_router, prefix="/auditlog", tags=["审计日志"], dependencies=[DependPermisson])
v1_router.include_router(tasks_router, prefix="/task", tags=["定时任务"], dependencies=[DependPermisson])
v1_router.include_router(conns_router, prefix="/conn", tags=["连接管理"], dependencies=[DependPermisson])
v1_router.include_router(dicts_router, prefix="/dict", tags=["字典管理"], dependencies=[DependPermisson])
v1_router.include_router(oplog_router, prefix="/oplog", tags=["运维日志"], dependencies=[DependPermisson])
v1_router.include_router(oms_router, prefix="/oms", tags=["订单中心"], dependencies=[DependPermisson])
v1_router.include_router(sim_router, prefix="/sim", tags=["SIM卡中心"], dependencies=[DependPermisson])
v1_router.include_router(tool_router, prefix="/tool", tags=["日常工具"], dependencies=[DependPermisson])
v1_router.include_router(report_router, prefix="/report", tags=["报表管理"], dependencies=[DependPermisson])
v1_router.include_router(wms_router, prefix="/wms", tags=["仓储中心"], dependencies=[DependPermisson])
# imptask下载接口 - 单独注册，不需要权限验证（在接口内部验证token）
v1_router.get("/imptask/download/{task_id}", summary="下载SQL文件")(download_sql_file)
# imptask其他接口 - 需要权限验证
v1_router.include_router(imptask_router, prefix="/imptask", tags=["Excel导入任务"], dependencies=[DependPermisson])
