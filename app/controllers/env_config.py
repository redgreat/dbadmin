import subprocess
import sys
from typing import List, Optional

from app.models.env_config import EnvConfig, PythonPackage
from app.schemas.env_config import (
    EnvConfigCreate,
    EnvConfigOut,
    EnvConfigUpdate,
    PythonPackageCreate,
    PythonPackageOut,
    PythonPackageUpdate,
)


class EnvConfigController:
    """环境变量配置控制器"""

    async def get_env_configs(self, page: int = 1, limit: int = 10, key: str = None):
        """获取环境变量列表"""
        query = EnvConfig.all()
        if key:
            query = query.filter(key__icontains=key)

        total = await query.count()
        configs = await query.offset((page - 1) * limit).limit(limit)

        data = []
        for config in configs:
            item = config.model_dump(mode='json')
            # 敏感字段脱敏显示
            if config.is_sensitive:
                item['value'] = '******'
            data.append(item)

        return {"total": total, "data": data}

    async def get_env_config(self, config_id: int):
        """获取环境变量详情"""
        config = await EnvConfig.get_or_none(id=config_id)
        if not config:
            return None
        return config.model_dump(mode='json')

    async def create_env_config(self, data: EnvConfigCreate):
        """创建环境变量"""
        config = await EnvConfig.create(**data.model_dump())
        return config.model_dump(mode='json')

    async def update_env_config(self, config_id: int, data: EnvConfigUpdate):
        """更新环境变量"""
        config = await EnvConfig.get_or_none(id=config_id)
        if not config:
            return None

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        await config.update_from_dict(update_data).save()

        result = config.model_dump(mode='json')
        if config.is_sensitive:
            result['value'] = '******'
        return result

    async def delete_env_config(self, config_id: int):
        """删除环境变量"""
        config = await EnvConfig.get_or_none(id=config_id)
        if not config:
            return False
        await config.delete()
        return True

    async def get_all_env_configs(self):
        """获取所有环境变量（用于脚本执行时注入）"""
        configs = await EnvConfig.all()
        return {config.key: config.value for config in configs}


class PythonPackageController:
    """Python包控制器"""

    async def get_packages(self, page: int = 1, limit: int = 10, name: str = None):
        """获取包列表"""
        query = PythonPackage.all()
        if name:
            query = query.filter(name__icontains=name)

        total = await query.count()
        packages = await query.offset((page - 1) * limit).limit(limit)

        data = [pkg.model_dump(mode='json') for pkg in packages]
        return {"total": total, "data": data}

    async def create_package(self, data: PythonPackageCreate):
        """创建包"""
        pkg = await PythonPackage.create(**data.model_dump())
        return pkg.model_dump(mode='json')

    async def update_package(self, pkg_id: int, data: PythonPackageUpdate):
        """更新包"""
        pkg = await PythonPackage.get_or_none(id=pkg_id)
        if not pkg:
            return None

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        await pkg.update_from_dict(update_data).save()

        return pkg.model_dump(mode='json')

    async def delete_package(self, pkg_id: int):
        """删除包"""
        pkg = await PythonPackage.get_or_none(id=pkg_id)
        if not pkg:
            return False
        await pkg.delete()
        return True

    async def install_package(self, pkg_id: int):
        """安装包"""
        pkg = await PythonPackage.get_or_none(id=pkg_id)
        if not pkg:
            return None

        # 构建安装命令
        package_spec = pkg.name
        if pkg.version:
            package_spec = f"{pkg.name}=={pkg.version}"

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_spec],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                pkg.is_installed = True
                pkg.installed_at = datetime.now()
                await pkg.save()
                return {"success": True, "output": result.stdout}
            else:
                return {"success": False, "error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "安装超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def uninstall_package(self, pkg_id: int):
        """卸载包"""
        pkg = await PythonPackage.get_or_none(id=pkg_id)
        if not pkg:
            return None

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", pkg.name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                pkg.is_installed = False
                pkg.installed_at = None
                await pkg.save()
                return {"success": True, "output": result.stdout}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_installed_packages(self):
        """获取已安装的包列表"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                import json
                packages = json.loads(result.stdout)
                return {"success": True, "packages": packages}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}


from datetime import datetime

env_config_controller = EnvConfigController()
python_package_controller = PythonPackageController()
