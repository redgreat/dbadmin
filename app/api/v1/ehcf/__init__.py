from fastapi import APIRouter

from .newaccept_refresh import router as newaccept_refresh_router
from .order_regenerate import router as order_regenerate_router
from .workorder_manage import router as workorder_manage_router

ehcf_router = APIRouter()
ehcf_router.include_router(order_regenerate_router)
ehcf_router.include_router(workorder_manage_router)
ehcf_router.include_router(newaccept_refresh_router)

__all__ = ["ehcf_router"]
