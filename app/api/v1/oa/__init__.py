from fastapi import APIRouter

from .entry_time import router as entry_time_router
from .positive_time import router as positive_time_router

oa_router = APIRouter()
oa_router.include_router(positive_time_router, prefix="/positive-time", tags=["OA运维"])
oa_router.include_router(entry_time_router, prefix="/entry-time", tags=["OA运维"])

__all__ = ["oa_router"]
