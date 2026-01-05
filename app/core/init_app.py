import shutil

from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise
from tortoise.expressions import Q

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
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from app.services.task_scheduler import scheduler
from app.settings.config import settings
from app.settings.database import get_tortoise_config, load_dynamic_connections
from app.utils.password import get_password_hash
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
            await command.upgrade(run_in_transaction=True)
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
        logger.error(f"初始化数据库时出错: {str(e)}")
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
    menus = await Menu.exists()
    if not menus:
        parent_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="系统管理",
            path="/system",
            order=1,
            parent_id=0,
            icon="carbon:gui-management",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/system/user",
        )
        children_menu = [
            Menu(
                menu_type=MenuType.MENU,
                name="用户管理",
                path="user",
                order=1,
                parent_id=parent_menu.id,
                icon="material-symbols:person-outline-rounded",
                is_hidden=False,
                component="/system/user",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="角色管理",
                path="role",
                order=2,
                parent_id=parent_menu.id,
                icon="carbon:user-role",
                is_hidden=False,
                component="/system/role",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="菜单管理",
                path="menu",
                order=3,
                parent_id=parent_menu.id,
                icon="material-symbols:list-alt-outline",
                is_hidden=False,
                component="/system/menu",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="API管理",
                path="api",
                order=4,
                parent_id=parent_menu.id,
                icon="ant-design:api-outlined",
                is_hidden=False,
                component="/system/api",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="审计日志",
                path="auditlog",
                order=5,
                parent_id=parent_menu.id,
                icon="ph:clipboard-text-bold",
                is_hidden=False,
                component="/system/auditlog",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(children_menu)
        # 连接管理
        conn_catalog = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="连接管理",
            path="/conn",
            order=3,
            parent_id=0,
            icon="material-symbols:database",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/conn",
        )
        await Menu.bulk_create(
            [
                Menu(
                    menu_type=MenuType.MENU,
                    name="连接管理",
                    path="",
                    order=1,
                    parent_id=conn_catalog.id,
                    icon="material-symbols:database-outline",
                    is_hidden=False,
                    component="/conn",
                    keepalive=False,
                ),
            ]
        )

        # 任务中心
        task_catalog = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="任务中心",
            path="/task",
            order=4,
            parent_id=0,
            icon="carbon:task",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/task",
        )
        await Menu.bulk_create(
            [
                Menu(
                    menu_type=MenuType.MENU,
                    name="任务管理",
                    path="",
                    order=1,
                    parent_id=task_catalog.id,
                    icon="mdi:clipboard-text-outline",
                    is_hidden=False,
                    component="/task",
                    keepalive=False,
                ),
            ]
        )

        # 告警中心
        alert_catalog = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="告警中心",
            path="/alert",
            order=5,
            parent_id=0,
            icon="mdi:alarm-light-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/alert",
        )
        await Menu.bulk_create(
            [
                Menu(
                    menu_type=MenuType.MENU,
                    name="告警管理",
                    path="",
                    order=1,
                    parent_id=alert_catalog.id,
                    icon="mdi:alarm-light",
                    is_hidden=False,
                    component="/alert",
                    keepalive=False,
                ),
            ]
        )

        # WMS 模块
        wms_catalog = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="WMS",
            path="/wms",
            order=6,
            parent_id=0,
            icon="mdi:warehouse",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/wms",
        )
        await Menu.bulk_create(
            [
                Menu(
                    menu_type=MenuType.MENU,
                    name="WMS主页",
                    path="",
                    order=1,
                    parent_id=wms_catalog.id,
                    icon="mdi:warehouse",
                    is_hidden=False,
                    component="/wms",
                    keepalive=False,
                ),
            ]
        )

        # OMS 模块
        oms_catalog = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="OMS",
            path="/oms",
            order=7,
            parent_id=0,
            icon="mdi:truck-fast-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/oms/oms1",
        )
        await Menu.bulk_create(
            [
                Menu(
                    menu_type=MenuType.MENU,
                    name="OMS1",
                    path="oms1",
                    order=1,
                    parent_id=oms_catalog.id,
                    icon="mdi:truck-fast",
                    is_hidden=False,
                    component="/oms/oms1",
                    keepalive=False,
                ),
            ]
        )
    # 确保“订单删除”菜单存在（在OMS目录下）
    try:
        oms_parent = await Menu.filter(path="/oms").first()
        if oms_parent:
            exists_delete = await Menu.filter(parent_id=oms_parent.id, component="/oms/oms-delete").exists()
            if not exists_delete:
                await Menu.create(
                    menu_type=MenuType.MENU,
                    name="订单删除",
                    path="oms-delete",
                    order=2,
                    parent_id=oms_parent.id,
                    icon="mdi:trash-can-outline",
                    is_hidden=False,
                    component="/oms/oms-delete",
                    keepalive=False,
                )
    except Exception:
        pass

        # EHCF 模块
        ehcf_catalog = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="EHCF",
            path="/ehcf",
            order=8,
            parent_id=0,
            icon="mdi:heart-pulse-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/ehcf",
        )
        await Menu.bulk_create(
            [
                Menu(
                    menu_type=MenuType.MENU,
                    name="EHCF主页",
                    path="",
                    order=1,
                    parent_id=ehcf_catalog.id,
                    icon="mdi:heart-pulse",
                    is_hidden=False,
                    component="/ehcf",
                    keepalive=False,
                ),
            ]
        )


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

        all_apis = await Api.all()
        await admin_role.apis.add(*all_apis)

        all_menus = await Menu.all()
        await admin_role.menus.add(*all_menus)
        await user_role.menus.add(*all_menus)

        basic_apis = await Api.filter(Q(method__in=["GET"]) | Q(tags="基础模块"))
        await user_role.apis.add(*basic_apis)


async def init_task_scheduler():
    try:
        await scheduler.start()
        logger.info("任务调度器已启动！")
    except Exception as e:
        logger.error(f"启动任务调度器时发生错误: {str(e)}")


async def init_dynamic_connections():
    """
    初始化动态数据库连接池
    """
    try:
        await load_dynamic_connections()
        logger.info("动态数据库连接池初始化完成！")
    except Exception as e:
        logger.error(f"初始化动态数据库连接池时发生错误: {str(e)}")


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
        logger.error(f"重新初始化Tortoise动态连接时发生错误: {str(e)}")


async def init_app(app: FastAPI):
    register_routers(app)
    register_exceptions(app)
    await init_database(app)
    await init_superuser()
    await init_menus()
    await init_apis()
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
