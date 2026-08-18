import logging

import aiomysql

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

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

    async def validate_stock(self, stock_nos: list[str], validate_type: str, operator_id: str = None) -> dict:
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
            async with pool.acquire() as conn, conn.cursor() as cur:
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

    async def fetch_stock_ids_by_nos(self, stock_nos: list[str]) -> dict[str, int]:
        """根据单据编码或数字Id获取对应的stock_id，优先按输入类型匹配"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        result: dict[str, int] = {}
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

    async def delete_logical_batch(self, stock_nos: list[str], operator_id: str) -> tuple[int, list[str]]:
        """批量逻辑删除单据（逐行调用存储过程）"""
        # 先根据单据编码获取Id
        stock_no_id_map = await self.fetch_stock_ids_by_nos(stock_nos)

        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: list[str] = []

        for stock_no in stock_nos:
            stock_id = stock_no_id_map.get(stock_no)
            if not stock_id:
                failed.append(stock_no)
                continue

            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn, conn.cursor() as cur:
                        # 调用存储过程：逻辑删除单据，参数：stock_id, operator_id
                        await cur.execute("CALL proc_DeleteStockInfoById(%s, %s)", (stock_id, operator_id))
                else:
                    raise ValueError("不支持的连接池类型")
                success += 1
            except Exception:
                failed.append(stock_no)
        return success, failed

    async def delete_physical_batch(self, stock_nos: list[str], operator_id: str) -> tuple[int, list[str]]:
        """批量物理删除单据（逐行调用存储过程）"""
        # 先根据单据编码获取Id
        stock_no_id_map = await self.fetch_stock_ids_by_nos(stock_nos)

        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")
        success = 0
        failed: list[str] = []

        for stock_no in stock_nos:
            stock_id = stock_no_id_map.get(stock_no)
            if not stock_id:
                failed.append(stock_no)
                continue

            try:
                if isinstance(pool, aiomysql.Pool):
                    async with pool.acquire() as conn, conn.cursor() as cur:
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

    async def query_price(self, stock_code: str, material_name: str, new_price: str) -> list[dict]:
        """
        查询价格信息，支持入库单和出库单

        Args:
            stock_code: 单据编码（入库单或出库单）
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
            async with pool.acquire() as conn, conn.cursor() as cur:
                # 先尝试查询入库单
                sql_instock = """
                        SELECT b.Id AS detail_id,b.MaterialName AS material_name,
                        b.InStockPrice AS original_price,b.InStockedNum AS instocked_num,
                        'instock' AS doc_type
                        FROM tb_instockinfohis a
                        JOIN tb_instockdetailhis b
                          ON b.InStockId=a.Id
                          AND b.MaterialName LIKE %s
                          AND b.Deleted=0
                        WHERE a.InStockNo=%s
                          AND a.Deleted=0;
                    """
                params = [f"%{material_name}%", stock_code]
                await cur.execute(sql_instock, params)
                rows = await cur.fetchall()

                for row in rows:
                    results.append({
                        "detail_id": str(row[0]),
                        "material_name": str(row[1]),
                        "original_price": str(row[2]),
                        "instocked_num": str(row[3]) if row[3] is not None else "0",
                        "doc_type": row[4],
                        "new_price": new_price
                    })

                # 如果入库单没查到，尝试查询出库单
                if not results:
                    sql_outstock = """
                            SELECT b.Id AS detail_id,b.MaterialName AS material_name,
                            b.OutStockPrice AS original_price,b.OutStockedNum AS instocked_num,
                            'outstock' AS doc_type
                            FROM tb_outstockinfohis a
                            JOIN tb_outstockdetailhis b
                              ON b.OutStockId=a.Id
                              AND b.MaterialName LIKE %s
                              AND b.Deleted=0
                            WHERE a.OutStockNo=%s
                              AND a.Deleted=0;
                        """
                    await cur.execute(sql_outstock, params)
                    rows = await cur.fetchall()

                    for row in rows:
                        results.append({
                            "detail_id": str(row[0]),
                            "material_name": str(row[1]),
                            "original_price": str(row[2]),
                            "instocked_num": str(row[3]) if row[3] is not None else "0",
                            "doc_type": row[4],
                            "new_price": new_price
                        })
        else:
            raise ValueError("不支持的连接池类型")

        return results

    async def validate_owing_status(self, stock_id: str) -> dict:
        """验证应付单是否对账，有记录时ReconcStatus必须为0"""
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn, conn.cursor() as cur:
                # 查询应付单
                sql_owing = "SELECT ReconcStatus FROM whcenter.tb_owinginfo WHERE StockId=%s LIMIT 1"
                await cur.execute(sql_owing, (stock_id,))
                row = await cur.fetchone()
                if row:
                    reconc_status = row[0]
                    if reconc_status != 0:
                        return {
                            "success": False,
                            "message": f"应付单已对账，ReconcStatus={ReconcStatus}（需为0未对账）",
                            "reconc_status": reconc_status,
                        }
                    return {"success": True, "message": "应付单未对账，允许修改", "reconc_status": reconc_status}

                # 查询应付单历史
                sql_owing_his = "SELECT ReconcStatus FROM whcenter.tb_owinginfohis WHERE StockId=%s LIMIT 1"
                await cur.execute(sql_owing_his, (stock_id,))
                row = await cur.fetchone()
                if row:
                    reconc_status = row[0]
                    if reconc_status != 0:
                        return {
                            "success": False,
                            "message": f"应付单历史已对账，ReconcStatus={ReconcStatus}（需为0未对账）",
                            "reconc_status": reconc_status,
                        }
                    return {"success": True, "message": "应付单历史未对账，允许修改", "reconc_status": reconc_status}

                return {"success": True, "message": "无应付单记录，允许修改", "reconc_status": None}
        else:
            raise ValueError("不支持的连接池类型")

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
            async with pool.acquire() as conn, conn.cursor() as cur:
                # TODO: 请根据实际业务需求修改存储过程名称和参数
                # 调用存储过程：修改价格，参数：detail_id, new_price
                await cur.execute("CALL proc_StockPriceChange(%s, %s)", (detail_id, new_price))
                return True
        else:
            raise ValueError("不支持的连接池类型")

    async def query_stock_status(self, stock_nos: list[str]) -> dict:
        """查询单据状态信息，返回Id、单号、AuditTime、Deleted、DeletedById、DeletedAt，并关联OA获取删除人姓名"""
        from app.services.user_service import user_service

        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        found_docs = []
        not_found_docs = []

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for stock_no in stock_nos:
                        is_numeric = stock_no.isdigit()
                        queries = []
                        if is_numeric:
                            doc_id = int(stock_no)
                            queries = [
                                ("SELECT Id, InStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'instock' AS doc_type FROM tb_instockinfohis WHERE Id=%s LIMIT 1", (doc_id,)),
                                ("SELECT Id, OutStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'outstock' AS doc_type FROM tb_outstockinfohis WHERE Id=%s LIMIT 1", (doc_id,)),
                                ("SELECT Id, InStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'instock' AS doc_type FROM tb_instockinfohis WHERE InStockNo=%s LIMIT 1", (stock_no,)),
                                ("SELECT Id, OutStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'outstock' AS doc_type FROM tb_outstockinfohis WHERE OutStockNo=%s LIMIT 1", (stock_no,)),
                            ]
                        else:
                            queries = [
                                ("SELECT Id, InStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'instock' AS doc_type FROM tb_instockinfohis WHERE InStockNo=%s LIMIT 1", (stock_no,)),
                                ("SELECT Id, OutStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'outstock' AS doc_type FROM tb_outstockinfohis WHERE OutStockNo=%s LIMIT 1", (stock_no,)),
                                ("SELECT Id, InStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'instock' AS doc_type FROM tb_instockinfohis WHERE Id=%s LIMIT 1", (stock_no,)),
                                ("SELECT Id, OutStockNo, AuditTime, Deleted, DeletedById, DeletedAt, 'outstock' AS doc_type FROM tb_outstockinfohis WHERE Id=%s LIMIT 1", (stock_no,)),
                            ]

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
                            doc_type = result[6]
                            stock_no_actual = result[1]
                            found_docs.append({
                                "id": str(result[0]),
                                "stock_no": str(stock_no_actual) if stock_no_actual else stock_no,
                                "doc_type": doc_type,
                                "audit_time": str(result[2]) if result[2] else "",
                                "deleted": result[3],
                                "deleted_by_id": str(result[4]) if result[4] else "",
                                "deleted_at": str(result[5]) if result[5] else "",
                            })
        else:
            raise ValueError("不支持的连接池类型")

        deleted_by_ids = [doc["deleted_by_id"] for doc in found_docs if doc["deleted_by_id"]]
        user_map = {}
        if deleted_by_ids:
            try:
                user_map = await user_service.batch_get_by_user_center_ids(deleted_by_ids)
            except Exception as e:
                logger.warning(f"获取删除人信息失败: {e}")

        # 降级：OA 查不到的 ID，尝试从本库 user 表查询 DisplayName
        unmatched_ids = [did for did in deleted_by_ids if did not in user_map]
        if unmatched_ids:
            try:
                local_map = await user_service.get_local_user_display_names(unmatched_ids)
                for did, display_name in local_map.items():
                    user_map[did] = {"user_name": display_name, "code": "", "user_center_user_id": did}
            except Exception as e:
                logger.warning(f"本库用户查询降级失败: {e}")

        for doc in found_docs:
            u = user_map.get(doc["deleted_by_id"], {})
            doc["deleted_by_name"] = u.get("user_name", "")
            doc["deleted_by_code"] = u.get("code", "")

        parts = []
        if found_docs:
            parts.append(f"找到 {len(found_docs)} 条")
        if not_found_docs:
            parts.append(f"{len(not_found_docs)} 条不存在")
        message = "，".join(parts) if parts else "查询完成"

        return {
            "success": len(not_found_docs) == 0,
            "total_count": len(stock_nos),
            "found_count": len(found_docs),
            "not_found_count": len(not_found_docs),
            "found_docs": found_docs,
            "not_found_docs": not_found_docs,
            "message": message,
        }


    async def query_owing_status(self, out_stock_no: str = "", stock_id: str = "") -> dict:
        """
        查询出库单应收状态，先查tb_outstockinfo，查不到再查tb_outstockinfohis

        Args:
            out_stock_no: 出库单号
            stock_id: 出库单ID

        Returns:
            查询结果字典，包含数据来源表名
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        if not out_stock_no and not stock_id:
            return {"success": False, "message": "请输入出库单号或ID", "data": None}

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 构建查询条件
                    condition_parts = []
                    params = []
                    if out_stock_no:
                        condition_parts.append("OutStockNo=%s")
                        params.append(out_stock_no)
                    if stock_id:
                        if condition_parts:
                            condition_parts.append("OR")
                        condition_parts.append("Id=%s")
                        params.append(stock_id)
                    where_clause = ' '.join(condition_parts)

                    # 先查tb_outstockinfo，查不到再查tb_outstockinfohis
                    tables = [("tb_outstockinfo", "main"), ("tb_outstockinfohis", "his")]
                    row = None
                    source_table = None

                    for table_name, table_type in tables:
                        sql = f"""
                            SELECT Id, OutStockNo,
                                   fn_GetStockTypeById(OutStockType) AS OutStockType,
                                   WarehouseName, ToWarehouseName,
                                   AuditTime, IsReceive
                            FROM {table_name}
                            WHERE ({where_clause}) AND Deleted=0
                            LIMIT 1
                        """
                        await cur.execute(sql, params)
                        row = await cur.fetchone()
                        if row:
                            source_table = table_type
                            break

                    if not row:
                        return {"success": False, "message": "未找到该出库单", "data": None}

                    return {
                        "success": True,
                        "message": "查询成功",
                        "data": {
                            "id": str(row[0]),
                            "out_stock_no": str(row[1]) if row[1] else "",
                            "out_stock_type": str(row[2]) if row[2] else "",
                            "warehouse_name": str(row[3]) if row[3] else "",
                            "to_warehouse_name": str(row[4]) if row[4] else "",
                            "audit_time": str(row[5]) if row[5] else "",
                            "is_receive": row[6] if row[6] is not None else 0,
                            "source_table": source_table,
                        }
                    }
        else:
            raise ValueError("不支持的连接池类型")

    async def update_receive_status(self, stock_id: str, is_receive: int, operator_id: str, source_table: str = "main") -> dict:
        """
        修改出库单应收状态

        Args:
            stock_id: 出库单ID
            is_receive: 应收状态: 0-未收, 1-已收
            operator_id: 修改人Id
            source_table: 数据来源表 main-主表, his-历史表

        Returns:
            修改结果字典
        """
        await self._ensure_pool()
        pool = db_pool.get_pool(await _get_conn_id())
        if pool is None:
            raise ValueError("连接池不存在")

        # 根据来源表选择对应的表名
        table_name = "tb_outstockinfo" if source_table == "main" else "tb_outstockinfohis"

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # 更新IsReceive字段，同时记录修改人和更新时间
                    sql = f"""
                        UPDATE {table_name}
                        SET IsReceive=%s,
                            ModifiedById=%s,
                            ModifiedTime=NOW()
                        WHERE Id=%s AND Deleted=0
                    """
                    await cur.execute(sql, (is_receive, operator_id, stock_id))

                    if cur.rowcount > 0:
                        return {"success": True, "message": "修改成功"}
                    else:
                        return {"success": False, "message": "未找到该出库单或无需修改"}
        else:
            raise ValueError("不支持的连接池类型")


wms_service = WmsService()
