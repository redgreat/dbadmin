from fastapi import APIRouter

from .simfill import router as simfill_router
from .simiccid import router as simiccid_router
from .simtrans import router as simtrans_router

sim_router = APIRouter()
sim_router.include_router(simfill_router, prefix="/simfill", tags=["SIM卡中心"])
sim_router.include_router(simiccid_router, prefix="/simiccid", tags=["SIM卡中心"])
sim_router.include_router(simtrans_router, prefix="/simtrans", tags=["SIM卡中心"])
