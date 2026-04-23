from typing import List, Dict, Any, Optional
import aiomysql
import logging
from app.services.db_pool import db_pool
from app.controllers.conn import conn_controller
from app.settings.config import settings

logger = logging.getLogger(__name__)


class SIMTransService:
    """SIM卡同步服务 - 从仓储中心同步数据到SIM卡中心"""

    async def _get_wms_conn_id(self):
        """获取仓储中心连接ID"""
        return await settings.WMS_CONN_ID()

    async def _get_sim_conn_id(self):
        """获取SIM卡中心连接ID"""
        return await settings.SIM_CONN_ID()

    async def validate_receipt_exists(self, receipt_numbers: List[str]) -> Dict[str, Any]:
        """
        验证入库单号在仓储中心是否存在（已完成且未删除）
        
        Args:
            receipt_numbers: 入库单号列表
            
        Returns:
            验证结果
        """
        wms_conn_id = await self._get_wms_conn_id()
        if wms_conn_id == 0:
            raise ValueError("仓储中心数据库连接未配置")

        pool = db_pool.get_pool(wms_conn_id)
        if pool is None:
            raise ValueError("仓储中心连接池不存在")

        not_exists = []
        exists = []

        # 验证仓储单据是否存在
        VALIDATE_SQL = """
        SELECT InStockNo 
        FROM whcenter.tb_instockinfohis 
        WHERE InStockNo = %s AND InStockType = 'IN0' AND Deleted = 0
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
                                exists.append(receipt_no)
                            else:
                                not_exists.append(receipt_no)
                        except Exception as e:
                            logger.error(f"验证入库单 {receipt_no} 失败: {e}")
                            raise ValueError(f"验证入库单 {receipt_no} 失败: {str(e)}")

        return {
            "exists": exists,
            "not_exists": not_exists,
            "total_count": len(receipt_numbers),
            "exists_count": len(exists),
            "not_exists_count": len(not_exists)
        }

    async def check_installed_devices(self, receipt_numbers: List[str]) -> Dict[str, Any]:
        """
        验证是否全部未加装，如果存在已加装设备则返回数量
        
        Args:
            receipt_numbers: 入库单号列表
            
        Returns:
            检查结果
        """
        wms_conn_id = await self._get_wms_conn_id()
        if wms_conn_id == 0:
            raise ValueError("仓储中心数据库连接未配置")

        pool = db_pool.get_pool(wms_conn_id)
        if pool is None:
            raise ValueError("仓储中心连接池不存在")

        # 检查已加装设备数量
        CHECK_INSTALLED_SQL = """
        SELECT COUNT(*) as installed_count
        FROM whcenter.tb_instockinfohis a
        JOIN whcenter.tb_instockdetailhis b
          ON b.InStockId = a.Id AND b.Deleted = 0
        JOIN whcenter.tb_instockno c
          ON c.DetailId = b.Id AND c.Deleted = 0
        WHERE a.Deleted = 0
          AND a.InStockNo IN ({})
          AND NOT EXISTS (
            SELECT 1 FROM tb_materialstock d
            WHERE d.MaterialNo = c.MaterialNo AND d.Deleted = 0
          )
        """

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor(aiomysql.cursors.DictCursor) as cur:
                    # 构建 IN 子句的占位符
                    placeholders = ','.join(['%s'] * len(receipt_numbers))
                    sql = CHECK_INSTALLED_SQL.format(placeholders)
                    
                    await cur.execute(sql, tuple(receipt_numbers))
                    result = await cur.fetchone()
                    
                    installed_count = result['installed_count'] if result else 0
                    
                    return {
                        "has_installed": installed_count > 0,
                        "installed_count": installed_count
                    }

        return {"has_installed": False, "installed_count": 0}

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

        # 步骤1: 验证入库单号是否存在
        logger.info(f"开始验证入库单号: {receipt_numbers}")
        validation_result = await self.validate_receipt_exists(receipt_numbers)
        
        if validation_result['not_exists_count'] > 0:
            not_exists_list = ', '.join(validation_result['not_exists'])
            return {
                "success": False,
                "message": f"以下入库单不存在或状态不正确: {not_exists_list}",
                "validation": validation_result
            }

        valid_receipts = validation_result['exists']
        logger.info(f"入库单号验证通过: {valid_receipts}")

        # 步骤2: 验证是否全部未加装
        logger.info("开始检查设备加装状态")
        installed_check = await self.check_installed_devices(valid_receipts)
        
        if installed_check['has_installed']:
            return {
                "success": False,
                "message": f"有 {installed_check['installed_count']} 条设备已加装，请手动处理",
                "validation": validation_result,
                "installed_check": installed_check
            }

        logger.info("设备加装状态检查通过，全部未加装")

        # 步骤3: 在SIM卡中心执行数据同步（跨库操作）
        logger.info("开始执行数据同步")
        sync_result = await self._execute_sync(valid_receipts)
        
        return {
            "success": True,
            "message": f"同步完成，共写入 {sync_result['sim_card_count']} 张SIM卡",
            "validation": validation_result,
            "installed_check": installed_check,
            "sync_result": sync_result
        }

    async def _execute_sync(self, receipt_numbers: List[str]) -> Dict[str, Any]:
        """
        在SIM卡中心执行数据同步（包含跨库操作）
        
        Args:
            receipt_numbers: 入库单号列表
            
        Returns:
            同步结果统计
        """
        sim_conn_id = await self._get_sim_conn_id()
        if sim_conn_id == 0:
            raise ValueError("SIM卡中心数据库连接未配置")

        pool = db_pool.get_pool(sim_conn_id)
        if pool is None:
            raise ValueError("SIM卡中心连接池不存在")

        placeholders = ','.join(['%s'] * len(receipt_numbers))
        
        # 构建所有INSERT语句
        sql_statements = [
            # 1. 写入 tb_siminfo
            f"""
            INSERT INTO tb_siminfo (
                Id, SIMNumber, SIMSupplierID, SupplierWareHouseId, SIMKinds, SIMType, SIMYears,
                FirstInStockTime, SilentDuration, SIMPackageName, IsInstallment, InstallmentCycle,
                OwnerId, SimSpec, CreatedById, CreatedAt, UpdatedById, UpdatedAt,
                DeletedById, DeletedAt, Deleted, Remark, SilentBeginTime, EnableTime
            )
            SELECT 
                fn_nextval('SI'),
                a.MaterialNo,
                f.SupplierID,
                e.SupplierId AS SupplierWareHouseId,
                1 AS SIMKinds,
                IF(LENGTH(a.MaterialNo)=13, 0, IF(LENGTH(a.MaterialNo)=11, 1, IF(LENGTH(a.MaterialNo)=15, 2, 0))) AS SIMType,
                NULL AS SIMYears,
                d.AuditTime,
                f.SilentDuration,
                NULL AS SIMPackageName,
                NULL AS IsInstallment,
                NULL AS InstallmentCycle,
                a.OwnerId,
                c.SimSpec,
                '203E0000-3E01-0016-3584-08D39E2871A0' AS CreatedById,
                NOW() AS CreatedAt,
                '203E0000-3E01-0016-3584-08D39E2871A0' AS UpdatedById,
                NOW() AS UpdatedAt,
                NULL AS DeletedById,
                NULL AS DeletedAt,
                0 AS Deleted,
                NULL AS Remark,
                DATE_FORMAT(d.AuditTime, '%Y-%m-%d 00:00:00') AS SilentBeginTime,
                NULL AS EnableTime
            FROM whcenter.tb_materialstock a
            JOIN whcenter.tb_instockno b ON b.MaterialNo = a.MaterialNo AND b.Deleted = 0
            JOIN whcenter.tb_instockdetailhis c ON c.Id = b.DetailId AND c.Deleted = 0
            JOIN whcenter.tb_instockinfohis d ON d.Id = c.InStockId AND d.Deleted = 0
            JOIN whcenter.tb_materialinit e ON e.MaterialNo = a.MaterialNo AND e.Deleted = 0
            LEFT JOIN tb_supplierwarehouse f ON f.SupplierWareHouseId = e.SupplierId AND f.SupplierKinds = 1 AND f.Deleted = 0
            WHERE a.Deleted = 0
              AND d.InStockNo IN ({placeholders})
              AND NOT EXISTS (SELECT 1 FROM tb_siminfo g WHERE g.SimNumber = a.MaterialNo)
            """,
            
            # 2. 写入 tb_simstatus
            f"""
            INSERT INTO tb_simstatus (
                Id, SIMNumber, SIMPackage, SIMLifeCycle, SIMStatus, SIMMarkStatus,
                WriteStatus, EnableStatus, SIMDataUseYesterday, CustSettleAccountTime,
                CarUserAccountTime, CustSettleRenewDuration, CarUserRenewDuration,
                CarUserRefundDuration, ExpiryDate, DeviceNumber, ICCID, VirtualICCID,
                LastUpdateTime, ActivationTime, SupplierPackage
            )
            SELECT 
                e.Id,
                e.Simnumber,
                NULL AS SIMPackage,
                1 AS SIMLifeCycle,
                a.StockStatus,
                0 AS SIMMarkStatus,
                NULL AS WriteStatus,
                0 AS EnableStatus,
                0 AS SIMDataUseYesterday,
                NULL AS CustSettleAccountTime,
                NULL AS CarUserAccountTime,
                NULL AS CustSettleRenewDuration,
                NULL AS CarUserRenewDuration,
                NULL AS CarUserRefundDuration,
                NULL AS ExpiryDate,
                NULL AS DeviceNumber,
                NULL AS ICCID,
                NULL AS VirtualICCID,
                NOW() AS LastUpdateTime,
                NULL AS ActivationTime,
                NULL AS SupplierPackage
            FROM whcenter.tb_materialstock a
            JOIN whcenter.tb_instockno b ON b.MaterialNo = a.MaterialNo AND b.Deleted = 0
            JOIN whcenter.tb_instockdetailhis c ON c.Id = b.DetailId AND c.Deleted = 0
            JOIN whcenter.tb_instockinfohis d ON d.Id = c.InStockId AND d.Deleted = 0
            JOIN tb_siminfo e ON e.SimNumber = a.MaterialNo
            WHERE a.Deleted = 0
              AND d.InStockNo IN ({placeholders})
              AND NOT EXISTS (SELECT 1 FROM tb_simstatus g WHERE g.SimNumber = a.MaterialNo)
            """,
            
            # 3. 写入 tb_simwarehouse
            f"""
            INSERT INTO tb_simwarehouse (
                Id, SIMNumber, LocationType, CustSettleId, CustSettleName, WarehouseId,
                WarehouseName, ParentWareHouseId, ParentWareHouseName, ProCode, ProName,
                CityCode, CityName, OutStockTime, ManagerCode, ManagerName,
                IsCardTermAdjust, OperationCode, OperationName, OperationTime, Deleted
            )
            SELECT 
                e.Id,
                e.Simnumber,
                IF(LEFT(a.StockLocationId, 2) = 'WH', 0, 1) AS LocationType,
                a.CustSettleId,
                a.CustSettleName,
                a.StockLocationId,
                a.StockLocationName,
                a.ParentWarehouseId,
                f.Name AS ParentWareHouseName,
                h.ProCode,
                j.Name AS ProName,
                h.CityCode,
                k.Name AS CityName,
                NULL AS OutStockTime,
                i.LoginName AS ManagerCode,
                i.UserName AS ManagerName,
                NULL AS IsCardTermAdjust,
                d.AuditPerson AS OperationCode,
                d.AuditName AS OperationName,
                d.AuditTime AS OperationTime,
                0 AS Deleted
            FROM whcenter.tb_materialstock a
            JOIN whcenter.tb_instockno b ON b.MaterialNo = a.MaterialNo AND b.Deleted = 0
            JOIN whcenter.tb_instockdetailhis c ON c.Id = b.DetailId AND c.Deleted = 0
            JOIN whcenter.tb_instockinfohis d ON d.Id = c.InStockId AND d.Deleted = 0
            JOIN tb_siminfo e ON e.SimNumber = a.MaterialNo
            LEFT JOIN whcenter.tb_warehouse f ON f.Id = a.ParentWarehouseId AND f.Deleted = 0
            LEFT JOIN whcenter.tb_whaddress h ON h.WarehouseId = a.StockLocationId AND h.IsDefault = 1 AND h.Deleted = 0
            LEFT JOIN whcenter.tb_whmanager i ON i.WarehouseId = a.StockLocationId AND i.IsDefault = 1 AND i.ManagerType = 0 AND i.Deleted = 0
            LEFT JOIN basic_district j ON j.Code = h.ProCode AND j.Deleted = 0
            LEFT JOIN basic_district k ON k.Code = h.CityCode AND k.Deleted = 0
            WHERE a.Deleted = 0
              AND d.InStockNo IN ({placeholders})
              AND NOT EXISTS (SELECT 1 FROM tb_simwarehouse g WHERE g.SimNumber = a.MaterialNo)
            """,
            
            # 4. 写入 tb_simfollowinfo
            f"""
            INSERT INTO tb_simfollowinfo (
                SIMId, SIMNumber, SIMLifeCycle, SIMStatus, SIMMarkStatus,
                OperationName, OperationSystem, CreatedByName, CreatedAt, Deleted
            )
            SELECT 
                e.Id,
                e.Simnumber,
                e.SIMLifeCycle,
                e.SIMStatus,
                e.SIMMarkStatus,
                '' AS OperationName,
                2 AS OperationSystem,
                d.AuditName AS CreatedByName,
                d.AuditTime AS CreatedAt,
                0 AS Deleted
            FROM whcenter.tb_materialstock a
            JOIN whcenter.tb_instockno b ON b.MaterialNo = a.MaterialNo AND b.Deleted = 0
            JOIN whcenter.tb_instockdetailhis c ON c.Id = b.DetailId AND c.Deleted = 0
            JOIN whcenter.tb_instockinfohis d ON d.Id = c.InStockId AND d.Deleted = 0
            JOIN tb_simstatus e ON e.SimNumber = a.MaterialNo
            WHERE a.Deleted = 0
              AND d.InStockNo IN ({placeholders})
              AND NOT EXISTS (SELECT 1 FROM tb_simfollowinfo g WHERE g.SimNumber = a.MaterialNo)
            """,
            
            # 5. 写入 tb_simdatauseinfo
            f"""
            INSERT INTO tb_simdatauseinfo (
                Id, SIMId, SIMNumber, SIMSupplierID, SIMUseDataTotal,
                SIMStatus, CheckDate, IsFrozen, Deleted
            )
            SELECT 
                fn_nextval('DU'),
                e.Id,
                a.MaterialNo,
                e.SIMSupplierID,
                0 AS SIMUseDataTotal,
                0 AS SIMStatus,
                CURDATE() AS CheckDate,
                0 AS IsFrozen,
                0 AS Deleted
            FROM whcenter.tb_materialstock a
            JOIN whcenter.tb_instockno b ON b.MaterialNo = a.MaterialNo AND b.Deleted = 0
            JOIN whcenter.tb_instockdetailhis c ON c.Id = b.DetailId AND c.Deleted = 0
            JOIN whcenter.tb_instockinfohis d ON d.Id = c.InStockId AND d.Deleted = 0
            JOIN tb_siminfo e ON e.SimNumber = a.MaterialNo
            WHERE a.Deleted = 0
              AND d.InStockNo IN ({placeholders})
              AND NOT EXISTS (SELECT 1 FROM tb_simdatauseinfo g WHERE g.SIMNumber = a.MaterialNo)
            """
        ]

        total_inserted = 0
        table_names = ['tb_siminfo', 'tb_simstatus', 'tb_simwarehouse', 'tb_simfollowinfo', 'tb_simdatauseinfo']
        inserted_by_table = {}

        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    try:
                        # 开始事务
                        await conn.begin()
                        
                        # 依次执行每个INSERT语句
                        for idx, sql in enumerate(sql_statements):
                            try:
                                await cur.execute(sql, tuple(receipt_numbers))
                                affected = cur.rowcount or 0
                                total_inserted += affected
                                inserted_by_table[table_names[idx]] = affected
                                logger.info(f"写入 {table_names[idx]}: {affected} 条")
                            except Exception as e:
                                logger.error(f"写入 {table_names[idx]} 失败: {e}")
                                await conn.rollback()
                                raise ValueError(f"写入 {table_names[idx]} 失败: {str(e)}")
                        
                        # 提交事务
                        await conn.commit()
                        logger.info(f"数据同步完成，总计写入: {total_inserted} 条")
                        
                    except Exception as e:
                        await conn.rollback()
                        logger.error(f"数据同步失败: {e}")
                        raise

        return {
            "total_inserted": total_inserted,
            "sim_card_count": inserted_by_table.get('tb_siminfo', 0),
            "inserted_by_table": inserted_by_table
        }


sim_trans_service = SIMTransService()
