"""
Docker 环境启动脚本
从 config.yml 读取配置并启动 uvicorn 服务
"""
import uvicorn
from app.core.config_loader import get_config

if __name__ == "__main__":
    # 从配置文件加载配置
    config = get_config()
    
    # 日志配置（内置，不使用外部 JSON 文件）
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": "%(asctime)s - %(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": config.logging.level,
            },
            "uvicorn.error": {
                "level": config.logging.level,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": config.logging.level,
                "propagate": False,
            },
        },
    }
    
    # 启动 uvicorn（配置从 config.yml 读取）
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        log_config=log_config,
        log_level=config.server.log_level.lower(),
    )
