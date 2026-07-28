from datetime import datetime
from typing import Any

import pytz
from fastapi import HTTPException
from pydantic import BaseModel

from app.controllers.oplog import OpLogController
from app.log import logger
from app.services.conn_manager import db_manager
from app.settings.config import settings
from app.settings.database import refresh_dynamic_connections


class OrderValidationRequest(BaseModel):
    """订单验证请求模型"""
    order_nos: str
    conn_id: int


class OrderUpdateRequest(BaseModel):
    """订单更新请求模型"""
    order_nos: str
    new_audit_time: datetime
    reason: str
    conn_id: int


class OrderDeleteValidationRequest(BaseModel):
    """订单删除验证请求模型"""
    order_nos: str
    conn_id: int


class OrderDeleteRequest(BaseModel):
    """订单删除请求模型"""
    order_nos: str
    reason: str
    conn_id: int


class OMSController:
    """
    订单管理系统控制器
    """

    @staticmethod
    async def validate_orders(request: OrderValidationRequest) -> dict[str, Any]:
        """
        验证订单编码是否存在
        """
        try:
            order_nos = [oid.strip() for oid in request.order_nos.split(',') if oid.strip()]
            if not order_nos:
                raise HTTPException(status_code=400, detail="订单编码不能为空")

            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")

            found_orders = []
            not_found_orders = []

            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")

            for order_no in order_nos:
                is_numeric = order_no.isdigit()

                # 根据输入类型决定主查和备查
                queries = []
                if is_numeric:
                    doc_id = int(order_no)
                    queries = [
                        ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE Id=%s AND Deleted=0 LIMIT 1", (doc_id,)),
                        ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                    ]
                else:
                    queries = [
                        ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                        ("SELECT Id, OrderNo, AuditTime FROM tb_orderinfo WHERE Id=%s AND Deleted=0 LIMIT 1", (order_no,)),
                    ]

                # 按优先级逐条查询，找到第一个命中的就停
                result = None
                for sql, params in queries:
                    result = await db_manager.execute_query(request.conn_id, sql, list(params))
                    if result and len(result) > 1 and result[1]:
                        data_list = result[1]
                        if data_list and len(data_list) > 0:
                            order_data = data_list[0]
                            found_orders.append({
                                "id": order_data.get('Id'),
                                "orderNo": order_data.get('OrderNo'),
                                "auditTime": order_data.get('AuditTime').strftime('%Y-%m-%d %H:%M:%S') if order_data.get('AuditTime') else None
                            })
                            logger.info(f"找到订单: {order_no} -> Id={order_data.get('Id')}, OrderNo={order_data.get('OrderNo')}")
                            break
                    result = None

                if not result or not found_orders or (found_orders and found_orders[-1]["orderNo"] != order_no and not any(o["orderNo"] == order_no or str(o["id"]) == order_no for o in found_orders)):
                    not_found_orders.append(order_no)
                    logger.warning(f"订单未找到: {order_no}")

            return {
                "success": len(not_found_orders) == 0,
                "total_count": len(order_nos),
                "found_count": len(found_orders),
                "not_found_count": len(not_found_orders),
                "foundOrders": found_orders,
                "notFoundIds": not_found_orders,
                "message": f"找到 {len(found_orders)} 条订单，{len(not_found_orders)} 条未找到" if not_found_orders else "所有订单都已找到",
                "connection_name": conn_info['name']
            }

        except Exception as e:
            logger.error(f"验证订单时发生错误: {e!s}")
            raise HTTPException(status_code=500, detail=f"验证订单失败: {e!s}")

    @staticmethod
    async def validate_orders_for_delete(request: OrderDeleteValidationRequest) -> dict[str, Any]:
        """
        验证订单是否存在且可删除（支持订单编码或订单Id）
        """
        try:
            order_nos = [oid.strip() for oid in request.order_nos.split(',') if oid.strip()]
            if not order_nos:
                raise HTTPException(status_code=400, detail="订单编码不能为空")

            conn_info = db_manager.get_connection_info(request.conn_id)
            if not conn_info:
                raise HTTPException(status_code=400, detail=f"连接ID {request.conn_id} 不存在")

            found_orders = []
            not_found_orders = []

            if conn_info['db_type'].lower() not in ['mysql']:
                raise HTTPException(status_code=400, detail=f"不支持的数据库类型: {conn_info['db_type']}，当前只支持MySQL")

            for order_no in order_nos:
                is_numeric = order_no.isdigit()

                # 根据输入类型决定主查和备查
                queries = []
                if is_numeric:
                    doc_id = int(order_no)
                    queries = [
                        ("SELECT Id, OrderNo, OrderStatus, CreatedAt FROM tb_orderinfo WHERE Id=%s AND Deleted=1 LIMIT 1", (doc_id,)),
                        ("SELECT Id, OrderNo, OrderStatus, CreatedAt FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=1 LIMIT 1", (order_no,)),
                    ]
                else:
                    queries = [
                        ("SELECT Id, OrderNo, OrderStatus, CreatedAt FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=1 LIMIT 1", (order_no,)),
                        ("SELECT Id, OrderNo, OrderStatus, CreatedAt FROM tb_orderinfo WHERE Id=%s AND Deleted=1 LIMIT 1", (order_no,)),
                    ]

                # 按优先级逐条查询，找到第一个命中的就停
                result = None
                for sql, params in queries:
                    result = await db_manager.execute_query(request.conn_id, sql, list(params))
                    if result and len(result) > 1 and result[1]:
                        data_list = result[1]
                        if data_list and len(data_list) > 0:
                            result = data_list[0]
                            break
                    result = None

                if result:
                    found_orders.append({
                        "id": result.get('Id'),
                        "orderNo": result.get('OrderNo'),
                        "status": result.get('OrderStatus', '未知'),
                        "createTime": result.get('CreatedAt').strftime('%Y-%m-%d %H:%M:%S') if result.get('CreatedAt') else None
                    })
                    logger.info(f"找到订单: {order_no} -> Id={result.get('Id')}, OrderNo={result.get('OrderNo')}")
                else:
                    not_found_orders.append(order_no)
                    logger.warning(f"订单未找到: {order_no}")

            # 查询GFS状态并合并到结果中
            gfs_status_map = {}
            try:
                gfs_conn_id = await settings.GFS_CONN_ID()
                if gfs_conn_id:
                    order_no_list = [o["orderNo"] for o in found_orders if o.get("orderNo")]
                    if order_no_list:
                        placeholders = ",".join(["%s"] * len(order_no_list))
                        gfs_sql = f"SELECT OrderNo, ReconcState, InvoiceState, ReceiptState, PromotionState FROM finance_basic.basic_orderinfo WHERE OrderNo IN ({placeholders})"
                        gfs_result = await db_manager.execute_query(gfs_conn_id, gfs_sql, order_no_list)
                        if gfs_result and len(gfs_result) > 1 and gfs_result[1]:
                            for row in gfs_result[1]:
                                gfs_status_map[row.get('OrderNo')] = {
                                    "reconc_state": row.get('ReconcState'),
                                    "invoice_state": row.get('InvoiceState'),
                                    "receipt_state": row.get('ReceiptState'),
                                    "promotion_state": row.get('PromotionState'),
                                }
            except Exception as e:
                logger.warning(f"查询GFS状态失败: {e}")

            # 将GFS状态合并到订单信息中
            for order in found_orders:
                order_no = order.get("orderNo")
                if order_no and order_no in gfs_status_map:
                    order["gfs_status"] = gfs_status_map[order_no]

            return {
                "success": len(not_found_orders) == 0,
                "total_count": len(order_nos),
                "found_count": len(found_orders),
                "not_found_count": len(not_found_orders),
                "foundOrders": found_orders,
                "notFoundIds": not_found_orders,
                "message": f"找到 {len(found_orders)} 条订单，{len(not_found_orders)} 条未找到" if not_found_orders else "所有订单都已找到",
                "connection_name": conn_info['name']
            }

        except Exception as e:
            logger.error(f"验证订单删除时发生错误: {e!s}")
            raise HTTPException(status_code=500, detail=f"验证订单删除失败: {e!s}")

    @staticmethod
    async def batch_update_audit_time(request: OrderUpdateRequest) -> dict[str, Any]:
        """
        批量更新订单审核时间（支持订单编码）
        """
        try:
            order_nos = [oid.strip() for oid in request.order_nos.split(',') if oid.strip()]

            if not order_nos:
                raise HTTPException(status_code=400, detail="订单编码不能为空")

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

            # 先查询订单编码或订单Id对应的Id
            order_no_id_map = {}
            for order_no in order_nos:
                is_numeric = order_no.isdigit()

                # 根据输入类型决定主查和备查
                queries = []
                if is_numeric:
                    doc_id = int(order_no)
                    queries = [
                        ("SELECT Id FROM tb_orderinfo WHERE Id=%s AND Deleted=0 LIMIT 1", (doc_id,)),
                        ("SELECT Id FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                    ]
                else:
                    queries = [
                        ("SELECT Id FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=0 LIMIT 1", (order_no,)),
                        ("SELECT Id FROM tb_orderinfo WHERE Id=%s AND Deleted=0 LIMIT 1", (order_no,)),
                    ]

                # 按优先级逐条查询，找到第一个命中的就停
                result = None
                for sql, params in queries:
                    result = await db_manager.execute_query(request.conn_id, sql, list(params))
                    if result and len(result) > 1 and result[1]:
                        data_list = result[1]
                        if data_list and len(data_list) > 0:
                            order_no_id_map[order_no] = data_list[0].get('Id')
                            logger.info(f"找到订单: {order_no} -> Id={order_no_id_map[order_no]}")
                            break
                    result = None

                if order_no not in order_no_id_map:
                    logger.warning(f"订单未找到: {order_no}")

            for order_no in order_nos:
                order_id = order_no_id_map.get(order_no)
                if not order_id:
                    failed_orders.append({"order_no": order_no, "reason": "订单不存在"})
                    continue

                try:
                    sql = "UPDATE tb_orderinfo SET AuditTime = %s WHERE Id = %s"
                    affected_rows = await db_manager.execute_update(
                        request.conn_id,
                        sql,
                        [formatted_time, order_id]
                    )

                    if affected_rows > 0:
                        updated_orders.append(order_no)
                    else:
                        failed_orders.append({"order_no": order_no, "reason": "更新失败"})

                except Exception as e:
                    failed_orders.append({"order_no": order_no, "reason": str(e)})

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
                    logger.error(f"记录操作日志失败: {e!s}")

            return {
                "success": len(failed_orders) == 0,
                "total_count": len(order_nos),
                "updated_count": len(updated_orders),
                "failed_count": len(failed_orders),
                "updated_orders": updated_orders,
                "failed_orders": failed_orders,
                "connection_name": conn_info['name']
            }

        except Exception as e:
            logger.error(f"批量更新订单审核时间时发生错误: {e!s}")
            raise HTTPException(status_code=500, detail=f"批量更新失败: {e!s}")

    @staticmethod
    async def batch_delete_orders(request: OrderDeleteRequest) -> dict[str, Any]:
        """
        批量删除订单，调用MySQL存储过程（支持订单编码）
        """
        try:
            import uuid

            order_nos = [oid.strip() for oid in request.order_nos.split(',') if oid.strip()]

            if not order_nos:
                raise HTTPException(status_code=400, detail="订单编码不能为空")

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

            # 先查询订单编码或订单Id对应的Id
            order_no_id_map = {}
            for order_no in order_nos:
                is_numeric = order_no.isdigit()

                # 根据输入类型决定主查和备查
                queries = []
                if is_numeric:
                    doc_id = int(order_no)
                    queries = [
                        ("SELECT Id FROM tb_orderinfo WHERE Id=%s AND Deleted=1 LIMIT 1", (doc_id,)),
                        ("SELECT Id FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=1 LIMIT 1", (order_no,)),
                    ]
                else:
                    queries = [
                        ("SELECT Id FROM tb_orderinfo WHERE OrderNo=%s AND Deleted=1 LIMIT 1", (order_no,)),
                        ("SELECT Id FROM tb_orderinfo WHERE Id=%s AND Deleted=1 LIMIT 1", (order_no,)),
                    ]

                # 按优先级逐条查询，找到第一个命中的就停
                result = None
                for sql, params in queries:
                    result = await db_manager.execute_query(request.conn_id, sql, list(params))
                    if result and len(result) > 1 and result[1]:
                        data_list = result[1]
                        if data_list and len(data_list) > 0:
                            order_no_id_map[order_no] = data_list[0].get('Id')
                            logger.info(f"找到订单: {order_no} -> Id={order_no_id_map[order_no]}")
                            break
                    result = None

                if order_no not in order_no_id_map:
                    logger.warning(f"订单未找到: {order_no}")

            # 使用Id执行删除操作
            for order_no in order_nos:
                order_id = order_no_id_map.get(order_no)
                if not order_id:
                    failed_orders.append({
                        "orderId": None,
                        "orderNo": order_no,
                        "deleteTime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "success": False,
                        "message": "订单不存在"
                    })
                    continue

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
                            "orderNo": order_no,
                            "deleteTime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                            "success": True,
                            "message": "删除成功"
                        })
                    else:
                        deleted_orders.append({
                            "orderId": order_id,
                            "orderNo": order_no,
                            "deleteTime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                            "success": True,
                            "message": "删除成功"
                        })

                except Exception as e:
                    failed_orders.append({
                        "orderId": order_id,
                        "orderNo": order_no,
                        "deleteTime": current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "success": False,
                        "message": str(e)
                    })

            if deleted_orders:
                try:
                    oplog_data = {
                        "deleted_orders": [order["orderNo"] for order in deleted_orders],
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
                    logger.error(f"记录操作日志失败: {e!s}")

            return {
                "success": len(failed_orders) == 0,
                "total_count": len(order_nos),
                "deleted_count": len(deleted_orders),
                "failed_count": len(failed_orders),
                "details": deleted_orders + failed_orders,
                "connection_name": conn_info['name']
            }

        except Exception as e:
            logger.error(f"批量删除订单时发生错误: {e!s}")
            raise HTTPException(status_code=500, detail=f"批量删除失败: {e!s}")

    @staticmethod
    async def get_connections() -> list[dict[str, Any]]:
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
    async def refresh_connections() -> dict[str, str]:
        """
        刷新数据库连接池
        """
        try:
            await refresh_dynamic_connections()
            return {"message": "连接池刷新成功"}
        except Exception as e:
            logger.error(f"刷新连接池时发生错误: {e!s}")
            raise HTTPException(status_code=500, detail=f"刷新连接池失败: {e!s}")


oms_controller = OMSController()
