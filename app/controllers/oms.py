from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from pydantic import BaseModel
from datetime import datetime
from math import ceil

from app.services.conn_manager import db_manager
from app.settings.database import refresh_dynamic_connections
from app.log import logger
from app.models.oplog import OpLog


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
            # 解析订单ID
            order_ids = [oid.strip() for oid in request.order_ids.split(',') if oid.strip()]
            
            if not order_ids:
                raise HTTPException(status_code=400, detail="订单ID不能为空")
            
            # 获取连接信息
            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")
            
            found_orders = []
            not_found_orders = []
            
            # 验证数据库类型
            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")
            
            # MySQL查询
            for order_id in order_ids:
                sql = "SELECT order_id FROM orders WHERE order_id = %s OR order_code = %s LIMIT 1"
                result = await db_manager.execute_query(request.conn_id, sql, [order_id, order_id])
                
                if result:
                    found_orders.append(order_id)
                else:
                    not_found_orders.append(order_id)
            
            return {
                "success": len(not_found_orders) == 0,
                "total_count": len(order_ids),
                "found_count": len(found_orders),
                "not_found_count": len(not_found_orders),
                "found_orders": found_orders,
                "not_found_orders": not_found_orders,
                "connection_name": conn_info['name']
            }
            
        except Exception as e:
            logger.error(f"验证订单时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"验证订单失败: {str(e)}")
    
    @staticmethod
    async def batch_update_audit_time(request: OrderUpdateRequest) -> Dict[str, Any]:
        """
        批量更新订单审核时间
        """
        try:
            # 解析订单ID
            order_ids = [oid.strip() for oid in request.order_ids.split(',') if oid.strip()]
            
            if not order_ids:
                raise HTTPException(status_code=400, detail="订单ID不能为空")
            
            # 获取连接信息
            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")
            
            updated_orders = []
            failed_orders = []
            
            # 验证数据库类型
            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")
            
            # MySQL更新
            for order_id in order_ids:
                try:
                    # 更新订单审核时间
                    sql = "UPDATE orders SET audit_time = %s, update_reason = %s WHERE order_id = %s OR order_code = %s"
                    affected_rows = await db_manager.execute_update(
                        request.conn_id, 
                        sql, 
                        [request.new_audit_time, request.reason, order_id, order_id]
                    )
                    
                    if affected_rows > 0:
                        updated_orders.append(order_id)
                    else:
                        failed_orders.append({"order_id": order_id, "reason": "订单不存在"})
                        
                except Exception as e:
                    failed_orders.append({"order_id": order_id, "reason": str(e)})
            
            # 记录操作日志到oplog表
            if updated_orders:
                try:
                    oplog_data = {
                        "updated_orders": updated_orders,
                        "new_audit_time": request.new_audit_time.isoformat(),
                        "reason": request.reason,
                        "connection_name": conn_info['name'],
                        "total_count": len(updated_orders)
                    }
                    
                    await OpLog.create(
                        logger="订单审核时间批量修改",
                        chgmsg=oplog_data,
                        operater="system",
                        final_modify_time=datetime.now()
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
    



# 创建控制器实例
oms_controller = OMSController()