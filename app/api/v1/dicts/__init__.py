from fastapi import APIRouter

from .dicts import router

dicts_router = APIRouter()
dicts_router.include_router(router)
