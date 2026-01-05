from fastapi import APIRouter

from .orders import router as orders_router

oms_router = APIRouter()
oms_router.include_router(orders_router, prefix="/orders", tags=["OMS"])
