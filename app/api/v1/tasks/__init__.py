from fastapi import APIRouter

from .tasks import router

tasks_router = APIRouter()
tasks_router.include_router(router)

__all__ = ["tasks_router"]
