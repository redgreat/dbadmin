"""
开发环境启动脚本
"""
import uvicorn
from app.core.config_loader import get_config

if __name__ == "__main__":
    config = get_config()
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )
