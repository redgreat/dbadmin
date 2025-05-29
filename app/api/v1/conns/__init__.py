from fastapi import APIRouter

from .conns import router

conns_router = APIRouter()
conns_router.include_router(router, tags=["连接管理"])

__all__ = ["conns_router"]
