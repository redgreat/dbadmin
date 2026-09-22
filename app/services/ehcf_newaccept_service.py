"""
壹好车服-车务待办人刷新服务
上传固定模板Excel(订单号/旧代办人工号/新代办人工号)，按批次ImpStamp写入已部署的
固定临时表 tm_newaccept，再调用存储过程 proc_VhsAcceptRefesh(批次Id) 刷新业务表。
"""
import asyncio
import logging
import uuid
from datetime import datetime
from io import BytesIO

import aiomysql
import openpyxl

from app.services.db_pool import db_pool
from app.settings.config import settings

logger = logging.getLogger(__name__)

_ehcf_conn_id = None

# 固定临时表为全局单例，预览/执行/清理全程互斥，防止并发互相覆盖
_temp_table_lock = asyncio.Lock()

# 固定模板表头（顺序对应Excel列）
TEMPLATE_HEADERS = ["订单号", "旧代办人工号", "新代办人工号"]

# 固定临时表名（与存储过程 proc_VhsAcceptRefesh 约定一致，表已部署在生产库）
TEMP_TABLE_NAME = "tm_newaccept"

# 固定存储过程名（入参为批次 ImpStamp）
PROC_NAME = "proc_VhsAcceptRefesh"


async def _get_conn_id():
    global _ehcf_conn_id
    if _ehcf_conn_id is None:
        _ehcf_conn_id = await settings.EHCF_CONN_ID()
    return _ehcf_conn_id


def build_template_bytes() -> bytes:
    """生成固定模板Excel（表头：订单号/旧代办人工号/新代办人工号 + 示例行）"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "车务待办人刷新"
    ws.append(TEMPLATE_HEADERS)
    ws.append(["YH2026092200001", "ZhangSan", "LiSi"])
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def parse_excel(content: bytes) -> list[tuple[str, str, str]]:
    """解析固定模板Excel，返回 (AppCode, OAcceptCode, NAcceptCode) 列表。

    校验表头、行数与必填列，格式非法时抛出 ValueError。
    """
    try:
        wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"Excel文件解析失败: {e!s}")

    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        raise ValueError("Excel文件内容为空")

    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    if header[:3] != TEMPLATE_HEADERS:
        raise ValueError(f"表头格式不符，要求固定为: {TEMPLATE_HEADERS}，实际为: {header[:3]}")

    data: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for idx, row in enumerate(rows[1:], start=2):
        if row is None or all(c is None for c in row):
            continue
        app_code = str(row[0]).strip() if row[0] is not None else ""
        old_code = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        new_code = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
        if not app_code or not old_code or not new_code:
            raise ValueError(f"第{idx}行存在空列: {row}")
        if app_code in seen:
            raise ValueError(f"第{idx}行订单号重复: {app_code}")
        seen.add(app_code)
        data.append((app_code, old_code, new_code))

    if not data:
        raise ValueError("Excel中没有有效数据行")
    return data


async def _prepare_pool() -> aiomysql.Pool:
    conn_id = await _get_conn_id()
    if conn_id in (None, 0):
        raise ValueError("未找到EHCF数据库连接（连接别名 EHCF_CONN 不存在或未启用）")
    await db_pool.ensure_pool(conn_id)
    pool = db_pool.get_pool(conn_id)
    if pool is None:
        raise ValueError("EHCF连接池不存在")
    if not isinstance(pool, aiomysql.Pool):
        raise ValueError("EHCF连接不是MySQL类型，暂不支持")
    return pool


async def _write_temp_table(
    pool: aiomysql.Pool, data: list[tuple[str, str, str]], imp_stamp: str
) -> int:
    """向固定临时表 tm_newaccept 按批次 ImpStamp 写入数据。

    按新代办人工号解析用户信息（仅写入新工号能解析到用户信息的行），
    全部打上当前批次 ImpStamp。返回实际写入行数。
    """
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                # 新代办人工号解析用户信息（LoginName -> UserCenterId/UserName）
                new_codes = sorted({item[2] for item in data})
                placeholders = ",".join(["%s"] * len(new_codes))
                await cur.execute(
                    f"""
                    SELECT LoginName, MAX(UserCenterId), MAX(UserName)
                    FROM tb_userinfo
                    WHERE LoginName IN ({placeholders}) AND Deleted=0
                    GROUP BY LoginName
                    """,
                    new_codes,
                )
                user_map: dict[str, tuple[str, str]] = {}
                for login, user_center_id, user_name in await cur.fetchall():
                    user_map[login] = (str(user_center_id or ""), str(user_name or ""))

                written = 0
                for app_code, old_code, new_code in data:
                    resolved = user_map.get(new_code)
                    if not resolved or not resolved[0]:
                        logger.warning(
                            f"新代办人工号 {new_code} 未解析到用户信息，跳过 AppCode={app_code}"
                        )
                        continue
                    await cur.execute(
                        f"""
                        INSERT INTO {TEMP_TABLE_NAME} (ImpStamp, AppCode, OAcceptCode, NAcceptCode, NAcceptId, NAcceptName)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (imp_stamp, app_code, old_code, new_code, resolved[0], resolved[1]),
                    )
                    written += 1
            await conn.commit()
            return written
        except Exception:
            await conn.rollback()
            raise


async def _call_refresh_procedure(pool: aiomysql.Pool, imp_stamp: str) -> dict:
    """调用存储过程 proc_VhsAcceptRefesh(imp_stamp) 刷新业务表。

    存储过程返回结果集 ErType/ErMessage；成功（ErType=0）后清理残留数据，
    失败时临时表数据保留以便排查或重试。
    """
    result_type, result_msg = None, None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"CALL {PROC_NAME}(%s)", (imp_stamp,))
            row = await cur.fetchone()
            if row:
                result_type, result_msg = row[0], row[1]

    # ErType: 0=成功, -1=失败; 存储过程异常路径无结果集返回，视为失败
    success = result_type is not None and int(result_type) == 0
    message = str(result_msg or ("刷新生效成功" if success else "刷新执行失败"))
    if success:
        await _cleanup_temp_rows(pool, imp_stamp)
    return {"success": success, "message": message}


async def _cleanup_temp_rows(pool: aiomysql.Pool, imp_stamp: str) -> None:
    """删除临时表中指定批次的残留数据（存储过程成功/失败路径都已尝试删除）"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"DELETE FROM {TEMP_TABLE_NAME} WHERE ImpStamp=%s", (imp_stamp,)
            )


class EhcfNewAcceptService:
    """壹好车服-车务待办人刷新"""

    async def upload_and_refresh(self, content: bytes, execute: bool = False) -> dict:
        """解析Excel写入临时表；execute=True 时额外调用存储过程刷新业务表。"""
        data = parse_excel(content)
        async with _temp_table_lock:
            return await self._upload_and_refresh_locked(data, execute)

    async def _upload_and_refresh_locked(
        self, data: list[tuple[str, str, str]], execute: bool
    ) -> dict:
        pool = await _prepare_pool()
        imp_stamp = str(uuid.uuid4())

        written = await _write_temp_table(pool, data, imp_stamp)
        if written == 0:
            raise ValueError("没有可刷新的有效数据（新代办人工号均未解析到用户信息）")

        result = {
            "success": True,
            "executed": execute,
            "table_name": TEMP_TABLE_NAME,
            "total": len(data),
            "written": written,
            "skipped": len(data) - written,
            "batch_id": imp_stamp,
            "batch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if execute:
            proc_result = await _call_refresh_procedure(pool, imp_stamp)
            result["executed"] = True
            result["success"] = proc_result["success"]
            result["message"] = (
                f"已写入临时表 {TEMP_TABLE_NAME}（{written}/{len(data)} 条，批次 {imp_stamp}），"
                + proc_result["message"]
            )
        else:
            result[
                "message"
            ] = f"已写入临时表 {TEMP_TABLE_NAME}（{written}/{len(data)} 条），存储过程未执行"

        return result

    async def preview(self, content: bytes) -> dict:
        """上传预览：解析Excel + 按批次写入临时表 + 刷新前统计SQL（不修改业务表）"""
        data = parse_excel(content)
        async with _temp_table_lock:
            pool = await _prepare_pool()
            imp_stamp = str(uuid.uuid4())
            written = await _write_temp_table(pool, data, imp_stamp)

            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        f"""
                        SELECT COUNT(1)
                        FROM {TEMP_TABLE_NAME} a
                        JOIN tb_workorderinfo b
                          ON b.AppCode=a.AppCode AND b.WorkStatus=6 AND b.Deleted=0
                        JOIN workflowruntimeitems c
                          ON c.TargetEntityId=b.Id AND c.Deleted=0
                        JOIN workflowruntimesteps d
                          ON d.RuntimeItemId=c.Id AND d.Status IN ('PROCESSING','SUSPENDED')
                          AND d.Name='提交处理结果' AND d.Deleted=0
                        JOIN workflowruntimeactors e
                          ON e.RuntimeStepId=d.Id AND e.Status='PROCESSING' AND e.Deleted=0
                        WHERE a.ImpStamp=%s
                        """,
                        (imp_stamp,),
                    )
                    matched_workflow = (await cur.fetchone())[0] or 0

                    await cur.execute(
                        f"""
                        SELECT COUNT(1)
                        FROM {TEMP_TABLE_NAME} a
                        JOIN tb_workorderinfo b
                          ON b.AppCode=a.AppCode AND b.WorkStatus=6 AND b.Deleted=0
                        JOIN tb_operatinginfo c
                          ON c.WorkOrderId=b.Id AND c.Deleted=0
                        WHERE a.ImpStamp=%s
                        """,
                        (imp_stamp,),
                    )
                    operating_info = (await cur.fetchone())[0] or 0

        return {
            "success": written > 0,
            "table_name": TEMP_TABLE_NAME,
            "total": len(data),
            "written": written,
            "skipped": len(data) - written,
            "batch_id": imp_stamp,
            "matched_workflow": matched_workflow,
            "operating_info": operating_info,
            "message": (
                f"解析 {len(data)} 条，写入 {written} 条，"
                f"命中工作流待办 {matched_workflow} 条，工单操作记录 {operating_info} 条"
            ),
        }

    async def refresh_only(self, batch_id: str) -> dict:
        """基于已写入的临时表按批次调用存储过程刷新业务表（加锁防止并发）"""
        batch_id = (batch_id or "").strip()
        if not batch_id:
            raise ValueError("缺少批次Id（batch_id），无法刷新")
        async with _temp_table_lock:
            pool = await _prepare_pool()
            await self._check_batch_exists(pool, batch_id)
            proc_result = await _call_refresh_procedure(pool, batch_id)
        if not proc_result["success"]:
            raise ValueError(f"刷新执行失败: {proc_result['message']}")
        return proc_result

    @staticmethod
    async def _check_batch_exists(pool: aiomysql.Pool, batch_id: str) -> None:
        """确认批次数据仍在临时表中，避免误刷已清理的批次"""
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT COUNT(1) FROM {TEMP_TABLE_NAME} WHERE ImpStamp=%s",
                    (batch_id,),
                )
                count = (await cur.fetchone())[0] or 0
        if count == 0:
            raise ValueError(f"批次 {batch_id} 不存在或已被清理，请重新预览")

    async def drop_temp_table(self, batch_id: str | None = None) -> bool:
        """清理固定临时表：传 batch_id 只删该批次，否则清空全表"""
        async with _temp_table_lock:
            pool = await _prepare_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if batch_id:
                        await cur.execute(
                            f"DELETE FROM {TEMP_TABLE_NAME} WHERE ImpStamp=%s",
                            (batch_id,),
                        )
                    else:
                        await cur.execute(f"DELETE FROM {TEMP_TABLE_NAME}")
        return True


ehcf_newaccept_service = EhcfNewAcceptService()
