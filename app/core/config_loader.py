"""
统一配置加载器
从 config/config.yml 读取所有配置
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """应用配置"""
    title: str = "数据运维"
    version: str = "0.1.0"
    description: str = "数据库管理后台"
    debug: bool = False
    secret_key: str
    db_password_salt: str = "dbadmin_salt_v1"


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8090
    workers: int = 1
    log_level: str = "info"


class JWTConfig(BaseModel):
    """JWT 配置"""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7天


class DBCredentials(BaseModel):
    """数据库连接凭据"""
    engine: str = "postgres"
    host: str
    port: int
    user: str
    password: str
    database: str
    min_size: int = Field(default=2, description="最小连接数")
    max_size: int = Field(default=10, description="最大连接数")


class DatabaseConfig(BaseModel):
    """数据库配置"""
    admin: DBCredentials


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelprefix)s %(message)s"
    directory: str = "./log"
    rotation: str = "50 MB"
    retention: int = 5


class CORSConfig(BaseModel):
    """CORS 配置"""
    origins: list = ["*"]
    allow_credentials: bool = True
    allow_methods: list = ["*"]
    allow_headers: list = ["*"]


class FrontendConfig(BaseModel):
    """前端配置"""
    title: str = "数据运维"
    port: int = 5180
    api_base_url: str = "/api"


class NginxConfig(BaseModel):
    """Nginx 配置"""
    enabled: bool = True
    listen_port: int = 80
    server_name: str = "localhost"
    static_root: str = "/opt/dbadmin/web/dist"
    api_proxy_pass: str = "http://127.0.0.1:8090"


class Config(BaseModel):
    """统一配置模型"""
    app: AppConfig
    server: ServerConfig
    jwt: JWTConfig
    database: DatabaseConfig
    logging: LoggingConfig
    cors: CORSConfig
    frontend: FrontendConfig
    nginx: NginxConfig


class ConfigLoader:
    """配置加载器"""
    
    _instance: Optional['ConfigLoader'] = None
    _config: Optional[Config] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self, config_path: Optional[str] = None) -> Config:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径，默认为 config/config.yml
            
        Returns:
            配置对象
        """
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).resolve().parent.parent.parent
            config_path = base_dir / "config" / "config.yml"
        
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {config_path}\n"
                f"请复制 config/config.yml.example 并重命名为 config.yml"
            )
        
        # 读取 YAML 配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        if not config_data:
            raise ValueError("配置文件为空或格式错误")
        
        # 解析为配置对象
        self._config = Config(**config_data)
        return self._config
    
    @property
    def config(self) -> Config:
        """获取配置对象"""
        if self._config is None:
            self.load_config()
        return self._config
    
    def reload(self, config_path: Optional[str] = None):
        """重新加载配置"""
        self._config = None
        return self.load_config(config_path)


# 全局配置加载器实例
_loader = ConfigLoader()


def get_config() -> Config:
    """获取全局配置对象"""
    return _loader.config


def reload_config(config_path: Optional[str] = None) -> Config:
    """重新加载配置"""
    return _loader.reload(config_path)


# 导出常用配置对象
config = get_config()
