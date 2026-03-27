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

    async def SIM_CONN_ID(self) -> int:
        """SIM数据库连接ID（从数据库读取）"""
        return await self._get_conn_id_by_alias('SIM_CONN')
    
    async def ORDER_CONN_ID(self) -> int:
        """订单数据库连接ID（从数据库读取）"""
        return await self._get_conn_id_by_alias('ORDER_CONN')
    
    async def WMS_CONN_ID(self) -> int:
        """仓储中心数据库连接ID（从数据库读取）"""
        return await self._get_conn_id_by_alias('WMS_CONN')
    
    async def FCC_CONN_ID(self) -> int:
        """FCC数据库连接ID（从数据库读取）"""
        return await self._get_conn_id_by_alias('FCC_CONN')
    
    async def _get_conn_id_by_alias(self, alias: str) -> int:
        """
        根据连接别名从数据库获取连接ID（使用Tortoise ORM连接池）
        
        Args:
            alias: 连接别名
            
        Returns:
            连接ID，如果不存在则返回0
        """
        import logging
        from tortoise import Tortoise
        
        logger = logging.getLogger(__name__)
        
        # 使用缓存避免重复查询
        cache_key = f'_conn_id_cache_{alias}'
        if hasattr(self, cache_key):
            cached_value = getattr(self, cache_key)
            logger.info(f"[连接别名] 从缓存读取: alias={alias}, conn_id={cached_value}")
            return cached_value
            
        try:
            logger.info(f"[连接别名] 开始查询数据库: alias={alias}")
            conn = Tortoise.get_connection("default")
            logger.info(f"[连接别名] 获取到数据库连接: {conn}")
            
            # 执行SQL查询
            result = await conn.execute_query(
                "SELECT id FROM conn WHERE alias = $1 AND status = 1",
                [alias]
            )
            
            # 解析结果
            conn_id = 0
            if result and len(result) > 1 and result[1]:
                rows = result[1]
                if rows and len(rows) > 0:
                    conn_id = rows[0]['id']
                    logger.info(f"[连接别名] 数据库查询结果: alias={alias}, conn_id={conn_id}")
            else:
                logger.warning(f"[连接别名] 未找到连接: alias={alias}")
                
            # 缓存结果
            setattr(self, cache_key, conn_id)
            logger.info(f"[连接别名] 查询完成并缓存: alias={alias}, conn_id={conn_id}")
            return conn_id
            
        except Exception as e:
            logger.error(f"[连接别名] 获取连接ID失败: alias={alias}, error={e}", exc_info=True)
            return 0
settings = Settings()
