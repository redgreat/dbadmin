from fastapi import APIRouter

from .alert import router

alert_router = APIRouter()
alert_router.include_router(router)
