from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_app,
    make_middlewares,
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
        docs_url="/docs",  # 配置swagger文档路径
        redoc_url="/redoc",  # 配置ReDoc文档路径
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "基础模块", "description": "基础信息相关接口"},
            {"name": "用户模块", "description": "用户相关接口"},
            {"name": "角色模块", "description": "角色相关接口"},
            {"name": "菜单模块", "description": "菜单相关接口"},
            {"name": "接口管理", "description": "接口相关接口"},
            {"name": "审计日志", "description": "审计日志相关接口"},
            {"name": "定时任务", "description": "定时任务相关接口"},
            {"name": "连接管理", "description": "数据库连接管理接口"},
        ],
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    return app


app = create_app()
