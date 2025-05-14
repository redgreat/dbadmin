from fastapi import APIRouter

from .buttons import router

buttons_router = APIRouter()
buttons_router.include_router(router, tags=["按钮权限"])
__all__ = ["buttons_router"]
