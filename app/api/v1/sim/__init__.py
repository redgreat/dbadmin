from fastapi import APIRouter
from .simiccid import router as simiccid_router

sim_router = APIRouter()
sim_router.include_router(simiccid_router, prefix="/simiccid", tags=["SIM"])
