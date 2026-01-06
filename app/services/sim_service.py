from typing import List, Tuple
from io import BytesIO
import csv
import uuid
import aiomysql
from app.services.db_pool import db_pool
from app.controllers.conn import conn_controller
from app.settings.config import settings

# SIM导入固定连接的Id
sim_conn_id = settings.SIM_CONN_ID


class SIMService:
    """SIM-ICCID导入服务"""

    async def _ensure_pool(self) -> None:
        """确保连接池已注册"""
        pool = db_pool.get_pool(sim_conn_id)
        if pool is not None:
            return
        conn = await conn_controller.get_decrypted_connection(sim_conn_id)
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

    async def _insert_rows(self, stamp: str, rows: List[Tuple[str, str]]) -> int:
        """批量写入临时表"""
        if not rows:
            return 0
        await self._ensure_pool()
        pool = db_pool.get_pool(sim_conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(
                        "INSERT INTO tm_simiccidimp (ImpStamp, SimNumber, ICCID) VALUES (%s, %s, %s)",
                        [(stamp, r[0], r[1]) for r in rows],
                    )
                    await conn.commit()
                    return cur.rowcount or 0
        raise ValueError("不支持的连接池类型")

    async def upload_excel(self, file_bytes: bytes, filename: str) -> str:
        """上传Excel并写入临时表"""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        rows: List[Tuple[str, str]] = []
        if ext in ("xlsx",):
            try:
                import openpyxl  # type: ignore
            except Exception:
                raise ValueError("服务器未安装Excel解析库，请上传CSV或联系管理员安装openpyxl")
            wb = openpyxl.load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
            ws = wb.active
            headers = [str(c.value).strip() if c.value is not None else "" for c in next(ws.iter_rows(max_row=1))]
            if headers != ["SimNumber", "ICCID"]:
                raise ValueError("Excel列名不符合要求，需为SimNumber、ICCID")
            for row in ws.iter_rows(min_row=2):
                sim = str(row[0].value).strip() if row[0].value is not None else ""
                iccid = str(row[1].value).strip() if row[1].value is not None else ""
                if sim or iccid:
                    rows.append((sim, iccid))
        elif ext in ("csv",):
            text = file_bytes.decode("utf-8", errors="ignore")
            reader = csv.reader(BytesIO(text.encode("utf-8")))
            try:
                headers = next(reader)
            except StopIteration:
                headers = []
            headers = [h.strip() for h in headers]
            if headers != ["SimNumber", "ICCID"]:
                raise ValueError("CSV列名不符合要求，需为SimNumber、ICCID")
            for r in reader:
                if not r or len(r) < 2:
                    continue
                sim = (r[0] or "").strip()
                iccid = (r[1] or "").strip()
                if sim or iccid:
                    rows.append((sim, iccid))
        else:
            raise ValueError("仅支持.xlsx或.csv文件")
        stamp = str(uuid.uuid4())
        await self._insert_rows(stamp, rows)
        return stamp

    async def process_tmp(self, stamp: str) -> None:
        """调用存储过程处理临时表数据"""
        await self._ensure_pool()
        pool = db_pool.get_pool(sim_conn_id)
        if pool is None:
            raise ValueError("连接池不存在")
        if isinstance(pool, aiomysql.Pool):
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    try:
                        await cur.execute("CALL proc_ProcessSimIccidByStamp(%s)", (stamp,))
                        await conn.commit()
                    except Exception:
                        await conn.commit()
                        raise
            return
        raise ValueError("不支持的连接池类型")


sim_service = SIMService()
