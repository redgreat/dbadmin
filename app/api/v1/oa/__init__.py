from fastapi import APIRouter

from .positive_time import router as positive_time_router

oa_router = APIRouter()
oa_router.include_router(positive_time_router, prefix="/positive-time", tags=["OA运维"])

__all__ = ["oa_router"]
