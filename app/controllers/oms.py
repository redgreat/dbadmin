from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
import pytz
from math import ceil

from app.services.conn_manager import db_manager
from app.settings.database import refresh_dynamic_connections
from app.log import logger
from app.controllers.oplog import OpLogController


class OrderValidationRequest(BaseModel):
    """订单验证请求模型"""
    order_ids: str
    conn_id: int


class OrderUpdateRequest(BaseModel):
    """订单更新请求模型"""
    order_ids: str
    new_audit_time: datetime
    reason: str
    conn_id: int


class OrderDeleteValidationRequest(BaseModel):
    """订单删除验证请求模型"""
    order_ids: str
    conn_id: int


class OrderDeleteRequest(BaseModel):
    """订单删除请求模型"""
    order_ids: str
    reason: str
    conn_id: int


class OMSController:
    """
    订单管理系统控制器
    """
    
    @staticmethod
    async def validate_orders(request: OrderValidationRequest) -> Dict[str, Any]:
        """
        验证订单ID是否存在
        """
        try:
            order_ids = [oid.strip() for oid in request.order_ids.split(',') if oid.strip()]
            if not order_ids:
                raise HTTPException(status_code=400, detail="订单ID不能为空")
            
            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")
            
            found_orders = []
            not_found_orders = []
            
            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")
            
            for order_id in order_ids:
                sql = "SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE Id = %s OR OrderNo = %s LIMIT 1"
                result = await db_manager.execute_query(request.conn_id, sql, [order_id, order_id])
                
                if result and len(result) > 1 and result[1]:
                    data_list = result[1]
                    if data_list and len(data_list) > 0:
                        order_data = data_list[0]
                        found_orders.append({
                            "id": order_data.get('Id'),
                            "orderNo": order_data.get('OrderNo'),
                            "auditTime": order_data.get('AuditTime').strftime('%Y-%m-%d %H:%M:%S') if order_data.get('AuditTime') else None
                        })
                    else:
                        not_found_orders.append(order_id)
                else:
                    not_found_orders.append(order_id)
            
            return {
                "success": len(not_found_orders) == 0,
                "total_count": len(order_ids),
                "found_count": len(found_orders),
                "not_found_count": len(not_found_orders),
                "foundOrders": found_orders,
                "notFoundIds": not_found_orders,
                "message": f"找到 {len(found_orders)} 条订单，{len(not_found_orders)} 条未找到" if not_found_orders else "所有订单都已找到",
                "connection_name": conn_info['name']
            }
            
        except Exception as e:
            logger.error(f"验证订单时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"验证订单失败: {str(e)}")
    
    @staticmethod
    async def validate_orders_for_delete(request: OrderDeleteValidationRequest) -> Dict[str, Any]:
        """
        验证订单是否存在且可删除
        """
        try:
            order_ids = [oid.strip() for oid in request.order_ids.split(',') if oid.strip()]
            if not order_ids:
                raise HTTPException(status_code=400, detail="订单ID不能为空")
            
            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")
            
            found_orders = []
            not_found_orders = []
            
            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")
            
            for order_id in order_ids:
                sql = "SELECT Id, OrderNo, OrderStatus, CreatedAt FROM tb_orderinfo WHERE Id = %s LIMIT 1"
                result = await db_manager.execute_query(request.conn_id, sql, [order_id])
                
                if result and len(result) > 1 and result[1]:
                    data_list = result[1]
                    if data_list and len(data_list) > 0:
                        order_data = data_list[0]
                        found_orders.append({
                            "id": order_data.get('Id'),
                            "orderNo": order_data.get('OrderNo'),
                            "status": order_data.get('OrderStatus', '未知'),
                            "createTime": order_data.get('CreatedAt').strftime('%Y-%m-%d %H:%M:%S') if order_data.get('CreatedAt') else None
                        })
                    else:
                        not_found_orders.append(order_id)
                else:
                    not_found_orders.append(order_id)
            
            return {
                "success": len(not_found_orders) == 0,
                "total_count": len(order_ids),
                "found_count": len(found_orders),
                "not_found_count": len(not_found_orders),
                "foundOrders": found_orders,
                "notFoundIds": not_found_orders,
                "message": f"找到 {len(found_orders)} 条订单，{len(not_found_orders)} 条未找到" if not_found_orders else "所有订单都已找到",
                "connection_name": conn_info['name']
            }
            
        except Exception as e:
            logger.error(f"验证订单删除时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"验证订单删除失败: {str(e)}")
    
    @staticmethod
    async def batch_update_audit_time(request: OrderUpdateRequest) -> Dict[str, Any]:
        """
        批量更新订单审核时间
        """
        try:
            order_ids = [oid.strip() for oid in request.order_ids.split(',') if oid.strip()]
            
            if not order_ids:
                raise HTTPException(status_code=400, detail="订单ID不能为空")

            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")
            
            updated_orders = []
            failed_orders = []
            
            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")
            
            beijing_tz = pytz.timezone('Asia/Shanghai')
            if request.new_audit_time.tzinfo is None:
                utc_time = request.new_audit_time.replace(tzinfo=pytz.UTC)
            else:
                utc_time = request.new_audit_time.astimezone(pytz.UTC)
            
            beijing_time = utc_time.astimezone(beijing_tz)
            formatted_time = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
            
            for order_id in order_ids:
                try:
                    sql = "UPDATE tb_orderinfo SET AuditTime = %s WHERE Id = %s OR OrderNo = %s"
                    affected_rows = await db_manager.execute_update(
                        request.conn_id, 
                        sql, 
                        [formatted_time, order_id, order_id]
                    )
                    
                    if affected_rows > 0:
                        updated_orders.append(order_id)
                    else:
                        failed_orders.append({"order_id": order_id, "reason": "订单不存在"})
                        
                except Exception as e:
                    failed_orders.append({"order_id": order_id, "reason": str(e)})
            
            if updated_orders:
                try:
                    oplog_data = {
                        "updated_orders": updated_orders,
                        "new_audit_time": formatted_time,
                        "reason": request.reason,
                        "connection_name": conn_info['name'],
                        "total_count": len(updated_orders)
                    }
                    
                    await OpLogController.create_operation_log(
                        logger_type="订单审核时间修改",
                        operation_content=oplog_data,
                        operator="system",
                        modify_time=datetime.now(beijing_tz)
                    )
                except Exception as e:
                    logger.error(f"记录操作日志失败: {str(e)}")
            
            return {
                "success": len(failed_orders) == 0,
                "total_count": len(order_ids),
                "updated_count": len(updated_orders),
                "failed_count": len(failed_orders),
                "updated_orders": updated_orders,
                "failed_orders": failed_orders,
                "connection_name": conn_info['name']
            }
            
        except Exception as e:
            logger.error(f"批量更新订单审核时间时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")
    
    @staticmethod
    async def batch_delete_orders(request: OrderDeleteRequest) -> Dict[str, Any]:
        """
        批量删除订单，调用MySQL存储过程
        """
        try:
            import uuid
            
            order_ids = [oid.strip() for oid in request.order_ids.split(',') if oid.strip()]
            
            if not order_ids:
                raise HTTPException(status_code=400, detail="订单ID不能为空")

            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")
            
            deleted_orders = []
            failed_orders = []
            
            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")
            
            # 生成随机UUID作为删除操作者ID
            deleted_by_id = str(uuid.uuid4())
            beijing_tz = pytz.timezone('Asia/Shanghai')
            current_time = datetime.now(beijing_tz)
            
            for order_id in order_ids:
                try:
                    sql = "CALL proc_DeleteOrderInfoById(%s, %s);"
                    result = await db_manager.execute_query(
                        request.conn_id, 
                        sql, 
                        [order_id, deleted_by_id]
                    )
                    
                    if result and len(result) > 1 and result[1]:
                        deleted_orders.append({
                            "orderId": order_id,
                            "deleteTime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                            "success": True,
                            "message": "删除成功"
                        })
                    else:
                        deleted_orders.append({
                            "orderId": order_id,
                            "deleteTime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                            "success": True,
                            "message": "删除成功"
                        })
                        
                except Exception as e:
                    failed_orders.append({
                        "orderId": order_id,
                        "deleteTime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "success": False,
                        "message": str(e)
                    })
            
            if deleted_orders:
                try:
                    oplog_data = {
                        "deleted_orders": [order["orderId"] for order in deleted_orders],
                        "reason": request.reason,
                        "connection_name": conn_info['name'],
                        "deleted_by_id": deleted_by_id,
                        "total_count": len(deleted_orders)
                    }
                    
                    await OpLogController.create_operation_log(
                        logger_type="订单批量删除",
                        operation_content=oplog_data,
                        operator="system",
                        modify_time=current_time
                    )
                except Exception as e:
                    logger.error(f"记录操作日志失败: {str(e)}")
            
            return {
                "success": len(failed_orders) == 0,
                "total_count": len(order_ids),
                "deleted_count": len(deleted_orders),
                "failed_count": len(failed_orders),
                "details": deleted_orders + failed_orders,
                "connection_name": conn_info['name']
            }
            
        except Exception as e:
            logger.error(f"批量删除订单时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")
    
    @staticmethod
    async def get_connections() -> List[Dict[str, Any]]:
        """
        获取所有可用的数据库连接
        """
        connections = db_manager.list_all_connections()
        return [
            {
                "id": conn_info["conn_id"],
                "name": conn_info["name"],
                "db_type": conn_info["db_type"],
                "connection_name": conn_name
            }
            for conn_name, conn_info in connections.items()
        ]
    
    @staticmethod
    async def refresh_connections() -> Dict[str, str]:
        """
        刷新数据库连接池
        """
        try:
            await refresh_dynamic_connections()
            return {"message": "连接池刷新成功"}
        except Exception as e:
            logger.error(f"刷新连接池时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"刷新连接池失败: {str(e)}")
    

oms_controller = OMSController()