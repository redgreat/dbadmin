from fastapi import APIRouter
from .simiccid import router as simiccid_router
from .simtrans import router as simtrans_router

sim_router = APIRouter()
sim_router.include_router(simiccid_router, prefix="/simiccid", tags=["SIM卡中心"])
sim_router.include_router(simtrans_router, prefix="/simtrans", tags=["SIM卡中心"])
