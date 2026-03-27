from typing import Dict, List, Optional, Tuple
import aiomysql

from app.services.db_pool import db_pool
from app.controllers.conn import conn_controller
from app.settings.config import settings

# 仓储中心固定连接的Id（需要用户配置）
conn_id = settings.WMS_CONN_ID


class WmsService:
    """仓储中心业务服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        pool = db_pool.get_pool(conn_id)
        if pool is not None:
            return
        conn = await conn_controller.get_decrypted_connection(conn_id)
        if not conn:
            raise ValueError("连接池不存在")
        await db_pool.register_pool(
            conn_id=conn["id"],
            db_type=conn["db_type"],
            host=conn["host"],
            port=conn["port"],
            username=conn["username"],
            password=conn["password"],
            database=conn["database"],
            params=conn["params"],
        )

    async def validate_stock(self, stock_ids: List[str], validate_type: str) -> Dict:
        """
        验证单据状态

        Args:
            stock_ids: 单据ID列表
            validate_type: 验证类型 (logical_delete, physical_delete, restore)

        Returns:
            验证结果字典
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")

        found_docs = []
        not_found_docs = []
        invalid_docs = []  # 状态不符合的单据

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for stock_id in stock_ids:
                        # 使用UNION ALL查询多个表,统一字段名为 stock_id 和 deleted
                        # 添加 table_name 字段标识来自哪个表
                        sql = """
                            SELECT Id AS stock_id, Deleted AS deleted, 'tb_instockinfohis' AS table_name
                            FROM tb_instockinfohis WHERE Id = %s
                            UNION ALL
                            SELECT Id AS stock_id, Deleted AS deleted, 'tb_outstockinfohis' AS table_name
                            FROM tb_outstockinfohis WHERE Id = %s
                            UNION ALL
                            SELECT Id AS stock_id, Deleted AS deleted, 'tb_instockinfo' AS table_name
                            FROM tb_instockinfohis WHERE Id = %s
                            UNION ALL
                            SELECT Id AS stock_id, Deleted AS deleted, 'tb_outstockinfo' AS table_name
                            FROM tb_outstockinfohis WHERE Id = %s
                            LIMIT 1
                        """
                        await cur.execute(sql, (stock_id, stock_id, stock_id, stock_id))
                        result = await cur.fetchone()

                        if result:
                            stock_id_db, deleted, table_name = result
                            doc_info = {
                                "stock_id": stock_id_db,
                                "deleted": deleted,
                                "table_name": table_name
                            }

                            if validate_type == "logical_delete":
                                # 逻辑删除：验证Deleted是否为0
                                if deleted == 1:
                                    invalid_docs.append({
                                        **doc_info,
                                        "reason": "单据已被逻辑删除，不能再次删除"
                                    })
                                else:
                                    found_docs.append(doc_info)

                            elif validate_type == "physical_delete":
                                # 物理删除：只验证是否存在
                                found_docs.append(doc_info)

                            elif validate_type == "restore":
                                # 恢复：验证Deleted是否为1
                                if deleted == 0:
                                    invalid_docs.append({
                                        **doc_info,
                                        "reason": "单据未被逻辑删除，无需恢复"
                                    })
                                else:
                                    found_docs.append(doc_info)
                        else:
                            not_found_docs.append(stock_id)
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(not_found_docs) == 0 and len(invalid_docs) == 0,
            "total_count": len(stock_ids),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "invalid_count": len(invalid_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "invalid_docs": invalid_docs,
            "message": self._build_validation_message(
                len(found_docs), len(not_found_docs), len(invalid_docs), validate_type
            )
        }

    def _build_validation_message(
        self, found_count: int, not_found_count: int, invalid_count: int, validate_type: str
    ) -> str:
        """构建验证消息"""
        type_names = {
            "logical_delete": "逻辑删除",
            "physical_delete": "物理删除",
            "restore": "恢复"
        }
        type_name = type_names.get(validate_type, "操作")

        parts = []
        if found_count > 0:
            parts.append(f"可{type_name} {found_count} 条")
        if not_found_count > 0:
            parts.append(f"{not_found_count} 条单据不存在")
        if invalid_count > 0:
            parts.append(f"{invalid_count} 条单据状态不符合")

        return "，".join(parts) if parts else f"所有单据均可{type_name}"

    async def delete_logical_batch(self, stock_ids: List[str], operator_id: str) -> Tuple[int, List[str]]:
        """批量逻辑删除单据（逐行调用存储过程）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        for stock_id in stock_ids:
            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 调用存储过程：逻辑删除单据，参数：stock_id, operator_id
                            await cur.execute("CALL proc_DeleteStockInfoById(%s, %s)", (stock_id, operator_id))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(str(stock_id))
        return success, failed

    async def delete_physical_batch(self, stock_ids: List[str], operator_id: str) -> Tuple[int, List[str]]:
        """批量物理删除单据（逐行调用存储过程）"""
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        for stock_id in stock_ids:
            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 调用存储过程：物理删除单据，参数：stock_id, operator_id
                            await cur.execute("CALL proc_TruncateStockInfoById(%s, %s)", (stock_id, operator_id))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(str(stock_id))
        return success, failed

    async def restore_logical(self, stock_id: str, operator_id: str) -> bool:
        """恢复逻辑删除的单据"""
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 调用存储过程：恢复单据，参数：stock_id, operator_id
                    await cur.execute("CALL proc_ReDeleteStockInfoById(%s, %s)", (stock_id, operator_id))
                    return True
        raise ValueError("不支持的连接池类型")

    async def query_price(self, stock_code: str, material_name: str, new_price: str) -> List[Dict]:
        """
        查询价格信息

        Args:
            stock_code: 入库单编码
            material_name: 物料名称
            new_price: 修改后价格

        Returns:
            查询结果列表
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")

        results = []
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # TODO: 请根据实际业务需求修改SQL查询语句
                    # 示例SQL：根据入库单编码、物料名称、修改后价格查询明细信息
                    sql = """
                        SELECT b.Id AS detail_id,b.MaterialName AS material_name,
                        b.InStockPrice AS original_price
                        FROM tb_instockinfohis a
                        JOIN tb_instockdetailhis b
                          ON b.InStockId=a.Id
                          AND b.MaterialName LIKE %s
                          AND b.Deleted=0
                        WHERE a.InStockNo=%s
                          AND a.Deleted=0;
                    """
                    params = [f"%{material_name}%", stock_code]
                    
                    await cur.execute(sql, params)
                    rows = await cur.fetchall()
                    
                    for row in rows:
                        results.append({
                            "detail_id": str(row[0]),
                            "material_name": str(row[1]),
                            "original_price": str(row[2]),
                            "new_price": new_price
                        })
        else:
            raise ValueError("不支持的连接池类型")

        return results

    async def modify_price(self, detail_id: str, new_price: str) -> bool:
        """
        修改价格

        Args:
            detail_id: 明细Id
            new_price: 修改后价格

        Returns:
            是否修改成功
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # TODO: 请根据实际业务需求修改存储过程名称和参数
                    # 调用存储过程：修改价格，参数：detail_id, new_price
                    await cur.execute("CALL proc_StockPriceChange(%s, %s)", (detail_id, new_price))
                    return True
        else:
            raise ValueError("不支持的连接池类型")


wms_service = WmsService()
