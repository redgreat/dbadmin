from typing import Dict, List, Tuple
import aiomysql

from app.services.db_pool import db_pool
from app.settings.config import settings

# 仓储中心固定连接的Id（延迟获取，避免模块加载时Tortoise未初始化）
_wms_conn_id = None

async def _get_conn_id():
    global _wms_conn_id
    if _wms_conn_id is None:
        _wms_conn_id = await settings.WMS_CONN_ID()
    return _wms_conn_id


class WmsService:
    """仓储中心业务服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        await db_pool.ensure_pool(await _get_conn_id())

    async def validate_stock(self, stock_nos: List[str], validate_type: str, operator_id: str = None) -> Dict:
        """
        验证单据状态，支持传入单据编码或数字Id

        Args:
            stock_nos: 单据编码或数字Id列表
            validate_type: 验证类型 (logical_delete, physical_delete, restore)
            operator_id: 删除人Id（恢复时需要验证）

        Returns:
            验证结果字典
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        found_docs = []
        not_found_docs = []
        invalid_docs = []  # 状态不符合的单据

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for stock_no in stock_nos:
                        is_numeric = stock_no.isdigit()

                        # 根据输入类型决定主查和备查
                        queries = []
                        if is_numeric:
                            doc_id = int(stock_no)
                            queries = [
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'instock' AS doc_type
                                    FROM tb_instockinfohis WHERE Id=%s""", (doc_id,)),
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'outstock' AS doc_type
                                    FROM tb_outstockinfohis WHERE Id=%s""", (doc_id,)),
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'instock' AS doc_type
                                    FROM tb_instockinfohis WHERE InStockNo=%s""", (stock_no,)),
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'outstock' AS doc_type
                                    FROM tb_outstockinfohis WHERE OutStockNo=%s""", (stock_no,)),
                            ]
                        else:
                            queries = [
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'instock' AS doc_type
                                    FROM tb_instockinfohis WHERE InStockNo=%s""", (stock_no,)),
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'outstock' AS doc_type
                                    FROM tb_outstockinfohis WHERE OutStockNo=%s""", (stock_no,)),
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'instock' AS doc_type
                                    FROM tb_instockinfohis WHERE Id=%s""", (stock_no,)),
                                ("""SELECT Id AS stock_id, Deleted AS deleted, DeletedById, 'outstock' AS doc_type
                                    FROM tb_outstockinfohis WHERE Id=%s""", (stock_no,)),
                            ]

                        # 按优先级逐条查询，找到第一个命中的就停
                        result = None
                        for sql, params in queries:
                            await cur.execute(sql, params)
                            row = await cur.fetchone()
                            if row:
                                result = row
                                break

                        if not result:
                            not_found_docs.append(stock_no)
                        else:
                            stock_id, deleted, deleted_by_id, doc_type = result
                            doc_info = {
                                "stock_id": stock_id,
                                "stock_no": stock_no,
                                "deleted": deleted,
                                "deleted_by_id": deleted_by_id,
                                "doc_type": doc_type
                            }

                            if validate_type == "logical_delete":
                                if deleted == 1:
                                    invalid_docs.append({
                                        **doc_info,
                                        "reason": "单据已被逻辑删除，不能再次删除"
                                    })
                                else:
                                    found_docs.append(doc_info)

                            elif validate_type == "physical_delete":
                                found_docs.append(doc_info)

                            elif validate_type == "restore":
                                if deleted == 0:
                                    invalid_docs.append({
                                        **doc_info,
                                        "reason": "单据未被逻辑删除，无需恢复"
                                    })
                                elif operator_id and deleted_by_id != operator_id:
                                    invalid_docs.append({
                                        **doc_info,
                                        "reason": f"删除人不匹配，期望 {operator_id}，实际 {deleted_by_id}"
                                    })
                                else:
                                    found_docs.append(doc_info)
        else:
            raise ValueError("不支持的连接池类型")

        return {
            "success": len(not_found_docs) == 0 and len(invalid_docs) == 0,
            "total_count": len(stock_nos),
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

    async def fetch_stock_ids_by_nos(self, stock_nos: List[str]) -> Dict[str, int]:
        """根据单据编码或数字Id获取对应的stock_id，优先按输入类型匹配"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        result: Dict[str, int] = {}
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for stock_no in stock_nos:
                        is_numeric = stock_no.isdigit()

                        queries = []
                        if is_numeric:
                            doc_id = int(stock_no)
                            queries = [
                                ("SELECT Id FROM tb_instockinfohis WHERE Id=%s LIMIT 1", (doc_id,)),
                                ("SELECT Id FROM tb_outstockinfohis WHERE Id=%s LIMIT 1", (doc_id,)),
                                ("SELECT Id FROM tb_instockinfohis WHERE InStockNo=%s LIMIT 1", (stock_no,)),
                                ("SELECT Id FROM tb_outstockinfohis WHERE OutStockNo=%s LIMIT 1", (stock_no,)),
                            ]
                        else:
                            queries = [
                                ("SELECT Id FROM tb_instockinfohis WHERE InStockNo=%s AND Deleted=0 LIMIT 1", (stock_no,)),
                                ("SELECT Id FROM tb_outstockinfohis WHERE OutStockNo=%s AND Deleted=0 LIMIT 1", (stock_no,)),
                                ("SELECT Id FROM tb_instockinfohis WHERE Id=%s LIMIT 1", (stock_no,)),
                                ("SELECT Id FROM tb_outstockinfohis WHERE Id=%s LIMIT 1", (stock_no,)),
                            ]

                        for sql, params in queries:
                            await cur.execute(sql, params)
                            row = await cur.fetchone()
                            if row:
                                result[stock_no] = row[0]
                                break
        else:
            raise ValueError("不支持的连接池类型")

        return result

    async def delete_logical_batch(self, stock_nos: List[str], operator_id: str) -> Tuple[int, List[str]]:
        """批量逻辑删除单据（逐行调用存储过程）"""
        # 先根据单据编码获取Id
        stock_no_id_map = await self.fetch_stock_ids_by_nos(stock_nos)
        
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        
        for stock_no in stock_nos:
            stock_id = stock_no_id_map.get(stock_no)
            if not stock_id:
                failed.append(stock_no)
                continue
            
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
                failed.append(stock_no)
        return success, failed

    async def delete_physical_batch(self, stock_nos: List[str], operator_id: str) -> Tuple[int, List[str]]:
        """批量物理删除单据（逐行调用存储过程）"""
        # 先根据单据编码获取Id
        stock_no_id_map = await self.fetch_stock_ids_by_nos(stock_nos)
        
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: List[str] = []
        
        for stock_no in stock_nos:
            stock_id = stock_no_id_map.get(stock_no)
            if not stock_id:
                failed.append(stock_no)
                continue
            
            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 调用存储过程：物理删除单据，参数：stock_id
                            await cur.execute("CALL proc_TruncateStockInfoById(%s)", (stock_id,))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(stock_no)
        return success, failed

    async def restore_logical(self, stock_no: str, operator_id: str) -> bool:
        """恢复逻辑删除的单据，支持传入编码或数字Id"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        stock_id = None
        is_numeric = stock_no.isdigit()

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if is_numeric:
                        doc_id = int(stock_no)
                        await cur.execute(
                            "SELECT Id FROM tb_instockinfohis WHERE Id=%s AND Deleted=1 AND DeletedById=%s LIMIT 1",
                            (doc_id, operator_id),
                        )
                        row = await cur.fetchone()
                        if row:
                            stock_id = row[0]
                        else:
                            await cur.execute(
                                "SELECT Id FROM tb_outstockinfohis WHERE Id=%s AND Deleted=1 AND DeletedById=%s LIMIT 1",
                                (doc_id, operator_id),
                            )
                            row = await cur.fetchone()
                            if row:
                                stock_id = row[0]

                    if not stock_id:
                        await cur.execute(
                            "SELECT Id FROM tb_instockinfohis WHERE InStockNo=%s AND Deleted=1 AND DeletedById=%s LIMIT 1",
                            (stock_no, operator_id),
                        )
                        row = await cur.fetchone()
                        if row:
                            stock_id = row[0]
                        else:
                            await cur.execute(
                                "SELECT Id FROM tb_outstockinfohis WHERE OutStockNo=%s AND Deleted=1 AND DeletedById=%s LIMIT 1",
                                (stock_no, operator_id),
                            )
                            row = await cur.fetchone()
                            if row:
                                stock_id = row[0]

                    if not stock_id:
                        raise ValueError(f"未找到单据 {stock_no} 且删除人为 {operator_id} 的已删除单据")

                    await cur.execute("CALL proc_ReDeleteStockInfoById(%s, %s)", (stock_id, operator_id))
                    return True
        else:
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
        pool = db_pool.get_pool(await _get_conn_id())
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
        pool = db_pool.get_pool(await _get_conn_id())
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
