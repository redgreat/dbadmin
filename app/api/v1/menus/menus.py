import logging

from fastapi import APIRouter, Body, Query
from fastapi.routing import APIRoute

from app.controllers.menu import menu_controller
from app.controllers.api import api_controller
from app.models.admin import Api, MenuApi, Menu
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.menus import *

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/list", summary="查看菜单列表")
async def list_menu(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
):
    """
    优化后的菜单列表查询
    使用单次查询获取所有菜单，然后在内存中构建树形结构
    """
    import time
    start_time = time.time()
    
    # 一次性获取所有菜单（避免N+1查询问题）
    all_menus = await menu_controller.model.all().order_by("order")
    query_time = time.time()
    logger.debug(f"查询所有菜单耗时: {query_time - start_time:.3f}秒, 菜单数量: {len(all_menus)}")
    
    # 构建菜单字典，方便快速查找
    menu_dict = {menu.id: await menu.to_dict() for menu in all_menus}
    dict_time = time.time()
    logger.debug(f"构建菜单字典耗时: {dict_time - query_time:.3f}秒")
    
    # 构建树形结构
    root_menus = []
    for menu in all_menus:
        menu_data = menu_dict[menu.id]
        if menu.parent_id == 0:
            # 根菜单
            root_menus.append(menu_data)
        else:
            # 子菜单，添加到父菜单的children中
            parent = menu_dict.get(menu.parent_id)
            if parent:
                if "children" not in parent:
                    parent["children"] = []
                parent["children"].append(menu_data)
    
    build_time = time.time()
    logger.debug(f"构建树形结构耗时: {build_time - dict_time:.3f}秒")
    logger.info(f"菜单列表查询总耗时: {build_time - start_time:.3f}秒")
    
    return SuccessExtra(data=root_menus, total=len(root_menus), page=page, page_size=page_size)


@router.get("/get", summary="查看菜单")
async def get_menu(
    menu_id: int = Query(..., description="菜单id"),
):
    result = await menu_controller.get(id=menu_id)
    return Success(data=result)


@router.post("/create", summary="创建菜单")
async def create_menu(
    menu_in: MenuCreate,
):
    await menu_controller.create(obj_in=menu_in)
    return Success(msg="Created Success")


@router.post("/update", summary="更新菜单")
async def update_menu(
    menu_in: MenuUpdate,
):
    await menu_controller.update(id=menu_in.id, obj_in=menu_in)
    return Success(msg="Updated Success")


@router.delete("/delete", summary="删除菜单")
async def delete_menu(
    id: int = Query(..., description="菜单id"),
):
    child_menu_count = await menu_controller.model.filter(parent_id=id).count()
    if child_menu_count > 0:
        return Fail(msg="Cannot delete a menu with child menus")
    # 删除菜单时同时删除关联的menu_api记录
    await MenuApi.filter(menu_id=id).delete()
    await menu_controller.remove(id=id)
    return Success(msg="Deleted Success")


# ==================== 菜单-API映射管理 ====================

@router.get("/api/list", summary="获取菜单关联的API列表")
async def get_menu_apis(
    menu_id: int = Query(..., description="菜单ID"),
):
    """获取指定菜单关联的所有API"""
    menu_api_relations = await MenuApi.filter(menu_id=menu_id).prefetch_related("api")
    apis = []
    for relation in menu_api_relations:
        if relation.api:
            api_dict = await relation.api.to_dict()
            apis.append(api_dict)
    return Success(data=apis)


@router.post("/api/update", summary="更新菜单关联的API")
async def update_menu_apis(
    data: dict = Body(...),
):
    """更新菜单关联的API列表"""
    menu_id = data.get("menu_id")
    api_ids = data.get("api_ids", [])
    
    if not menu_id:
        return Fail(msg="菜单ID不能为空")
    
    # 验证菜单存在
    menu = await menu_controller.get(id=menu_id)
    if not menu:
        return Fail(msg="菜单不存在")
    
    # 删除现有关联
    await MenuApi.filter(menu_id=menu_id).delete()
    
    # 添加新关联
    for api_id in api_ids:
        api = await Api.filter(id=api_id).first()
        if api:
            await MenuApi.create(menu_id=menu_id, api_id=api_id)
    
    return Success(msg="更新成功")


@router.get("/api/available", summary="获取可用的API列表")
async def get_available_apis(
    page: int = Query(1, description="页码"),
    page_size: int = Query(100, description="每页数量"),
    tags: str = Query("", description="API标签筛选"),
):
    """获取所有可用的API列表（用于选择关联）"""
    query = Api.all()
    if tags:
        query = query.filter(tags=tags)
    
    total = await query.count()
    apis = await query.offset((page - 1) * page_size).limit(page_size)
    data = [await api.to_dict() for api in apis]
    
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


# 刷新任务状态
_refresh_task_status = {"running": False, "result": None}


async def _do_refresh_menu_api_relations(mode: str = "increment"):
    """
    后台执行刷新菜单-API关系
    
    Args:
        mode: 刷新模式
            - "increment": 增量更新，只新增不删除（保留手动配置）
            - "full": 完全刷新，删除所有关联后重新创建
            - "smart": 智能更新，识别多菜单共用API并保留
    """
    from app import app
    
    global _refresh_task_status
    _refresh_task_status["running"] = True
    _refresh_task_status["result"] = None
    
    try:
        # 1. 先刷新API表
        await api_controller.refresh_api()
        logger.info("API表刷新完成")
        
        # 2. 获取所有菜单（只处理menu类型，不处理catalog类型）
        menus = await Menu.filter(menu_type="menu")
        
        # 3. 构建路由路径到API的映射
        route_api_map = {}  # {"/api/v1/user/list": Api对象}
        for route in app.routes:
            if isinstance(route, APIRoute) and len(route.dependencies) > 0:
                path = route.path_format
                method = list(route.methods)[0]
                api_obj = await Api.filter(path=path, method=method).first()
                if api_obj:
                    route_api_map[path] = api_obj
        
        # 4. 根据菜单的component路径匹配API
        # 规则：菜单component如 "/system/user"，对应API路径前缀 "/api/v1/user"
        
        if mode == "full":
            # 完全刷新模式：删除所有现有关联
            await MenuApi.all().delete()
            logger.info("已删除所有现有关联")
        
        updated_count = 0
        new_count = 0
        preserved_count = 0
        
        for menu in menus:
            if not menu.component:
                continue
            
            # 从component提取模块名，如 "/system/user" -> "user"
            component_parts = menu.component.strip("/").split("/")
            if len(component_parts) < 1:
                continue
            
            # 尝试匹配API路径
            matched_api_ids = []
            for api_path, api_obj in route_api_map.items():
                # 匹配规则：API路径包含菜单component的关键部分
                # 如菜单component="/system/user"，匹配API路径包含"/user/"
                for part in component_parts:
                    if f"/{part}/" in api_path or api_path.endswith(f"/{part}"):
                        matched_api_ids.append(api_obj.id)
                        break
            
            if matched_api_ids:
                matched_api_ids = set(matched_api_ids)  # 去重
                
                if mode == "increment":
                    # 增量更新模式：只添加新的关联，不删除现有关联
                    existing_relations = await MenuApi.filter(menu_id=menu.id)
                    existing_api_ids = {rel.api_id for rel in existing_relations}
                    
                    new_api_ids = matched_api_ids - existing_api_ids
                    for api_id in new_api_ids:
                        await MenuApi.create(menu_id=menu.id, api_id=api_id)
                        new_count += 1
                    
                    if new_api_ids:
                        updated_count += 1
                        logger.info(f"菜单 [{menu.name}] 新增 {len(new_api_ids)} 个API关联")
                    
                elif mode == "smart":
                    # 智能更新模式：识别多菜单共用API并保留
                    existing_relations = await MenuApi.filter(menu_id=menu.id)
                    existing_api_ids = {rel.api_id for rel in existing_relations}
                    
                    # 检查哪些API被多个菜单使用
                    multi_menu_apis = set()
                    for api_id in existing_api_ids:
                        # 查询这个API被多少个菜单使用
                        usage_count = await MenuApi.filter(api_id=api_id).count()
                        if usage_count > 1:
                            multi_menu_apis.add(api_id)
                    
                    # 保留多菜单共用的API，只更新其他API
                    new_api_ids = matched_api_ids - existing_api_ids
                    removed_api_ids = existing_api_ids - matched_api_ids - multi_menu_apis
                    
                    # 添加新关联
                    for api_id in new_api_ids:
                        await MenuApi.create(menu_id=menu.id, api_id=api_id)
                        new_count += 1
                    
                    # 删除不再匹配的关联（保留多菜单共用的）
                    for api_id in removed_api_ids:
                        await MenuApi.filter(menu_id=menu.id, api_id=api_id).delete()
                    
                    preserved_count += len(multi_menu_apis & existing_api_ids)
                    
                    if new_api_ids or removed_api_ids:
                        updated_count += 1
                        logger.info(f"菜单 [{menu.name}] 新增 {len(new_api_ids)} 个，删除 {len(removed_api_ids)} 个，保留 {len(multi_menu_apis & existing_api_ids)} 个多菜单共用API")
                
                else:  # mode == "full"
                    # 完全刷新模式：直接添加所有关联
                    for api_id in matched_api_ids:
                        await MenuApi.create(menu_id=menu.id, api_id=api_id)
                        new_count += 1
                    updated_count += 1
                    logger.info(f"菜单 [{menu.name}] 关联了 {len(matched_api_ids)} 个API")
        
        if mode == "increment":
            _refresh_task_status["result"] = f"增量更新完成：更新了 {updated_count} 个菜单，新增 {new_count} 个API关联"
        elif mode == "smart":
            _refresh_task_status["result"] = f"智能更新完成：更新了 {updated_count} 个菜单，新增 {new_count} 个，保留了 {preserved_count} 个多菜单共用API"
        else:
            _refresh_task_status["result"] = f"完全刷新完成：更新了 {updated_count} 个菜单，共 {new_count} 个API关联"
        
        logger.info(_refresh_task_status["result"])
    except Exception as e:
        _refresh_task_status["result"] = f"刷新失败: {str(e)}"
        logger.error(_refresh_task_status["result"])
    finally:
        _refresh_task_status["running"] = False


@router.post("/api/refresh", summary="刷新菜单-API关系")
async def refresh_menu_api_relations(mode: str = "increment"):
    """
    根据代码中的路由信息自动刷新菜单-API关系表（异步执行）
    
    Args:
        mode: 刷新模式
            - increment: 增量更新（默认），只新增不删除，保留手动配置
            - full: 完全刷新，删除所有关联后重新创建
            - smart: 智能更新，识别多菜单共用API并保留
    
    执行步骤：
        1. 先刷新API表（确保所有API都在数据库中）
        2. 根据菜单的component路径匹配对应的API路由
        3. 根据模式更新菜单-API关联
    """
    global _refresh_task_status
    
    if _refresh_task_status["running"]:
        return Success(msg="刷新任务正在执行中，请稍后查询结果")
    
    if mode not in ["increment", "full", "smart"]:
        return Fail(msg="无效的刷新模式，支持: increment, full, smart")
    
    # 启动后台任务
    import asyncio
    asyncio.create_task(_do_refresh_menu_api_relations(mode=mode))
    
    mode_desc = {
        "increment": "增量更新（只新增不删除）",
        "full": "完全刷新（删除所有后重建）",
        "smart": "智能更新（保留多菜单共用API）"
    }
    
    return Success(msg=f"刷新任务已启动（{mode_desc[mode]}），请稍后查询结果")


@router.get("/api/refresh/status", summary="获取刷新任务状态")
async def get_refresh_status():
    """获取刷新任务的状态和结果"""
    global _refresh_task_status
    return Success(data={
        "running": _refresh_task_status["running"],
        "result": _refresh_task_status["result"]
    })
