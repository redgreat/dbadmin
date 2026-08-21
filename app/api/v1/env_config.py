from fastapi import APIRouter, Query

from app.controllers.env_config import env_config_controller, python_package_controller
from app.schemas.env_config import (
    EnvConfigCreate,
    EnvConfigOut,
    EnvConfigUpdate,
    PythonPackageCreate,
    PythonPackageOut,
    PythonPackageUpdate,
)
from app.schemas.base import Success, Fail

router = APIRouter(prefix="/env", tags=["环境变量配置"])


@router.get("/configs")
async def get_env_configs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    key: str = Query(None),
):
    """获取环境变量列表"""
    data = await env_config_controller.get_env_configs(page, limit, key)
    return Success(data=data)


@router.get("/configs/{config_id}")
async def get_env_config(config_id: int):
    """获取环境变量详情"""
    data = await env_config_controller.get_env_config(config_id)
    if not data:
        return Fail(msg="环境变量不存在")
    return Success(data=data)


@router.post("/configs")
async def create_env_config(data: EnvConfigCreate):
    """创建环境变量"""
    result = await env_config_controller.create_env_config(data)
    return Success(msg="创建成功", data=result)


@router.put("/configs/{config_id}")
async def update_env_config(config_id: int, data: EnvConfigUpdate):
    """更新环境变量"""
    result = await env_config_controller.update_env_config(config_id, data)
    if not result:
        return Fail(msg="环境变量不存在")
    return Success(msg="更新成功", data=result)


@router.delete("/configs/{config_id}")
async def delete_env_config(config_id: int):
    """删除环境变量"""
    success = await env_config_controller.delete_env_config(config_id)
    if not success:
        return Fail(msg="环境变量不存在")
    return Success(msg="删除成功")


@router.get("/configs/all/get")
async def get_all_env_configs():
    """获取所有环境变量（用于脚本执行）"""
    data = await env_config_controller.get_all_env_configs()
    return Success(data=data)


# Python包管理路由
@router.get("/packages")
async def get_packages(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    name: str = Query(None),
):
    """获取包列表"""
    data = await python_package_controller.get_packages(page, limit, name)
    return Success(data=data)


@router.post("/packages")
async def create_package(data: PythonPackageCreate):
    """创建包"""
    result = await python_package_controller.create_package(data)
    return Success(msg="创建成功", data=result)


@router.put("/packages/{pkg_id}")
async def update_package(pkg_id: int, data: PythonPackageUpdate):
    """更新包"""
    result = await python_package_controller.update_package(pkg_id, data)
    if not result:
        return Fail(msg="包不存在")
    return Success(msg="更新成功", data=result)


@router.delete("/packages/{pkg_id}")
async def delete_package(pkg_id: int):
    """删除包"""
    success = await python_package_controller.delete_package(pkg_id)
    if not success:
        return Fail(msg="包不存在")
    return Success(msg="删除成功")


@router.post("/packages/{pkg_id}/install")
async def install_package(pkg_id: int):
    """安装包"""
    result = await python_package_controller.install_package(pkg_id)
    if result is None:
        return Fail(msg="包不存在")
    if result.get("success"):
        return Success(msg="安装成功", data=result)
    return Fail(msg=f"安装失败: {result.get('error')}")


@router.post("/packages/{pkg_id}/uninstall")
async def uninstall_package(pkg_id: int):
    """卸载包"""
    result = await python_package_controller.uninstall_package(pkg_id)
    if result is None:
        return Fail(msg="包不存在")
    if result.get("success"):
        return Success(msg="卸载成功", data=result)
    return Fail(msg=f"卸载失败: {result.get('error')}")


@router.get("/packages/installed/list")
async def get_installed_packages():
    """获取已安装的包列表"""
    result = await python_package_controller.get_installed_packages()
    if result.get("success"):
        return Success(data=result.get("packages", []))
    return Fail(msg=f"获取失败: {result.get('error')}")
