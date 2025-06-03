from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.controllers.oplog import oplog_controller
from app.schemas.oplog import (
    OpLogCreateRequest,
    OpLogUpdateRequest,
    OpLogQueryRequest,
    OpLogResponse,
    OpLogListResponse
)
from app.core.dependency import DependAuth

router = APIRouter()


@router.post("/create", summary="创建运维日志")
async def create_oplog(
    request: OpLogCreateRequest,
    _: str = DependAuth
) -> JSONResponse:
    """
    创建运维日志记录
    
    Args:
        request: 运维日志创建请求
        
    Returns:
        创建的运维日志信息
    """
    try:
        result = await oplog_controller.create_oplog(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "运维日志创建成功",
                "data": result.model_dump(mode='json')
            }
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "code": e.status_code,
                "message": e.detail,
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}",
                "data": None
            }
        )


@router.get("/list", summary="获取运维日志列表")
async def list_oplogs(
    logger: str = None,
    operater: str = None,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    page_size: int = 20,
    _: str = DependAuth
) -> JSONResponse:
    """
    获取运维日志列表
    
    Args:
        logger: 修改类型（可选）
        operater: 操作人（可选）
        start_date: 开始时间（可选，格式：YYYY-MM-DD HH:MM:SS）
        end_date: 结束时间（可选，格式：YYYY-MM-DD HH:MM:SS）
        page: 页码（默认1）
        page_size: 每页数量（默认20）
        
    Returns:
        运维日志列表和分页信息
    """
    try:
        from datetime import datetime
        from app.schemas.oplog import OpLogQueryRequest
        
        # 构建查询请求
        query_request = OpLogQueryRequest(
            logger=logger,
            operater=operater,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            end_date=datetime.fromisoformat(end_date) if end_date else None,
            page=page,
            page_size=page_size
        )
        
        result = await oplog_controller.query_oplogs(query_request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "获取成功",
                "data": result.model_dump(mode='json')
            }
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "code": e.status_code,
                "message": e.detail,
                "data": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": f"服务器内部错误: {str(e)}",
                "data": None
            }
        )
