from fastapi import APIRouter

from .base import router
from .workbench import router as workbench_router

base_router = APIRouter()
base_router.include_router(router)
base_router.include_router(workbench_router)

__all__ = ["base_router"]
