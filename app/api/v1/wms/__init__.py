from fastapi import APIRouter

from .wms_curd import router
from .wms_fcc import router as fcc_router
from .wms_simdup import router as simdup_router

wms_router = APIRouter()
wms_router.include_router(router)
wms_router.include_router(fcc_router)
wms_router.include_router(simdup_router)

__all__ = ["wms_router"]
