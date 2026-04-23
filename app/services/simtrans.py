from typing import List, Dict, Any, Optional
import aiomysql
from app.services.db_pool import db_pool
from app.controllers.conn import conn_controller
from app.settings.config import settings


class SIMTransService:
    """SIM卡同步服务 - 从仓储中心同步数据到SIM卡中心"""

    async def _get_wms_conn_id(self):
        """获取仓储中心连接ID"""
        return await settings.WMS_CONN_ID()

    async def _get_sim_conn_id(self):
        """获取SIM卡中心连接ID"""
        return await settings.SIM_CONN_ID()

    async def validate_receipt_numbers(self, receipt_numbers: List[str]) -> Dict[str, Any]:
        """
        验证入库单号在仓储中心是否存在已完成单据
        
        Args:
            receipt_numbers: 入库单号列表
            
        Returns:
            验证结果，包含有效和无效的入库单号
        """
        wms_conn_id = await self._get_wms_conn_id()
        if wms_conn_id == 0:
            raise ValueError("仓储中心数据库连接未配置")

        pool = db_pool.get_pool(wms_conn_id)
        if pool is None:
            raise ValueError("仓储中心连接池不存在")

        valid_receipts = []
        invalid_receipts = []

        # TODO: 替换为实际的验证SQL
        # 以下为占位SQL，请根据实际情况修改
        VALIDATE_SQL = """
        SELECT receipt_no, status 
        FROM wms_receipt 
        WHERE receipt_no = %s AND status = 'COMPLETED'
        """

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.cursors.DictCursor) as cur:
                    for receipt_no in receipt_numbers:
                        receipt_no = receipt_no.strip()
                        if not receipt_no:
                            continue
                        
                        try:
                            await cur.execute(VALIDATE_SQL, (receipt_no,))
                            result = await cur.fetchone()
                            
                            if result:
                                valid_receipts.append(receipt_no)
                            else:
                                invalid_receipts.append({
                                    "receipt_no": receipt_no,
                                    "reason": "入库单不存在或状态不是已完成"
                                })
                        except Exception as e:
                            invalid_receipts.append({
                                "receipt_no": receipt_no,
                                "reason": f"查询失败: {str(e)}"
                            })

        return {
            "valid_receipts": valid_receipts,
            "invalid_receipts": invalid_receipts,
            "total_count": len(receipt_numbers),
            "valid_count": len(valid_receipts),
            "invalid_count": len(invalid_receipts)
        }

    async def fetch_data_from_wms(self, receipt_numbers: List[str]) -> List[Dict[str, Any]]:
        """
        从仓储中心抓取数据
        
        Args:
            receipt_numbers: 入库单号列表
            
        Returns:
            抓取到的数据列表
        """
        wms_conn_id = await self._get_wms_conn_id()
        if wms_conn_id == 0:
            raise ValueError("仓储中心数据库连接未配置")

        pool = db_pool.get_pool(wms_conn_id)
        if pool is None:
            raise ValueError("仓储中心连接池不存在")

        all_data = []

        # TODO: 替换为实际的数据抓取SQL
        # 以下为占位SQL，请根据实际情况修改
        FETCH_SQL = """
        SELECT 
            receipt_no,
            sim_number,
            iccid,
            create_time
        FROM wms_receipt_detail
        WHERE receipt_no = %s
        """

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.cursors.DictCursor) as cur:
                    for receipt_no in receipt_numbers:
                        receipt_no = receipt_no.strip()
                        if not receipt_no:
                            continue
                        
                        try:
                            await cur.execute(FETCH_SQL, (receipt_no,))
                            results = await cur.fetchall()
                            all_data.extend(results)
                        except Exception as e:
                            raise ValueError(f"抓取入库单 {receipt_no} 数据失败: {str(e)}")

        return all_data

    async def write_data_to_sim(self, data_list: List[Dict[str, Any]]) -> int:
        """
        将数据写入SIM卡中心
        
        Args:
            data_list: 要写入的数据列表
            
        Returns:
            写入的记录数
        """
        sim_conn_id = await self._get_sim_conn_id()
        if sim_conn_id == 0:
            raise ValueError("SIM卡中心数据库连接未配置")

        pool = db_pool.get_pool(sim_conn_id)
        if pool is None:
            raise ValueError("SIM卡中心连接池不存在")

        if not data_list:
            return 0

        # TODO: 替换为实际的数据写入SQL
        # 以下为占位SQL，请根据实际情况修改
        INSERT_SQL = """
        INSERT INTO sim_card_data 
        (receipt_no, sim_number, iccid, sync_time)
        VALUES (%s, %s, %s, NOW())
        """

        total_inserted = 0

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for data in data_list:
                        try:
                            await cur.execute(
                                INSERT_SQL,
                                (
                                    data.get('receipt_no'),
                                    data.get('sim_number'),
                                    data.get('iccid'),
                                )
                            )
                            total_inserted += 1
                        except Exception as e:
                            raise ValueError(f"写入数据失败: {str(e)}")
                    
                    await conn.commit()

        return total_inserted

    async def sync_sim_cards(self, receipt_numbers_text: str) -> Dict[str, Any]:
        """
        执行SIM卡同步流程
        
        Args:
            receipt_numbers_text: 入库单号文本，换行分隔
            
        Returns:
            同步结果
        """
        # 解析入库单号
        receipt_numbers = [
            rn.strip() 
            for rn in receipt_numbers_text.split('\n') 
            if rn.strip()
        ]

        if not receipt_numbers:
            raise ValueError("请输入至少一个入库单号")

        # 步骤1: 验证入库单号
        validation_result = await self.validate_receipt_numbers(receipt_numbers)
        
        if not validation_result['valid_receipts']:
            return {
                "success": False,
                "message": "所有入库单号验证失败",
                "validation": validation_result
            }

        # 步骤2: 从仓储中心抓取数据
        wms_data = await self.fetch_data_from_wms(validation_result['valid_receipts'])
        
        if not wms_data:
            return {
                "success": False,
                "message": "未抓取到任何数据",
                "validation": validation_result
            }

        # 步骤3: 写入SIM卡中心
        inserted_count = await self.write_data_to_sim(wms_data)

        return {
            "success": True,
            "message": f"同步完成，共写入 {inserted_count} 条记录",
            "validation": validation_result,
            "fetched_count": len(wms_data),
            "inserted_count": inserted_count
        }


sim_trans_service = SIMTransService()
