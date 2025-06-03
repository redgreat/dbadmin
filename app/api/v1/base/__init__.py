from fastapi import APIRouter

from .base import router

base_router = APIRouter()
base_router.include_router(router)

__all__ = ["base_router"]
