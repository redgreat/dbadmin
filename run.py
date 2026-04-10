"""
开发环境启动脚本
"""
import warnings

warnings.filterwarnings("ignore", message="websockets.legacy is deprecated.*", category=DeprecationWarning)
warnings.filterwarnings(
    "ignore",
    message="websockets.server.WebSocketServerProtocol is deprecated",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message="Please use `import python_multipart` instead.",
    category=PendingDeprecationWarning,
)
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*", category=DeprecationWarning)
warnings.filterwarnings(
    "ignore",
    message="'crypt' is deprecated and slated for removal in Python 3.13",
    category=DeprecationWarning,
)

if __name__ == "__main__":
    import uvicorn
    from app.core.config_loader import get_config

    config = get_config()
    uvicorn.run(
        "app.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
    )
