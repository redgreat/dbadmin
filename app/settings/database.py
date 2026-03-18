"""
数据库配置模块
从统一配置文件 config.yml 读取数据库配置
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.core.config_loader import get_config

# 数据库引擎映射
DB_ENGINES = {
    'postgres': 'tortoise.backends.asyncpg',
    'mysql': 'tortoise.backends.mysql',
    'sqlite': 'tortoise.backends.sqlite',
}


def _get_admin_db_config():
    """从配置文件获取系统管理数据库配置"""
    config = get_config()
    admin_db = config.database.admin
    return {
        'engine': admin_db.engine,
        'credentials': admin_db.model_dump()
    }

def get_tortoise_config() -> Dict[str, Any]:
    """
    生成完整的Tortoise ORM配置（从 config.yml 读取）
    """
    admin_db = _get_admin_db_config()
    
    connections = {
        "default": {
            "engine": DB_ENGINES[admin_db['engine']],
            "credentials": {
                "host": admin_db['credentials']['host'],
                "port": admin_db['credentials']['port'],
                "user": admin_db['credentials']['user'],
                "password": admin_db['credentials']['password'],
                "database": admin_db['credentials']['database'],
                "minsize": admin_db['credentials'].get('min_size', 2),
                "maxsize": admin_db['credentials'].get('max_size', 10),
                "ssl": "disable",
            },
        }
    }
    return {
        "connections": connections,
        "apps": {
            "models": {
                "models": ["app.models", "aerich.models"],
                "default_connection": "default",
            }
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }

# 导出 Tortoise ORM 配置
TORTOISE_ORM = get_tortoise_config()

# 动态连接占位
DYNAMIC_CONNECTIONS: Dict[str, Dict[str, Any]] = {}

async def load_dynamic_connections():
    """
    加载动态数据库连接（占位实现）
    """
    return

def get_tortoise_config_with_dynamic() -> Dict[str, Any]:
    """
    获取包含动态连接的Tortoise配置（占位实现，返回静态配置）
    """
    return get_tortoise_config()

async def refresh_dynamic_connections():
    """
    刷新动态数据库连接（占位实现）
    """
    return
