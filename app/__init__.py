from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_app,
    make_middlewares,
    register_exceptions,
    register_routers,
)
from app.services.task_scheduler import scheduler

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await init_app(app)
    yield
    await scheduler.shutdown()
    await Tortoise.close_connections()


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "基础模块", "description": "基础信息相关接口,包括登录、用户信息、菜单等"},
            {"name": "用户模块", "description": "用户管理相关接口"},
            {"name": "角色模块", "description": "角色管理相关接口"},
            {"name": "菜单模块", "description": "菜单管理相关接口"},
            {"name": "接口管理", "description": "API接口管理相关接口"},
            {"name": "审计日志", "description": "审计日志查询相关接口"},
            {"name": "连接管理", "description": "数据库连接管理相关接口"},
            {"name": "日常工具", "description": "SQL格式化、Excel临时表生成等工具接口"},
            {"name": "定时任务", "description": "定时任务管理相关接口"},
            {"name": "告警中心", "description": "告警信息管理相关接口"},
            {"name": "SIM卡中心", "description": "SIM卡管理相关接口,包括ICCID导入、特殊预警客户等"},
            {"name": "订单中心", "description": "订单中心运维相关接口,包括订单时间修改、订单删除等"},
            {"name": "仓储中心", "description": "仓储中心运维相关接口,单据删除等"},
            {"name": "运维日志", "description": "运维日志记录相关接口"},
            {"name": "报表管理", "description": "报表配置和生成相关接口"},
        ],
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_routers(app)
    register_exceptions(app)
    return app


app = create_app()
