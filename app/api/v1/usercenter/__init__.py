from fastapi import APIRouter

from .usercenter import router

usercenter_router = APIRouter()
usercenter_router.include_router(router)

__all__ = ["usercenter_router"]
