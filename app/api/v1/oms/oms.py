from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.controllers.oms import oms_controller, OrderValidationRequest, OrderUpdateRequest, OrderDeleteValidationRequest, OrderDeleteRequest
from app.core.dependency import DependAuth

router = APIRouter()


@router.post("/validate-orders", summary="验证订单ID")
async def validate_orders(
    request: OrderValidationRequest,
    _: str = DependAuth
) -> JSONResponse:
    """
    验证订单ID是否存在
    
    Args:
        request: 包含订单ID列表和连接ID的请求
        
    Returns:
        验证结果，包含找到和未找到的订单列表
    """
    try:
        result = await oms_controller.validate_orders(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "验证完成",
                "data": result
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


@router.post("/validate-orders-for-delete", summary="验证订单是否可删除")
async def validate_orders_for_delete(
    request: OrderDeleteValidationRequest,
    _: str = DependAuth
) -> JSONResponse:
    """
    验证订单是否存在且可删除
    
    Args:
        request: 包含订单ID列表和连接ID的请求
        
    Returns:
        验证结果，包含找到和未找到的订单列表
    """
    try:
        result = await oms_controller.validate_orders_for_delete(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "验证完成",
                "data": result
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


@router.post("/batch-update-audit-time", summary="批量更新订单审核时间")
async def batch_update_audit_time(
    request: OrderUpdateRequest,
    _: str = DependAuth
) -> JSONResponse:
    """
    批量更新订单审核时间
    
    Args:
        request: 包含订单ID列表、新审核时间、原因和连接ID的请求
        
    Returns:
        更新结果，包含成功和失败的订单列表
    """
    try:
        result = await oms_controller.batch_update_audit_time(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "批量更新完成",
                "data": result
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


@router.post("/batch-delete-orders", summary="批量删除订单")
async def batch_delete_orders(
    request: OrderDeleteRequest,
    _: str = DependAuth
) -> JSONResponse:
    """
    批量删除订单，调用MySQL存储过程
    
    Args:
        request: 包含订单ID列表、删除原因和连接ID的请求
        
    Returns:
        删除结果，包含成功和失败的订单列表
    """
    try:
        result = await oms_controller.batch_delete_orders(request)
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "批量删除完成",
                "data": result
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


@router.get("/connections", summary="获取可用数据库连接")
async def get_connections(
    _: str = DependAuth
) -> JSONResponse:
    """
    获取所有可用的数据库连接
    
    Returns:
        数据库连接列表
    """
    try:
        result = await oms_controller.get_connections()
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "获取连接列表成功",
                "data": result
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


@router.post("/refresh-connections", summary="刷新数据库连接池")
async def refresh_connections(
    _: str = DependAuth
) -> JSONResponse:
    """
    刷新数据库连接池
    
    Returns:
        刷新结果
    """
    try:
        result = await oms_controller.refresh_connections()
        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": result["message"],
                "data": None
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