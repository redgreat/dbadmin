"""
SIM卡重复入库验证服务
流程：
1. 解析Excel/CSV（仅一列 SimNumber），生成批次号 ImpStamp。
2. 将 SimNumber 批量写入 WMS_CONN(whcenter) 的临时表 tm_remano（按 ImpStamp 隔离）。
3. 执行验证SQL，命中 tb_materialinit(Deleted=0) 的即视为"重复入库"。
4. 结果写入系统管理库 sys_simdupverify_record / sys_simdupverify_result。
5. 生成重复编码导出Excel，保存文件路径，供页面随时下载。
6. 验证完成后清理 tm_remano 本批次数据。
"""
import csv
import io
import logging
import os
import uuid
from datetime import datetime
from io import BytesIO

import aiomysql
import openpyxl

from app.models.simdupverify import SimDupVerifyRecord, SimDupVerifyResult
from app.services.db_pool import db_pool, is_connection_error
from app.settings.config import settings

logger = logging.getLogger(__name__)

# 仓储中心连接ID（延迟获取，避免模块加载时Tortoise未初始化）
_wms_conn_id = None


async def _get_wms_conn_id() -> int:
    global _wms_conn_id
    if _wms_conn_id is None:
        _wms_conn_id = await settings.WMS_CONN_ID()
    return _wms_conn_id


async def _get_wms_conn_id() -> int:
    global _wms_conn_id
    if _wms_conn_id is None:
        _wms_conn_id = await settings.WMS_CONN_ID()
    return _wms_conn_id


# 导出目录（本地文件，供页面下载；相对应用根目录 data/simdup）
# 项目根目录 = 从 app/services 向上三级
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_EXPORT_DIR = os.path.join(_PROJECT_ROOT, "data", "simdup")

BATCH_SIZE = 1000
# 对外API单次验证数量上限（同时限制SQL IN占位符规模）
MAX_API_CODES = 20000


def build_template_bytes() -> bytes:
    """生成SIM卡重复入库验证模板Excel（仅一列 SimNumber + 示例行）"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SimNumber"
    ws.append(["SimNumber"])
    ws.append(["89010000000000000000"])
    ws.append(["89010000000000000001"])
    ws.column_dimensions["A"].width = 26
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()

# 验证SQL：命中 tb_materialinit(未删除) 的 MaterialNo 即视为重复入库
# %s 参数化为本次批次号(InStamp)，保证只匹配当前导入批次
VERIFY_SQL = """
    SELECT a.MaterialNo
    FROM tb_materialinit a
    JOIN tm_remano b
      ON b.MaterialNo = a.MaterialNo
      AND b.ImpStamp = %s
    WHERE a.Deleted = 0
"""


class SimDupVerifyService:
    """SIM卡重复入库验证服务"""

    def __init__(self):
        os.makedirs(_EXPORT_DIR, exist_ok=True)

    # ── 批次号 ──
    def _new_batch_no(self) -> str:
        return uuid.uuid4().hex

    # ── 连接池 ──
    async def _ensure_pool(self) -> aiomysql.Pool:
        conn_id = await _get_wms_conn_id()
        if conn_id in (None, 0):
            raise ValueError("仓储中心数据库连接未配置（WMS_CONN）")
        await db_pool.ensure_pool(conn_id)
        pool = db_pool.get_pool(conn_id)
        if pool is None:
            raise ValueError("仓储中心连接池不存在")
        if not isinstance(pool, aiomysql.Pool):
            raise ValueError("仓储中心连接必须是 MySQL 类型")
        return pool

    # ── 解析Excel/CSV，提取SimNumber列 ──
    def parse_sim_numbers(self, content: bytes, filename: str) -> list[str]:
        ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
        numbers: list[str] = []
        if ext in ("xlsx", "xls"):
            try:
                wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
            except Exception as e:
                raise ValueError(f"Excel文件解析失败: {e!s}")
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if not rows:
                raise ValueError("Excel文件内容为空")
            header = [str(c).strip() if c is not None else "" for c in rows[0]]
            idx = self._find_sim_column(header)
            for row in rows[1:]:
                if row is None or len(row) <= idx:
                    continue
                val = row[idx]
                if val is None:
                    continue
                s = str(val).strip()
                if s:
                    numbers.append(s)
        elif ext == "csv":
            text = content.decode("utf-8-sig", errors="ignore")
            reader = csv.reader(io.StringIO(text))
            try:
                header = next(reader)
            except StopIteration:
                raise ValueError("CSV文件内容为空")
            header = [h.strip() for h in header]
            idx = self._find_sim_column(header)
            for r in reader:
                if not r or len(r) <= idx:
                    continue
                s = (r[idx] or "").strip()
                if s:
                    numbers.append(s)
        else:
            raise ValueError("仅支持 .xlsx / .xls / .csv 文件")

        numbers = list(dict.fromkeys(n for n in (s.strip() for s in numbers) if n))
        if not numbers:
            raise ValueError("文件中没有有效的SimNumber数据")
        return numbers

    @staticmethod
    def _find_sim_column(header: list[str]) -> int:
        for i, h in enumerate(header):
            if h.strip().lower() in ("simnumber", "sim_number", "simno", "物料编码", "物料编码(simnumber)", "物料编号"):
                return i
        if not header:
            return 0
        return 0

    # ── 写入临时表 tm_remano（分批 executemany，避免单条SQL过大）──
    async def _write_tmp(self, pool: aiomysql.Pool, batch_no: str, numbers: list[str]) -> int:
        sql = "INSERT IGNORE INTO tm_remano (MaterialNo, ImpStamp) VALUES (%s, %s)"
        rows = [(n, batch_no) for n in numbers]
        written = 0
        async with pool.acquire() as conn, conn.cursor() as cur:
            for i in range(0, len(rows), BATCH_SIZE):
                chunk = rows[i : i + BATCH_SIZE]
                await cur.executemany(sql, chunk)
                written += len(chunk)
            await conn.commit()
        return written

    # ── 执行验证SQL ──
    async def _run_verify(self, pool: aiomysql.Pool, batch_no: str) -> list[str]:
        async with pool.acquire() as conn, conn.cursor() as cur:
            await cur.execute(VERIFY_SQL, (batch_no,))
            rows = await cur.fetchall()
            return [r[0] for r in rows]

    # ── 清理本批次 ──
    async def _cleanup_batch(self, pool: aiomysql.Pool, batch_no: str) -> int:
        try:
            async with pool.acquire() as conn, conn.cursor() as cur:
                await cur.execute("DELETE FROM tm_remano WHERE ImpStamp = %s", (batch_no,))
                await conn.commit()
                return cur.rowcount or 0
        except Exception as e:
            logger.warning(f"清理tm_remano批次失败: batch={batch_no}, error={e}")
            return 0

    # ── 导出Excel ──
    def export_excel(self, batch_no: str, duplicates: list[str]) -> str:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "重复入库卡号"
        ws.append(["SimNumber"])
        for n in duplicates:
            ws.append([n])
        ws.column_dimensions["A"].width = 26
        buffer = BytesIO()
        wb.save(buffer)
        fname = f"simdup_{batch_no}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        path = os.path.join(_EXPORT_DIR, fname)
        with open(path, "wb") as f:
            f.write(buffer.getvalue())
        return path

    # ── 持久化记录与结果 ──
    async def _persist(
        self,
        record: SimDupVerifyRecord,
        duplicates: list[str],
        success: bool,
        message: str,
    ) -> SimDupVerifyRecord:
        record.status = "completed" if success else "failed"
        record.duplicate_count = len(duplicates)
        record.message = message
        record.finished_at = datetime.now()
        if success and duplicates:
            try:
                record.result_file_path = self.export_excel(record.batch_no, duplicates)
            except Exception as e:
                logger.warning(f"导出重复编码Excel失败: {e}")
                record.result_file_path = None
        await record.save()
        if success:
            # 结果子表：只存命中的重复卡号
            objs = [SimDupVerifyResult(record=record, sim_number=n) for n in duplicates]
            if objs:
                await SimDupVerifyResult.bulk_create(objs, batch_size=1000)
        return record

    # ── 主流程：Web 页面导入验证 ──
    async def verify_from_upload(
        self,
        content: bytes,
        filename: str,
        user_id: int,
        username: str,
        source: str = "web",
        api_caller: str = "",
    ) -> SimDupVerifyRecord:
        numbers = self.parse_sim_numbers(content, filename)
        record = await SimDupVerifyRecord.create(
            batch_no=self._new_batch_no(),
            source=source,
            status="processing",
            filename=filename or "",
            total_count=len(numbers),
            user_id=user_id or 0,
            username=username or "",
            api_caller=api_caller or "",
            started_at=datetime.now(),
        )

        pool = await self._ensure_pool()
        try:
            await self._write_tmp(pool, record.batch_no, numbers)
        except Exception as e:
            if is_connection_error(e):
                logger.warning(f"SIM验证检测到连接异常，自动重连后重试: {e}")
                await db_pool.reconnect_pool(await _get_wms_conn_id())
                pool = await self._ensure_pool()
                await self._write_tmp(pool, record.batch_no, numbers)
            else:
                await self._persist(record, [], False, f"写入临时表失败: {e!s}")
                await self._cleanup_batch(pool, record.batch_no)
                return record

        try:
            duplicates = await self._run_verify(pool, record.batch_no)
        except Exception as e:
            await self._persist(record, [], False, f"执行验证SQL失败: {e!s}")
            await self._cleanup_batch(pool, record.batch_no)
            return record

        if duplicates:
            msg = f"验证完成：导入{len(numbers)}个SimNumber，其中{len(duplicates)}个已存在于系统（重复入库）"
        else:
            msg = f"验证完成：导入{len(numbers)}个SimNumber，未发现重复入库"
        await self._persist(record, duplicates, True, msg)
        await self._cleanup_batch(pool, record.batch_no)
        return record

    # ── 对外API：直接传 SimNumber 列表验证（不落临时表，避免污染 tm_remano）──
    async def verify_codes(
        self,
        codes: list[str],
        user_id: int,
        username: str,
        api_caller: str = "",
    ) -> dict:
        codes = list(dict.fromkeys(c.strip() for c in codes if c and c.strip()))
        if not codes:
            raise ValueError("SimNumber列表不能为空")
        if len(codes) > MAX_API_CODES:
            raise ValueError(f"单次验证SimNumber数量上限为{MAX_API_CODES}")

        record = await SimDupVerifyRecord.create(
            batch_no=self._new_batch_no(),
            source="api",
            status="processing",
            filename="",
            total_count=len(codes),
            user_id=user_id or 0,
            username=username or "",
            api_caller=api_caller or "",
            started_at=datetime.now(),
        )

        pool = await self._ensure_pool()
        try:
            # 直接以参数化 IN 查询，避免向临时表写数据
            placeholders = ",".join(["%s"] * len(codes))
            sql = f"""
                SELECT a.MaterialNo
                FROM tb_materialinit a
                WHERE a.Deleted = 0
                  AND a.MaterialNo IN ({placeholders})
            """
            async with pool.acquire() as conn, conn.cursor() as cur:
                await cur.execute(sql, codes)
                rows = await cur.fetchall()
                duplicates = [r[0] for r in rows]
        except Exception as e:
            if is_connection_error(e):
                logger.warning(f"对外API验证检测到连接异常，自动重连后重试: {e}")
                await db_pool.reconnect_pool(await _get_wms_conn_id())
                pool = await self._ensure_pool()
                placeholders = ",".join(["%s"] * len(codes))
                sql = f"""
                    SELECT a.MaterialNo
                    FROM tb_materialinit a
                    WHERE a.Deleted = 0
                      AND a.MaterialNo IN ({placeholders})
                """
                async with pool.acquire() as conn, conn.cursor() as cur:
                    await cur.execute(sql, codes)
                    rows = await cur.fetchall()
                    duplicates = [r[0] for r in rows]
            else:
                await self._persist(record, [], False, f"对外API验证失败: {e!s}")
                return {
                    "batch_no": record.batch_no,
                    "total_count": len(codes),
                    "duplicate_count": 0,
                    "duplicates": [],
                    "success": False,
                    "message": f"验证失败: {e!s}",
                }

        if duplicates:
            msg = f"发现{len(duplicates)}个重复入库卡号"
        else:
            msg = "未发现重复入库卡号"
        await self._persist(record, duplicates, True, msg)
        return {
            "batch_no": record.batch_no,
            "total_count": len(codes),
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
            "success": True,
            "message": msg,
        }


simdup_service = SimDupVerifyService()
