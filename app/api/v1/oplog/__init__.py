from fastapi import APIRouter

from .oplog import router

oplog_router = APIRouter()
oplog_router.include_router(router)

__all__ = ["oplog_router"]
