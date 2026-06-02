from typing import List, Dict, Any, Optional, Awaitable, Callable
import aiomysql
import logging
from app.services.db_pool import db_pool, is_connection_error
from app.settings.config import settings

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[Dict[str, Any]], Awaitable[None]]
BATCH_SIZE = 2000


class SIMTransService:
    """SIM卡同步服务 - 从仓储中心同步数据到SIM卡中心"""

    async def _get_wms_conn_id(self):
        """获取仓储中心连接ID"""
        return await settings.WMS_CONN_ID()

    async def _get_sim_conn_id(self):
        """获取SIM卡中心连接ID"""
        return await settings.SIM_CONN_ID()

    def _chunks(self, items: List[Any], size: int = BATCH_SIZE):
        for start in range(0, len(items), size):
            yield items[start:start + size]

    async def _emit_progress(
        self,
        progress_cb: Optional[ProgressCallback],
        stage: str,
        message: str,
        progress: int,
        **extra,
    ):
        if progress_cb:
            await progress_cb({
                "stage": stage,
                "message": message,
                "progress": max(0, min(progress, 100)),
                **extra,
            })

    async def _ensure_wms_pool(self):
        wms_conn_id = await self._get_wms_conn_id()
        if wms_conn_id == 0:
            raise ValueError("仓储中心数据库连接未配置")
        pool = await db_pool.ensure_pool(wms_conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("仓储中心连接必须是 MySQL 类型")
        return wms_conn_id, pool

    async def _ensure_sim_pool(self):
        sim_conn_id = await self._get_sim_conn_id()
        if sim_conn_id == 0:
            raise ValueError("SIM卡中心数据库连接未配置")
        pool = await db_pool.ensure_pool(sim_conn_id)
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("SIM卡中心连接必须是 MySQL 类型")
        return sim_conn_id, pool

    async def _reconnect_known_pools(self):
        for conn_id in (await self._get_wms_conn_id(), await self._get_sim_conn_id()):
            if conn_id:
                try:
                    await db_pool.reconnect_pool(conn_id)
                except Exception as exc:
                    logger.warning(f"自动重连数据库失败: conn_id={conn_id}, error={exc}")

    async def validate_receipt_exists(self, receipt_numbers: List[str]) -> Dict[str, Any]:
        """
        验证入库单号在仓储中心是否存在（已完成且未删除）

        Args:
            receipt_numbers: 入库单号列表

        Returns:
            验证结果
        """
        _, pool = await self._ensure_wms_pool()

        not_exists = []
        exists = []

        # 验证仓储单据是否存在
        VALIDATE_SQL = """
        SELECT InStockNo
        FROM tb_instockinfohis
        WHERE InStockNo = %s AND InStockType = 'IN0' AND Deleted = 0
        """

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
        _, pool = await self._ensure_wms_pool()

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

        installed_count = 0
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.cursors.DictCursor) as cur:
                for receipt_chunk in self._chunks(receipt_numbers):
                    placeholders = ','.join(['%s'] * len(receipt_chunk))
                    sql = CHECK_INSTALLED_SQL.format(placeholders)

                    await cur.execute(sql, tuple(receipt_chunk))
                    result = await cur.fetchone()
                    installed_count += result['installed_count'] if result else 0

        return {
            "has_installed": installed_count > 0,
            "installed_count": installed_count
        }

    async def sync_sim_cards(
        self,
        receipt_numbers_text: str,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
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

        try:
            return await self._sync_sim_cards_once(receipt_numbers, progress_cb)
        except Exception as exc:
            if not is_connection_error(exc):
                raise
            logger.warning(f"SIM同步检测到数据库连接异常，自动重连后重试一次: {exc}")
            await self._emit_progress(progress_cb, "reconnecting", "数据库连接已断开，正在自动重连", 5)
            await self._reconnect_known_pools()
            return await self._sync_sim_cards_once(receipt_numbers, progress_cb)

    async def _sync_sim_cards_once(
        self,
        receipt_numbers: List[str],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        # 步骤1: 验证入库单号是否存在
        logger.info(f"开始验证入库单号: {receipt_numbers}")
        await self._emit_progress(progress_cb, "validating", "正在验证入库单号", 5)
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
        await self._emit_progress(progress_cb, "checking", "正在检查设备加装状态", 15)
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
        await self._emit_progress(progress_cb, "syncing", "开始执行数据同步", 25)
        sync_result = await self._execute_sync(valid_receipts, progress_cb=progress_cb)
        
        return {
            "success": True,
            "message": f"同步完成，共写入 {sync_result['sim_card_count']} 张SIM卡",
            "validation": validation_result,
            "installed_check": installed_check,
            "sync_result": sync_result
        }

    async def _fetch_existing_map(self, cur, sql: str, material_nos: List[str], key: str = "SimNumber") -> Dict[str, Dict[str, Any]]:
        rows = {}
        for material_chunk in self._chunks(material_nos):
            placeholders = ','.join(['%s'] * len(material_chunk))
            await cur.execute(sql.format(placeholders=placeholders), tuple(material_chunk))
            for row in await cur.fetchall():
                rows[row[key]] = row
        return rows

    async def _fetch_existing_set(self, cur, sql: str, material_nos: List[str], key: str = "SimNumber") -> set:
        rows = set()
        for material_chunk in self._chunks(material_nos):
            placeholders = ','.join(['%s'] * len(material_chunk))
            await cur.execute(sql.format(placeholders=placeholders), tuple(material_chunk))
            rows.update(row[key] for row in await cur.fetchall())
        return rows

    async def _execute_sync(
        self,
        receipt_numbers: List[str],
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Dict[str, Any]:
        """
        执行数据同步 - 先从WMS_CONN查询仓储数据，取回结果再写入SIM_CONN

        Args:
            receipt_numbers: 入库单号列表

        Returns:
            同步结果统计
        """
        _, wms_pool = await self._ensure_wms_pool()
        _, sim_pool = await self._ensure_sim_pool()

        inserted_by_table = {
            "tb_siminfo": 0,
            "tb_simstatus": 0,
            "tb_simwarehouse": 0,
            "tb_simfollowinfo": 0,
            "tb_simdatauseinfo": 0,
        }

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

        whcenter_rows = []
        async with wms_pool.acquire() as wms_conn:
            async with wms_conn.cursor(aiomysql.cursors.DictCursor) as wms_cur:
                for receipt_chunk in self._chunks(receipt_numbers):
                    placeholders = ','.join(['%s'] * len(receipt_chunk))
                    await wms_cur.execute(
                        wms_query.format(placeholders=placeholders),
                        tuple(receipt_chunk),
                    )
                    whcenter_rows.extend(await wms_cur.fetchall())

        if not whcenter_rows:
            logger.info("未查询到仓储数据，跳过同步")
            return {"total_inserted": 0, "sim_card_count": 0, "inserted_by_table": {}}

        material_nos = [r['MaterialNo'] for r in whcenter_rows]
        logger.info(f"从WMS_CONN查询到 {len(whcenter_rows)} 条仓储记录")
        await self._emit_progress(
            progress_cb,
            "syncing",
            f"从仓储中心查询到 {len(whcenter_rows)} 条记录，开始分批写入",
            35,
            total=len(whcenter_rows),
            current=0,
        )

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

                processed = 0

                for row_chunk in self._chunks(whcenter_rows):
                    chunk_material_nos = [r['MaterialNo'] for r in row_chunk]

                    # 2c. 各目标表中已有的 SimNumber。按批查询，避免 MySQL range_optimizer 内存 warning。
                    existing_siminfo = await self._fetch_existing_map(
                        sim_cur,
                        "SELECT SimNumber, Id, SIMSupplierID FROM tb_siminfo WHERE SimNumber IN ({placeholders})",
                        chunk_material_nos,
                    )
                    existing_simstatus = await self._fetch_existing_set(
                        sim_cur,
                        "SELECT SimNumber FROM tb_simstatus WHERE SimNumber IN ({placeholders})",
                        chunk_material_nos,
                    )
                    existing_simwarehouse = await self._fetch_existing_set(
                        sim_cur,
                        "SELECT SimNumber FROM tb_simwarehouse WHERE SimNumber IN ({placeholders})",
                        chunk_material_nos,
                    )
                    existing_simfollowinfo = await self._fetch_existing_set(
                        sim_cur,
                        "SELECT SimNumber FROM tb_simfollowinfo WHERE SimNumber IN ({placeholders})",
                        chunk_material_nos,
                    )
                    existing_simdatauseinfo = await self._fetch_existing_set(
                        sim_cur,
                        "SELECT SIMNumber AS SimNumber FROM tb_simdatauseinfo WHERE SIMNumber IN ({placeholders})",
                        chunk_material_nos,
                    )

                    # ══════════════════════════════════════════════════
                    # Step 3: 在 SIM_CONN 上分批写入（每批一个事务）
                    # ══════════════════════════════════════════════════
                    await sim_conn.begin()
                    try:
                        batch_inserted = 0
                        batch_counts = {
                            "tb_siminfo": 0,
                            "tb_simstatus": 0,
                            "tb_simwarehouse": 0,
                            "tb_simfollowinfo": 0,
                            "tb_simdatauseinfo": 0,
                        }
                        siminfo_new = {}          # MaterialNo -> Id
                        siminfo_supplier = {}     # MaterialNo -> SIMSupplierID（新写入的）
                        status_new = set()        # MaterialNo（新写入的）
    
                        # ── 3a. tb_siminfo ──
                        for row in row_chunk:
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
                            batch_inserted += 1
    
                        cnt = len(siminfo_new)
                        batch_counts['tb_siminfo'] = cnt
    
                        # ── 3b. tb_simstatus ──
                        for row in row_chunk:
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
                            batch_inserted += 1
    
                        cnt = len(status_new)
                        batch_counts['tb_simstatus'] = cnt
    
                        # ── 3c. tb_simwarehouse ──
                        wh_count = 0
                        for row in row_chunk:
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
                            batch_inserted += 1
    
                        batch_counts['tb_simwarehouse'] = wh_count
    
                        # ── 3d. tb_simfollowinfo ──
                        # 需要 tb_simstatus 的 SIMLifeCycle / SIMStatus / SIMMarkStatus
                        follow_count = 0
                        for row in row_chunk:
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
                            batch_inserted += 1
    
                        batch_counts['tb_simfollowinfo'] = follow_count
    
                        # ── 3e. tb_simdatauseinfo ──
                        du_count = 0
                        for row in row_chunk:
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
                            batch_inserted += 1
    
                        batch_counts['tb_simdatauseinfo'] = du_count
    
                        # ── 提交事务 ──
                        await sim_conn.commit()
                        for table, count in batch_counts.items():
                            inserted_by_table[table] += count
                        processed += len(row_chunk)
                        logger.info(
                            f"SIM同步批次完成: processed={processed}/{len(whcenter_rows)}, "
                            f"batch_inserted={batch_inserted}"
                        )
                        await self._emit_progress(
                            progress_cb,
                            "syncing",
                            f"已同步 {processed}/{len(whcenter_rows)} 条仓储记录",
                            35 + int(processed / len(whcenter_rows) * 60),
                            total=len(whcenter_rows),
                            current=processed,
                            inserted_by_table=inserted_by_table,
                        )

                    except Exception as e:
                        await sim_conn.rollback()
                        logger.error(f"数据同步失败: {e}")
                        raise

                logger.info(f"写入 tb_siminfo: {inserted_by_table['tb_siminfo']} 条")
                logger.info(f"写入 tb_simstatus: {inserted_by_table['tb_simstatus']} 条")
                logger.info(f"写入 tb_simwarehouse: {inserted_by_table['tb_simwarehouse']} 条")
                logger.info(f"写入 tb_simfollowinfo: {inserted_by_table['tb_simfollowinfo']} 条")
                logger.info(f"写入 tb_simdatauseinfo: {inserted_by_table['tb_simdatauseinfo']} 条")
                logger.info(f"数据同步完成，总计写入: {sum(inserted_by_table.values())} 条")

        return {
            "total_inserted": sum(inserted_by_table.values()),
            "sim_card_count": inserted_by_table.get('tb_siminfo', 0),
            "inserted_by_table": inserted_by_table
        }


sim_trans_service = SIMTransService()
