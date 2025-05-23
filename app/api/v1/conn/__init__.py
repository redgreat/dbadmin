from fastapi import APIRouter

from .conn import router as conn_router

router = APIRouter()
router.include_router(conn_router, prefix="/conn", tags=["数据库连接管理"])
