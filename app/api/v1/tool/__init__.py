from fastapi import APIRouter

from .tool import router

tool_router = APIRouter()
tool_router.include_router(router)

__all__ = ["tool_router"]
