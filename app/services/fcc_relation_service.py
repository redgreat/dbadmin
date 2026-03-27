"""
FCC报销单关联服务
实现财务报销单与仓储对账单的关联功能
"""
import logging
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import aiomysql

from app.services.db_pool import db_pool
from app.controllers.conn import conn_controller
from app.settings.config import settings

logger = logging.getLogger(__name__)

# 数据库连接ID
WMS_CONN_ID = settings.WMS_CONN_ID
FCC_CONN_ID = settings.FCC_CONN_ID


class FccRelationService:
    """FCC报销单关联服务"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}  # 任务存储
    
    async def _ensure_wms_pool(self) -> None:
        """确保仓储中心连接池已注册"""
        pool = db_pool.get_pool(WMS_CONN_ID)
        if pool is not None:
            return
        conn = await conn_controller.get_decrypted_connection(WMS_CONN_ID)
        if not conn:
            raise ValueError("仓储中心连接池不存在")
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
    
    async def _ensure_fcc_pool(self) -> None:
        """确保FCC连接池已注册"""
        pool = db_pool.get_pool(FCC_CONN_ID)
        if pool is not None:
            return
        conn = await conn_controller.get_decrypted_connection(FCC_CONN_ID)
        if not conn:
            raise ValueError("FCC连接池不存在")
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
    
    def parse_input_text(self, input_text: str) -> Dict:
        """
        解析输入文本
        
        格式规则：
        - 每行一个FCC报销单与多个仓储对账单的关联
        - 格式：FCC报销单号:仓储对账单1,仓储对账单2,...;
        - 示例：J202512250009:ZD20260325153906B413D18,ZD202603251538028DCFA89;
        
        Args:
            input_text: 输入文本
            
        Returns:
            解析结果字典
        """
        relations = []
        lines = input_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or not line.endswith(';'):
                continue
            
            line = line[:-1]  # 去除分号
            if ':' not in line:
                continue
            
            parts = line.split(':')
            if len(parts) != 2:
                continue
            
            fcc_no = parts[0].strip()
            # 支持逗号、顿号、中文逗号分隔
            wms_nos = []
            for w in parts[1].replace('、', ',').replace('，', ',').split(','):
                w = w.strip()
                if w:
                    wms_nos.append(w)
            
            if fcc_no and wms_nos:
                relations.append({
                    'fcc_no': fcc_no,
                    'wms_nos': wms_nos
                })
        
        total_fcc = len(relations)
        total_wms = sum(len(r['wms_nos']) for r in relations)
        
        return {
            'relations': relations,
            'total_fcc': total_fcc,
            'total_wms': total_wms
        }
    
    async def validate_codenumber(self, relations: List[Dict]) -> Dict:
        """
        验证单据存在性
        
        Args:
            relations: 对应关系列表
            
        Returns:
            验证结果字典
        """
        await self._ensure_wms_pool()
        await self._ensure_fcc_pool()
        
        wms_pool = db_pool.get_pool(WMS_CONN_ID)
        fcc_pool = db_pool.get_pool(FCC_CONN_ID)
        
        if not wms_pool or not fcc_pool:
            raise ValueError("数据库连接池不存在")
        
        not_found_fcc = []
        not_found_wms = []
        
        # 收集所有单号
        all_fcc_nos = list(set(r['fcc_no'] for r in relations))
        all_wms_nos = list(set(w for r in relations for w in r['wms_nos']))
        
        # 验证FCC报销单（SQL Server）
        async with fcc_pool.acquire() as conn:
            async with conn.cursor() as cur:
                for fcc_no in all_fcc_nos:
                    # SQL1: 验证FCC报销单是否存在
                    sql = "SELECT COUNT(*) FROM [dbo].[fms.reimbursement_info] WHERE CodeNumber = ?"
                    await cur.execute(sql, (fcc_no,))
                    result = await cur.fetchone()
                    if not result or result[0] == 0:
                        not_found_fcc.append(fcc_no)
        
        # 验证仓储对账单（MySQL）
        if isinstance(wms_pool, aiomysql.Pool):
            async with wms_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    for wms_no in all_wms_nos:
                        # SQL2: 验证仓储对账单是否存在
                        sql = "SELECT COUNT(*) FROM tb_reconcinfo WHERE ReconcNo = %s"
                        await cur.execute(sql, (wms_no,))
                        result = await cur.fetchone()
                        if not result or result[0] == 0:
                            not_found_wms.append(wms_no)
        
        valid = len(not_found_fcc) == 0 and len(not_found_wms) == 0
        
        if valid:
            message = "所有单据验证通过"
        else:
            parts = []
            if not_found_fcc:
                parts.append(f"{len(not_found_fcc)} 个FCC报销单不存在")
            if not_found_wms:
                parts.append(f"{len(not_found_wms)} 个仓储对账单不存在")
            message = "，".join(parts)
        
        return {
            'valid': valid,
            'not_found_fcc': not_found_fcc,
            'not_found_wms': not_found_wms,
            'message': message
        }
    
    async def execute_relation_task(self, task_id: str, relations: List[Dict]) -> None:
        """
        执行关联任务（异步）
        
        Args:
            task_id: 任务ID
            relations: 对应关系列表
        """
        try:
            # 更新任务状态为processing
            self.tasks[task_id]['status'] = 'processing'
            
            await self._ensure_wms_pool()
            await self._ensure_fcc_pool()
            
            wms_pool = db_pool.get_pool(WMS_CONN_ID)
            fcc_pool = db_pool.get_pool(FCC_CONN_ID)
            
            if not wms_pool or not fcc_pool:
                raise ValueError("数据库连接池不存在")
            
            # 计算总数
            total = sum(len(r['wms_nos']) for r in relations)
            self.tasks[task_id]['progress']['total'] = total
            
            success_count = 0
            failed_items = []
            processed = 0
            
            # 逐个处理关联关系
            for relation in relations:
                fcc_no = relation['fcc_no']
                wms_nos = relation['wms_nos']
                
                try:
                    # 步骤1: 从仓储中心查询对账单信息（SQL3）
                    reconc_data = []
                    if isinstance(wms_pool, aiomysql.Pool):
                        async with wms_pool.acquire() as conn:
                            async with conn.cursor() as cur:
                                # SQL3: 查询仓储对账单信息
                                placeholders = ','.join(['%s'] * len(wms_nos))
                                sql = f"""
                                    SELECT a.Id AS ReconcId,a.ReconcNo,a.SupplierId,a.SupplierName,a.OwnerId,a.OwnerName,
                                      a.Amount AS ReconcPrice,a.SubmitPerson AS ReconcPersonCode,a.SubmitPersonName AS ReconcPersonName,
                                      a.SubmitTime AS ApplyTime,a.OwingNum AS ReconcNum
                                    FROM tb_reconcinfo a
                                    JOIN tb_reconcdetail b
                                      ON b.ReconcId=a.Id
                                      AND b.Deleted=0
                                    WHERE a.Deleted=0
                                      AND a.ReconcNo IN ({placeholders})
                                """
                                await cur.execute(sql, wms_nos)
                                reconc_data = await cur.fetchall()
                    
                    if not reconc_data:
                        raise ValueError(f"未查询到对账单信息: {wms_nos}")
                    
                    # 步骤2: 写入FCC临时表（SQL4）
                    async with fcc_pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            # 先清空临时表
                            await cur.execute("DELETE FROM [dbo].[tm_wh_reconcinfo]")
                            
                            # SQL4: 写入FCC临时表
                            insert_values = []
                            for row in reconc_data:
                                reconc_id, reconc_no, supplier_id, supplier_name, owner_id, owner_name, \
                                reconc_price, reconc_person_code, reconc_person_name, apply_time, reconc_num = row
                                insert_values.append(
                                    f"('{reconc_id}','{reconc_no}','{supplier_id}','{supplier_name}',"
                                    f"'{owner_id}','{owner_name}',{reconc_price},'{reconc_person_code}',"
                                    f"'{reconc_person_name}','{apply_time}',null,{reconc_num})"
                                )
                            
                            if insert_values:
                                insert_sql = f"""
                                    INSERT INTO [dbo].[tm_wh_reconcinfo] 
                                    ([ReconcId],[ReconcNo],[SupplierId],[SupplierName],[OwnerId],[OwnerName],
                                     [ReconcPrice],[ReconcPersonCode],[ReconcPersonName],[ApplyTime],
                                     [CodeNumber],[ReconcNum]) 
                                    VALUES {','.join(insert_values)}
                                """
                                await cur.execute(insert_sql)
                            
                            # 步骤3: 写入FCC对应关系表（SQL5）
                            placeholders = ','.join(['?'] * len(wms_nos))
                            sql5 = f"""
                                SELECT NEWID() AS Id,1 AS ApplicationType,B.Id AS ApplicationId,B.CodeNumber,C.Id AS CostDetailId,
                                       A.ReconcId,A.ReconcNo,A.SupplierId,A.SupplierName,
                                       D.CompanyId AS OwnerId,
                                       D.OwnerId AS WareHouseOwnerId,D.OwnerName,
                                       A.ApplyTime,
                                       A.ReconcPrice,
                                       A.ReconcPrice AS InvoiceSurplusPrice,
                                       A.ReconcPrice AS ThisInvoicePrice,
                                       (CAST(FORMAT(GETDATE(),'yyyy-MM-dd') AS VARCHAR)+' 手动刷数') AS Remark,
                                       A.ReconcPersonCode,A.ReconcPersonName,
                                       NULL,GETDATE(),NULL,GETDATE(),NULL,NULL,0,A.ReconcNum
                                  FROM tm_wh_reconcinfo A
                                  LEFT JOIN dbo.[fms.reimbursement_info] B ON B.CodeNumber=?
                                  LEFT JOIN dbo.[fms.costdetail_info] C ON B.Id=C.ReimbursementId AND C.Deleted=0
                                  LEFT JOIN dbo.[fms_warehouse_ownerinfo] D ON D.OwnerId=A.OwnerId
                                  LEFT JOIN membership_userbaseinfo E ON B.CreatedById=E.Id
                                 WHERE 1=1
                                   AND A.ReconcNo IN ({placeholders})
                                 ORDER BY A.ApplyTime
                            """
                            params = [fcc_no] + wms_nos
                            await cur.execute(sql5, params)
                            relation_data = await cur.fetchall()
                            
                            # 插入到正式表
                            if relation_data:
                                for rel_row in relation_data:
                                    # 这里需要根据实际表结构构建INSERT语句
                                    # 暂时记录日志
                                    logger.info(f"关联数据: {rel_row}")
                    
                    # 步骤4: 更新仓储中心付款状态（SQL6）
                    if isinstance(wms_pool, aiomysql.Pool):
                        async with wms_pool.acquire() as conn:
                            async with conn.cursor() as cur:
                                # SQL6: 更新仓储中心付款状态
                                placeholders = ','.join(['%s'] * len(wms_nos))
                                sql6 = f"""
                                    UPDATE tb_owinginfo x
                                      SET OwingStatus=4,OwingPrice=0,OwingedPrice=Amount
                                    WHERE x.Id IN (
                                      SELECT S.OwingId FROM(
                                    SELECT a.OwingId,SUM(a.ReconcNum),b.StockNum
                                      FROM tb_reconcdetail a
                                      JOIN tb_owinginfo b
                                        ON b.Id=a.OwingId
                                        AND b.Deleted=0
                                      JOIN tb_reconcinfo c
                                        ON c.Id=a.ReconcId
                                        AND c.Deleted=0
                                    WHERE a.Deleted=0
                                      AND c.ReconcNo IN ({placeholders})
                                    GROUP BY a.OwingId
                                      HAVING SUM(a.ReconcNum)=b.StockNum ) AS S
                                      )
                                """
                                await cur.execute(sql6, wms_nos)
                                
                                # SQL7: 更新应付单付款信息
                                sql7 = f"""
                                    UPDATE tb_reconcinfo
                                    SET PayStatus=3,InvoiceStatus=2,InvoicePrice=Amount,UnInvoicePrice=0 
                                    WHERE ReconcNo IN ({placeholders})
                                      AND Deleted=0
                                """
                                await cur.execute(sql7, wms_nos)
                    
                    # 成功处理
                    success_count += len(wms_nos)
                    processed += len(wms_nos)
                    
                except Exception as e:
                    logger.error(f"处理关联失败: fcc_no={fcc_no}, wms_nos={wms_nos}, error={e}")
                    for wms_no in wms_nos:
                        failed_items.append({
                            'fcc_no': fcc_no,
                            'wms_no': wms_no,
                            'reason': str(e)
                        })
                        processed += 1
                finally:
                    self.tasks[task_id]['progress']['processed'] = processed
                    self.tasks[task_id]['progress']['success'] = success_count
                    self.tasks[task_id]['progress']['failed'] = len(failed_items)
            
            # 更新任务状态为completed
            self.tasks[task_id]['status'] = 'completed'
            self.tasks[task_id]['finished_at'] = datetime.now().isoformat()
            self.tasks[task_id]['result'] = {
                'success_count': success_count,
                'failed_items': failed_items
            }
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}")
            self.tasks[task_id]['status'] = 'failed'
            self.tasks[task_id]['finished_at'] = datetime.now().isoformat()
            self.tasks[task_id]['result'] = {
                'success_count': 0,
                'failed_items': [{
                    'fcc_no': '',
                    'wms_no': '',
                    'reason': str(e)
                }]
            }
    
    async def submit_task(self, relations: List[Dict]) -> str:
        """
        提交任务
        
        Args:
            relations: 对应关系列表
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            'task_id': task_id,
            'status': 'pending',
            'progress': {
                'total': 0,
                'processed': 0,
                'success': 0,
                'failed': 0
            },
            'result': None,
            'created_at': datetime.now().isoformat(),
            'finished_at': None
        }
        
        # 异步执行任务
        asyncio.create_task(self.execute_relation_task(task_id, relations))
        
        return task_id
    
    def query_task_status(self, task_id: str) -> Optional[Dict]:
        """
        查询任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典
        """
        return self.tasks.get(task_id)


# 单例
fcc_relation_service = FccRelationService()
