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
        FROM tb_instockinfohis
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
        FROM tb_instockinfohis a
        JOIN tb_instockdetailhis b
          ON b.InStockId = a.Id AND b.Deleted = 0
        JOIN tb_instockno c
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

        # 步骤3: 在WMS_CONN执行数据同步
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
        执行数据同步 - 先从WMS_CONN查询仓储数据，取回结果再写入SIM_CONN

        Args:
            receipt_numbers: 入库单号列表

        Returns:
            同步结果统计
        """
        wms_conn_id = await self._get_wms_conn_id()
        sim_conn_id = await self._get_sim_conn_id()
        if wms_conn_id == 0:
            raise ValueError("仓储中心数据库连接未配置")
        if sim_conn_id == 0:
            raise ValueError("SIM卡中心数据库连接未配置")

        wms_pool = db_pool.get_pool(wms_conn_id)
        sim_pool = db_pool.get_pool(sim_conn_id)
        if wms_pool is None:
            raise ValueError("仓储中心连接池不存在")
        if sim_pool is None:
            raise ValueError("SIM卡中心连接池不存在")

        inserted_by_table = {}
        placeholders = ','.join(['%s'] * len(receipt_numbers))

        # ══════════════════════════════════════════════════════════
        # Step 1: 从 WMS_CONN 查询 whcenter 源数据
        # ══════════════════════════════════════════════════════════
        wms_query = f"""
            SELECT a.MaterialNo, a.OwnerId, a.StockStatus,
                   a.StockLocationId, a.StockLocationName, a.CustSettleId, a.CustSettleName,
                   a.ParentWarehouseId,
                   c.SimSpec,
                   d.AuditTime, d.AuditPerson, d.AuditName,
                   e.SupplierId,
                   f.Name AS WHName,
                   h.ProCode, h.CityCode,
                   i.LoginName, i.UserName
            FROM tb_materialstock a
            JOIN tb_instockno b ON b.MaterialNo = a.MaterialNo AND b.Deleted = 0
            JOIN tb_instockdetailhis c ON c.Id = b.DetailId AND c.Deleted = 0
            JOIN tb_instockinfohis d ON d.Id = c.InStockId AND d.Deleted = 0
            JOIN tb_materialinit e ON e.MaterialNo = a.MaterialNo AND e.Deleted = 0
            LEFT JOIN tb_warehouse f ON f.Id = a.ParentWarehouseId AND f.Deleted = 0
            LEFT JOIN tb_whaddress h ON h.WarehouseId = a.StockLocationId AND h.IsDefault = 1 AND h.Deleted = 0
            LEFT JOIN tb_whmanager i ON i.WarehouseId = a.StockLocationId AND i.IsDefault = 1 AND i.ManagerType = 0 AND i.Deleted = 0
            WHERE a.Deleted = 0 AND d.InStockNo IN ({placeholders})
        """

        async with wms_pool.acquire() as wms_conn:
            async with wms_conn.cursor(aiomysql.cursors.DictCursor) as wms_cur:
                await wms_cur.execute(wms_query, tuple(receipt_numbers))
                whcenter_rows = await wms_cur.fetchall()

        if not whcenter_rows:
            logger.info("未查询到仓储数据，跳过同步")
            return {"total_inserted": 0, "sim_card_count": 0, "inserted_by_table": {}}

        material_nos = [r['MaterialNo'] for r in whcenter_rows]
        mat_ph = ','.join(['%s'] * len(material_nos))
        logger.info(f"从WMS_CONN查询到 {len(whcenter_rows)} 条仓储记录")

        # ══════════════════════════════════════════════════════════
        # Step 2: 从 SIM_CONN 获取辅助数据
        # ══════════════════════════════════════════════════════════
        async with sim_pool.acquire() as sim_conn:
            async with sim_conn.cursor(aiomysql.cursors.DictCursor) as sim_cur:
                # 2a. tb_supplierwarehouse (SIMCENTER表，LEFT JOIN用)
                await sim_cur.execute(
                    "SELECT SupplierWareHouseId, SupplierID, SilentDuration "
                    "FROM tb_supplierwarehouse WHERE SupplierKinds = 1 AND Deleted = 0"
                )
                supplier_wh = {r['SupplierWareHouseId']: r for r in await sim_cur.fetchall()}

                # 2b. basic_district (SIMCENTER表，LEFT JOIN用)
                all_codes = set()
                for r in whcenter_rows:
                    if r.get('ProCode'):
                        all_codes.add(r['ProCode'])
                    if r.get('CityCode'):
                        all_codes.add(r['CityCode'])
                district_map = {}
                if all_codes:
                    code_ph = ','.join(['%s'] * len(all_codes))
                    await sim_cur.execute(
                        f"SELECT Code, Name FROM basic_district WHERE Code IN ({code_ph}) AND Deleted = 0",
                        tuple(all_codes)
                    )
                    for r in await sim_cur.fetchall():
                        district_map[r['Code']] = r['Name']

                # 2c. 各目标表中已有的 SimNumber
                await sim_cur.execute(
                    f"SELECT SimNumber, Id, SIMSupplierID FROM tb_siminfo WHERE SimNumber IN ({mat_ph})",
                    tuple(material_nos)
                )
                existing_siminfo = {r['SimNumber']: r for r in await sim_cur.fetchall()}

                await sim_cur.execute(
                    f"SELECT SimNumber FROM tb_simstatus WHERE SimNumber IN ({mat_ph})",
                    tuple(material_nos)
                )
                existing_simstatus = {r['SimNumber'] for r in await sim_cur.fetchall()}

                await sim_cur.execute(
                    f"SELECT SimNumber FROM tb_simwarehouse WHERE SimNumber IN ({mat_ph})",
                    tuple(material_nos)
                )
                existing_simwarehouse = {r['SimNumber'] for r in await sim_cur.fetchall()}

                await sim_cur.execute(
                    f"SELECT SimNumber FROM tb_simfollowinfo WHERE SimNumber IN ({mat_ph})",
                    tuple(material_nos)
                )
                existing_simfollowinfo = {r['SimNumber'] for r in await sim_cur.fetchall()}

                await sim_cur.execute(
                    f"SELECT SimNumber FROM tb_simdatauseinfo WHERE SIMNumber IN ({mat_ph})",
                    tuple(material_nos)
                )
                existing_simdatauseinfo = {r['SimNumber'] for r in await sim_cur.fetchall()}

                # ══════════════════════════════════════════════════
                # Step 3: 在 SIM_CONN 上写入（事务内）
                # ══════════════════════════════════════════════════
                await sim_conn.begin()
                try:
                    siminfo_new = {}          # MaterialNo -> Id
                    siminfo_supplier = {}     # MaterialNo -> SIMSupplierID（新写入的）
                    status_new = set()        # MaterialNo（新写入的）
                    total_inserted = 0

                    # ── 3a. tb_siminfo ──
                    for row in whcenter_rows:
                        mn = row['MaterialNo']
                        if mn in existing_siminfo:
                            continue

                        await sim_cur.execute("SELECT fn_nextval('SI') AS nid")
                        nid = (await sim_cur.fetchone())['nid']

                        sw = supplier_wh.get(row.get('SupplierId'))
                        sid = sw['SupplierID'] if sw else None
                        sd = sw['SilentDuration'] if sw else None

                        mlen = len(mn)
                        if mlen == 13:
                            stype = 0
                        elif mlen == 11:
                            stype = 1
                        elif mlen == 15:
                            stype = 2
                        else:
                            stype = 0

                        audit_time = row.get('AuditTime')
                        silent_begin = audit_time.strftime('%Y-%m-%d 00:00:00') if audit_time else None

                        await sim_cur.execute("""
                            INSERT INTO tb_siminfo (
                                Id, SIMNumber, SIMSupplierID, SupplierWareHouseId,
                                SIMKinds, SIMType, SIMYears,
                                FirstInStockTime, SilentDuration,
                                SIMPackageName, IsInstallment, InstallmentCycle,
                                OwnerId, SimSpec,
                                CreatedById, CreatedAt, UpdatedById, UpdatedAt,
                                DeletedById, DeletedAt, Deleted, Remark,
                                SilentBeginTime, EnableTime
                            ) VALUES (
                                %s,%s,%s,%s,
                                1,%s,%s,
                                %s,%s,
                                %s,%s,%s,
                                %s,%s,
                                %s,NOW(),%s,NOW(),
                                NULL,NULL,0,NULL,
                                %s,NULL
                            )
                        """, (
                            nid, mn, sid, row.get('SupplierId'),
                            stype, None,
                            audit_time, sd,
                            None, None, None,
                            row.get('OwnerId'), row.get('SimSpec'),
                            '203E0000-3E01-0016-3584-08D39E2871A0',
                            '203E0000-3E01-0016-3584-08D39E2871A0',
                            silent_begin,
                        ))
                        siminfo_new[mn] = nid
                        siminfo_supplier[mn] = sid
                        total_inserted += 1

                    cnt = len(siminfo_new)
                    inserted_by_table['tb_siminfo'] = cnt
                    logger.info(f"写入 tb_siminfo: {cnt} 条")

                    # ── 3b. tb_simstatus ──
                    for row in whcenter_rows:
                        mn = row['MaterialNo']
                        if mn in existing_simstatus:
                            continue
                        info_id = siminfo_new.get(mn) or (existing_siminfo.get(mn) or {}).get('Id')
                        if not info_id:
                            continue

                        await sim_cur.execute("""
                            INSERT INTO tb_simstatus (
                                Id, SIMNumber, SIMPackage, SIMLifeCycle, SIMStatus,
                                SIMMarkStatus, WriteStatus, EnableStatus, SIMDataUseYesterday,
                                CustSettleAccountTime, CarUserAccountTime,
                                CustSettleRenewDuration, CarUserRenewDuration,
                                CarUserRefundDuration, ExpiryDate, DeviceNumber,
                                ICCID, VirtualICCID, LastUpdateTime, ActivationTime,
                                SupplierPackage
                            ) VALUES (
                                %s,%s,NULL,1,%s,
                                0,NULL,0,0,
                                NULL,NULL,
                                NULL,NULL,
                                NULL,NULL,NULL,
                                NULL,NULL,NOW(),NULL,
                                NULL
                            )
                        """, (info_id, mn, row.get('StockStatus')))
                        status_new.add(mn)
                        total_inserted += 1

                    cnt = len(status_new)
                    inserted_by_table['tb_simstatus'] = cnt
                    logger.info(f"写入 tb_simstatus: {cnt} 条")

                    # ── 3c. tb_simwarehouse ──
                    wh_count = 0
                    for row in whcenter_rows:
                        mn = row['MaterialNo']
                        if mn in existing_simwarehouse:
                            continue
                        info_id = siminfo_new.get(mn) or (existing_siminfo.get(mn) or {}).get('Id')
                        if not info_id:
                            continue

                        loc_id = row.get('StockLocationId') or ''
                        lt = 0 if loc_id.startswith('WH') else 1
                        pro_name = district_map.get(row.get('ProCode') or '')
                        city_name = district_map.get(row.get('CityCode') or '')

                        await sim_cur.execute("""
                            INSERT INTO tb_simwarehouse (
                                Id, SIMNumber, LocationType,
                                CustSettleId, CustSettleName, WarehouseId, WarehouseName,
                                ParentWareHouseId, ParentWareHouseName,
                                ProCode, ProName, CityCode, CityName,
                                OutStockTime, ManagerCode, ManagerName,
                                IsCardTermAdjust, OperationCode, OperationName, OperationTime,
                                Deleted
                            ) VALUES (
                                %s,%s,%s,
                                %s,%s,%s,%s,
                                %s,%s,
                                %s,%s,%s,%s,
                                NULL,%s,%s,
                                NULL,%s,%s,%s,
                                0
                            )
                        """, (
                            info_id, mn, lt,
                            row.get('CustSettleId'), row.get('CustSettleName'),
                            loc_id, row.get('StockLocationName'),
                            row.get('ParentWarehouseId'), row.get('WHName'),
                            row.get('ProCode'), pro_name, row.get('CityCode'), city_name,
                            row.get('LoginName'), row.get('UserName'),
                            row.get('AuditPerson'), row.get('AuditName'), row.get('AuditTime'),
                        ))
                        wh_count += 1
                        total_inserted += 1

                    inserted_by_table['tb_simwarehouse'] = wh_count
                    logger.info(f"写入 tb_simwarehouse: {wh_count} 条")

                    # ── 3d. tb_simfollowinfo ──
                    # 需要 tb_simstatus 的 SIMLifeCycle / SIMStatus / SIMMarkStatus
                    follow_count = 0
                    for row in whcenter_rows:
                        mn = row['MaterialNo']
                        if mn in existing_simfollowinfo:
                            continue
                        # 已有的或刚写入的 tb_simstatus 均可
                        if mn not in existing_simstatus and mn not in status_new:
                            continue

                        await sim_cur.execute(
                            "SELECT Id, SIMLifeCycle, SIMStatus, SIMMarkStatus "
                            "FROM tb_simstatus WHERE SimNumber = %s", (mn,)
                        )
                        st = await sim_cur.fetchone()
                        if not st:
                            continue

                        await sim_cur.execute("""
                            INSERT INTO tb_simfollowinfo (
                                SIMId, SIMNumber, SIMLifeCycle, SIMStatus, SIMMarkStatus,
                                OperationName, OperationSystem, CreatedByName, CreatedAt, Deleted
                            ) VALUES (
                                %s,%s,%s,%s,%s,
                                '',2,%s,%s,0
                            )
                        """, (
                            st['Id'], mn, st['SIMLifeCycle'], st['SIMStatus'], st['SIMMarkStatus'],
                            row.get('AuditName'), row.get('AuditTime'),
                        ))
                        follow_count += 1
                        total_inserted += 1

                    inserted_by_table['tb_simfollowinfo'] = follow_count
                    logger.info(f"写入 tb_simfollowinfo: {follow_count} 条")

                    # ── 3e. tb_simdatauseinfo ──
                    du_count = 0
                    for row in whcenter_rows:
                        mn = row['MaterialNo']
                        if mn in existing_simdatauseinfo:
                            continue
                        info_id = siminfo_new.get(mn) or (existing_siminfo.get(mn) or {}).get('Id')
                        if not info_id:
                            continue

                        # SIMSupplierID：优先用刚写入的，否则用已存在的
                        supplier_id = siminfo_supplier.get(mn)
                        if supplier_id is None and mn in existing_siminfo:
                            supplier_id = existing_siminfo[mn].get('SIMSupplierID')

                        await sim_cur.execute("SELECT fn_nextval('DU') AS nid")
                        du_id = (await sim_cur.fetchone())['nid']

                        await sim_cur.execute("""
                            INSERT INTO tb_simdatauseinfo (
                                Id, SIMId, SIMNumber, SIMSupplierID,
                                SIMUseDataTotal, SIMStatus, CheckDate, IsFrozen, Deleted
                            ) VALUES (
                                %s,%s,%s,%s,
                                0,0,CURDATE(),0,0
                            )
                        """, (du_id, info_id, mn, supplier_id))
                        du_count += 1
                        total_inserted += 1

                    inserted_by_table['tb_simdatauseinfo'] = du_count
                    logger.info(f"写入 tb_simdatauseinfo: {du_count} 条")

                    # ── 提交事务 ──
                    await sim_conn.commit()
                    logger.info(f"数据同步完成，总计写入: {total_inserted} 条")

                except Exception as e:
                    await sim_conn.rollback()
                    logger.error(f"数据同步失败: {e}")
                    raise

        return {
            "total_inserted": sum(inserted_by_table.values()),
            "sim_card_count": inserted_by_table.get('tb_siminfo', 0),
            "inserted_by_table": inserted_by_table
        }


sim_trans_service = SIMTransService()
