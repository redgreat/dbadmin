from fastapi import APIRouter

from .orders import router

oms_router = APIRouter()
oms_router.include_router(router)

__all__ = ["oms_router"]
