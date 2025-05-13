from fastapi import APIRouter

from .apis import router as api_router
from .buttons import router as buttons_router

apis_router = APIRouter()
apis_router.include_router(api_router, tags=["API模块"])
apis_router.include_router(buttons_router, prefix="/button", tags=["按钮权限"])

__all__ = ["apis_router"]
