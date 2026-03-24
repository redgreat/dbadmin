from fastapi import APIRouter

from .wms_curd import router

wms_router = APIRouter()
wms_router.include_router(router)

__all__ = ["wms_router"]