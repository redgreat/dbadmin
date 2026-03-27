"""
应用配置模块
从统一配置文件 config.yml 读取配置
"""
import os
import typing

from app.core.config_loader import get_config


# 动态路径常量
PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))


class Settings:
    """应用配置类（从 config.yml 读取）"""
    
    def __init__(self):
        self._config = get_config()
    
    @property
    def VERSION(self) -> str:
        return self._config.app.version
    
    @property
    def APP_TITLE(self) -> str:
        return self._config.app.title
    
    @property
    def PROJECT_NAME(self) -> str:
        return self._config.app.title
    
    @property
    def APP_DESCRIPTION(self) -> str:
        return self._config.app.description
    
    @property
    def CORS_ORIGINS(self) -> typing.List:
        return self._config.cors.origins
    
    @property
    def CORS_ALLOW_CREDENTIALS(self) -> bool:
        return self._config.cors.allow_credentials
    
    @property
    def CORS_ALLOW_METHODS(self) -> typing.List:
        return self._config.cors.allow_methods
    
    @property
    def CORS_ALLOW_HEADERS(self) -> typing.List:
        return self._config.cors.allow_headers
    
    @property
    def ADD_LOG_ORIGINS_INCLUDE(self) -> list:
        return ["*"]
    
    @property
    def ADD_LOG_ORIGINS_DECLUDE(self) -> list:
        return ["/system-manage", "/redoc", "/doc", "/openapi.json"]
    
    @property
    def DEBUG(self) -> bool:
        return self._config.app.debug
    
    @property
    def PROJECT_ROOT(self) -> str:
        return PROJECT_ROOT
    
    @property
    def BASE_DIR(self) -> str:
        return BASE_DIR
    
    @property
    def LOGS_ROOT(self) -> str:
        # 使用配置文件中的日志目录
        log_dir = self._config.logging.directory
        if os.path.isabs(log_dir):
            return log_dir
        return os.path.join(BASE_DIR, log_dir)
    
    @property
    def SECRET_KEY(self) -> str:
        return self._config.app.secret_key
    
    @property
    def JWT_ALGORITHM(self) -> str:
        return self._config.jwt.algorithm
    
    @property
    def JWT_ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self._config.jwt.access_token_expire_minutes
    
    @property
    def DATETIME_FORMAT(self) -> str:
        return "%Y-%m-%d %H:%M:%S"
    
    @property
    def DB_PASSWORD_SALT(self) -> str:
        return self._config.app.db_password_salt

    @property
    def SIM_CONN_ID(self) -> int:
        # 保持原有的硬编码值（可以后续移到配置文件）
        return 5

    @property
    def ORDER_CONN_ID(self) -> int:
        # 保持原有的硬编码值（可以后续移到配置文件）
        return 4

    @property
    def WMS_CONN_ID(self) -> int:
        # 仓储中心数据库连接ID（需要用户配置）
        return 6

    @property
    def FCC_CONN_ID(self) -> int:
        # FCC数据库连接ID（需要用户配置）
        return 7
settings = Settings()
