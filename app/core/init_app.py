import shutil

from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

from app.api import api_router
from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.log import logger
from app.models.admin import Api, Menu, MenuApi, Role
from app.schemas.menus import MenuType
from app.services.task_scheduler import scheduler
from app.settings.config import settings
from app.settings.database import get_tortoise_config, load_dynamic_connections
from app.utils.password import get_password_hash

from .middlewares import BackGroundTaskMiddleware, HttpAuditLogMiddleware


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/docs",
                "/openapi.json",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def init_database(app: FastAPI):
    try:
        db_config = get_tortoise_config()
        await Tortoise.init(config=db_config)
        command = Command(tortoise_config=db_config, app="models")
        try:
            await command.init()
        except FileExistsError:
            logger.info("迁移文件夹已存在！")

        conn = Tortoise.get_connection("default")
        try:
            aerich_check = await conn.execute_query_dict("SELECT to_regclass('public.aerich') AS aerich")
            aerich_exists = bool(aerich_check and aerich_check[0].get("aerich"))
        except Exception:
            aerich_exists = False

        if aerich_exists:
            try:
                await command.upgrade(run_in_transaction=True)
            except Exception as e:
                logger.warning(f"迁移升级失败，改为同步模型: {e}")
                await Tortoise.generate_schemas()
        else:
            try:
                table_check = await conn.execute_query_dict(
                    "SELECT to_regclass('public.conn') AS conn, to_regclass('public\"user\"') AS user"
                )
                has_existing_tables = any(table_check and table_check[0].values())
            except Exception:
                has_existing_tables = False

            if has_existing_tables:
                await Tortoise.generate_schemas()
                logger.warning("检测到已有业务表但无迁移版本表：已跳过迁移，改为同步模型。")
            else:
                await command.upgrade(run_in_transaction=True)

        logger.info("数据库初始化成功完成！")
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e!s}")
        raise


async def init_superuser():
    user = await user_controller.model.exists()
    if not user:
        await user_controller.create(
            UserCreate(
                username="wangcw",
                email="rubygreat@msn.com",
                password=get_password_hash('Lunz2017'),
                is_active=True,
                is_superuser=True,
            )
        )


async def init_menus():
    """检查菜单表是否有数据，如果没有则记录错误日志"""
    try:
        menus = await Menu.exists()
        if not menus:
            logger.error(
                "========================================\n"
                "菜单表没有数据！\n"
                "========================================\n"
                "请执行以下操作之一：\n"
                "1. 运行数据库迁移: aerich migrate && aerich upgrade\n"
                "2. 手动插入菜单数据到数据库\n"
                "3. 检查数据库连接配置是否正确\n"
                "========================================"
            )
            return False
        await ensure_oa_menus()
        return True
    except Exception as e:
        logger.error(f"检查菜单表失败: {e}", exc_info=True)
        return False


async def ensure_oa_menus():
    """确保OA运维菜单存在"""
    parent = await Menu.get_or_none(path="/oa", parent_id=0)
    if not parent:
        parent = await Menu.create(
            name="OA运维",
            menu_type=MenuType.CATALOG.value,
            icon="material-symbols:engineering-outline",
            path="/oa",
            order=60,
            parent_id=0,
            is_hidden=False,
            component="/oa",
            keepalive=True,
        )

    positive_child = await Menu.get_or_none(path="positive-time", parent_id=parent.id)
    if not positive_child:
        positive_child = await Menu.create(
            name="转正时间修改",
            menu_type=MenuType.MENU.value,
            icon="mdi:calendar-edit-outline",
            path="positive-time",
            order=1,
            parent_id=parent.id,
            is_hidden=False,
            component="/oa/positive-time",
            keepalive=True,
        )

    entry_child = await Menu.get_or_none(path="entry-time", parent_id=parent.id)
    if not entry_child:
        entry_child = await Menu.create(
            name="修改入职时间",
            menu_type=MenuType.MENU.value,
            icon="mdi:calendar-account-outline",
            path="entry-time",
            order=2,
            parent_id=parent.id,
            is_hidden=False,
            component="/oa/entry-time",
            keepalive=True,
        )

    admin_role = await Role.get_or_none(name="管理员")
    if admin_role:
        await admin_role.menus.add(parent, positive_child, entry_child)

    api_specs = [
        (positive_child.id, "POST", "/api/v1/oa/positive-time/validate", "验证转正时间"),
        (positive_child.id, "POST", "/api/v1/oa/positive-time/execute", "修改转正时间"),
        (entry_child.id, "POST", "/api/v1/oa/entry-time/validate", "验证入职时间"),
        (entry_child.id, "POST", "/api/v1/oa/entry-time/execute", "修改入职时间"),
    ]
    for menu_id, method, path, summary in api_specs:
        api_obj = await Api.filter(method=method, path=path).first()
        if not api_obj:
            api_obj = await Api.create(method=method, path=path, summary=summary, tags="OA运维")
        relation_exists = await MenuApi.filter(menu_id=menu_id, api_id=api_obj.id).exists()
        if not relation_exists:
            await MenuApi.create(menu_id=menu_id, api_id=api_obj.id)

async def init_apis():
    apis = await api_controller.model.exists()
    if not apis:
        await api_controller.refresh_api()


async def init_db():
    command = Command(tortoise_config=settings.TORTOISE_ORM)
    try:
        await command.init_db(safe=True)
    except FileExistsError:
        pass

    await command.init()
    try:
        await command.migrate()
    except AttributeError:
        logger.warning("无法从数据库中检索模型历史记录，模型历史将从头开始创建！")
        shutil.rmtree("migrations")
        await command.init_db(safe=True)

    await command.upgrade(run_in_transaction=True)


async def init_roles():
    """初始化角色"""
    try:
        roles = await Role.exists()
        if not roles:
            admin_role = await Role.create(
                name="管理员",
                desc="管理员角色",
            )
            user_role = await Role.create(
                name="普通用户",
                desc="普通用户角色",
            )
            logger.info("角色初始化完成！")
        else:
            logger.info("角色已存在，跳过初始化")
    except Exception as e:
        logger.error(f"初始化角色失败: {e}", exc_info=True)


async def init_task_scheduler():
    try:
        await scheduler.start()
        logger.info("任务调度器已启动！")
    except Exception as e:
        logger.error(f"启动任务调度器时发生错误: {e!s}")


async def init_dynamic_connections():
    """
    初始化动态数据库连接池
    """
    try:
        await load_dynamic_connections()
        logger.info("动态数据库连接池初始化完成！")
    except Exception as e:
        logger.error(f"初始化动态数据库连接池时发生错误: {e!s}")


async def reinit_tortoise_with_dynamic_connections():
    """
    重新初始化Tortoise以包含动态连接
    """
    try:
        # 获取包含动态连接的完整配置
        from app.settings.database import get_tortoise_config_with_dynamic
        dynamic_config = get_tortoise_config_with_dynamic()

        # 关闭现有连接
        await Tortoise.close_connections()

        # 重新初始化
        await Tortoise.init(config=dynamic_config)

        logger.info("Tortoise动态连接重新初始化完成！")
    except Exception as e:
        logger.error(f"重新初始化Tortoise动态连接时发生错误: {e!s}")


async def init_app(app: FastAPI):
    await init_database(app)
    await init_superuser()
    await init_apis()
    await init_menus()
    await init_roles()
    await init_dynamic_connections()
    await reinit_tortoise_with_dynamic_connections()
    await init_task_scheduler()

    return app


__all__ = [
    "init_app",
    "make_middlewares",
    "register_exceptions",
    "register_routers"
]
