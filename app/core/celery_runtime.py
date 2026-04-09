import asyncio
from typing import Any, Awaitable, Callable

from tortoise import Tortoise

from app.settings.database import get_tortoise_config_with_dynamic


def run_async_with_tortoise(async_func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
    """
    在 Celery Worker 中安全运行异步业务逻辑：
    - 初始化 Tortoise
    - 执行异步函数
    - 关闭连接
    """

    async def _runner():
        await Tortoise.init(config=get_tortoise_config_with_dynamic())
        try:
            return await async_func(*args, **kwargs)
        finally:
            await Tortoise.close_connections()

    return asyncio.run(_runner())
