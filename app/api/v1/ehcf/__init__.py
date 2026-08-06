from fastapi import APIRouter

from .order_regenerate import router as order_regenerate_router

ehcf_router = APIRouter()
ehcf_router.include_router(order_regenerate_router)

__all__ = ["ehcf_router"]
