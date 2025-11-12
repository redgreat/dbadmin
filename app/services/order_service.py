from typing import List, Tuple

from app.services.db_connector import db_connector


class OrderService:
    """订单业务服务"""

    async def delete_logical_batch(self, order_ids: List[str]) -> Tuple[int, List[str]]:
        """批量逻辑删除订单"""
        return await db_connector.delete_orders_logical(order_ids)

    async def delete_physical_batch(self, order_ids: List[str]) -> Tuple[int, List[str]]:
        """批量物理删除订单"""
        return await db_connector.delete_orders_physical(order_ids)


order_service = OrderService()

