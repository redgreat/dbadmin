from fastapi import APIRouter

from .orders import router
from .oms import router as oms_router_orders

oms_router = APIRouter()
oms_router.include_router(router, prefix="/orders", tags=["订单操作"])
oms_router.include_router(oms_router_orders)

__all__ = ["oms_router"]
