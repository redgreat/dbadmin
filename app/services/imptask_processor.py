"""
Excel导入任务后台处理器
"""
import os
import asyncio
from datetime import datetime
from app.models.imptask import ImpTask
from app.services.excelimp_service import generate_sql_file_from_excel
from app.services.sql_apply_service import calc_sha256, execute_sql_on_connection
from app.services.celery_dispatcher import dispatch_imptask, dispatch_imptask_execute
from app.log import logger


RETRYABLE_ERRORS = (MemoryError, OSError, TimeoutError, ConnectionError)
_LOCAL_PROCESS_TASKS: dict[int, asyncio.Task] = {}
_LOCAL_EXECUTE_TASKS: dict[int, asyncio.Task] = {}


class RetryableImportError(Exception):
    """导入任务可自动重试的临时错误。"""


class ManualStopError(Exception):
    """导入任务被手动停止时抛出的异常。"""


def _register_local_task(task_map: dict[int, asyncio.Task], task_id: int, bg_task: asyncio.Task):
    task_map[task_id] = bg_task

    def _cleanup(_):
        current = task_map.get(task_id)
        if current is bg_task:
            task_map.pop(task_id, None)

    bg_task.add_done_callback(_cleanup)


def cancel_local_imptask_process(task_id: int) -> bool:
    bg_task = _LOCAL_PROCESS_TASKS.get(task_id)
    if not bg_task or bg_task.done():
        return False
    bg_task.cancel()
    return True


def cancel_local_imptask_execute(task_id: int) -> bool:
    bg_task = _LOCAL_EXECUTE_TASKS.get(task_id)
    if not bg_task or bg_task.done():
        return False
    bg_task.cancel()
    return True


async def _raise_if_process_stop_requested(task_id: int):
    task = await ImpTask.get_or_none(id=task_id)
    if task and task.stop_requested:
        raise ManualStopError("任务已手动停止")


async def _raise_if_execute_stop_requested(task_id: int):
    task = await ImpTask.get_or_none(id=task_id)
    if task and task.execute_stop_requested:
        raise ManualStopError("导入执行已手动停止")


async def submit_imptask(task_id: int):
    """
    提交Excel导入任务到后台处理

    Args:
        task_id: 任务ID
    """
    celery_task_id = dispatch_imptask(task_id)
    if celery_task_id:
        await _update_task_status(
            task_id,
            status="pending",
            progress=0,
            message="任务已进入后台队列，等待Worker处理",
            process_celery_task_id=celery_task_id,
            stop_requested=False,
            stopped_at=None,
        )
        logger.info(f"任务已提交到Celery后台处理: task_id={task_id}, celery_task_id={celery_task_id}")
        return

    await _update_task_status(
        task_id,
        status="pending",
        progress=0,
        message="任务已进入本地后台队列",
        process_celery_task_id=None,
        stop_requested=False,
        stopped_at=None,
    )
    bg_task = asyncio.create_task(process_imptask(task_id))
    _register_local_task(_LOCAL_PROCESS_TASKS, task_id, bg_task)
    logger.info(f"Celery未启用或不可用，任务已提交到本地后台处理: {task_id}")


async def process_imptask(task_id: int, raise_retryable: bool = False):
    """
    异步处理Excel导入任务

    Args:
        task_id: 任务ID
    """
    try:
        await _raise_if_process_stop_requested(task_id)
        # 获取任务
        task = await ImpTask.get(id=task_id)

        if not task:
            logger.error(f"任务不存在: {task_id}")
            return

        # 更新任务状态为处理中
        task.status = "processing"
        task.started_at = datetime.now()
        task.progress = 10
        task.message = "开始处理Excel文件..."
        task.stop_requested = False
        task.stopped_at = None
        await task.save(update_fields=["status", "started_at", "progress", "message", "stop_requested", "stopped_at"])

        logger.info(f"开始处理Excel导入任务: {task_id}, 文件: {task.filename}")

        # 检查文件是否存在
        if not os.path.exists(task.file_path):
            raise FileNotFoundError(f"文件不存在: {task.file_path}")

        await _raise_if_process_stop_requested(task_id)

        # 更新进度: 检查文件
        task.progress = 20
        task.message = "正在检查Excel文件..."
        await task.save(update_fields=["progress", "message"])

        # 更新进度: 解析Excel并生成SQL文件
        task.progress = 40
        task.message = "正在解析Excel并生成SQL文件..."
        await task.save(update_fields=["progress", "message"])

        # 生成SQL文件路径
        sql_filename = f"sql_{task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        sql_file_path = os.path.join(os.path.dirname(task.file_path), sql_filename)

        sql_meta = await asyncio.to_thread(
            generate_sql_file_from_excel,
            task.file_path,
            task.filename,
            task.db_type,
            sql_file_path,
        )

        await _raise_if_process_stop_requested(task_id)

        task.progress = 90
        task.message = "SQL文件生成完成，正在保存任务结果..."
        await task.save(update_fields=["progress", "message"])

        # 更新任务状态为完成
        task.status = "completed"
        task.progress = 100
        task.message = "SQL生成完成"
        task.sql_file_path = sql_file_path
        task.sql_file_size = os.path.getsize(sql_file_path)
        task.sql_sha256 = sql_meta["sql_sha256"]
        task.completed_at = datetime.now()
        task.process_celery_task_id = None
        task.stop_requested = False
        await task.save()

        logger.info(
            f"Excel导入任务完成: {task_id}, SQL文件: {sql_filename}, "
            f"rows={sql_meta.get('row_count')}, table={sql_meta.get('table_name')}"
        )

    except asyncio.CancelledError:
        await _mark_task_manual_stopped(task_id, target="process")
        raise
    except ManualStopError:
        await _mark_task_manual_stopped(task_id, target="process")
        return
    except Exception as e:
        logger.error(f"Excel导入任务失败: {task_id}, 错误: {str(e)}", exc_info=True)
        if raise_retryable and isinstance(e, RETRYABLE_ERRORS):
            await _update_task_status(
                task_id,
                status="pending",
                message=f"处理遇到临时错误，等待自动重试: {str(e)[:200]}",
            )
            raise RetryableImportError(str(e)) from e
        await _update_task_failed(task_id, str(e))


async def _update_task_failed(task_id: int, error_message: str):
    """更新任务失败状态"""
    try:
        task = await ImpTask.get(id=task_id)
        if task.status == "manual_stopped":
            return
        task.status = "failed"
        task.progress = min(task.progress or 0, 99)
        task.message = f"处理失败: {error_message[:450]}"
        task.error_message = error_message
        task.completed_at = datetime.now()
        task.process_celery_task_id = None
        task.stop_requested = False
        await task.save()
    except Exception as save_error:
        logger.error(f"更新任务失败状态时出错: {save_error}")


async def _update_task_status(task_id: int, **kwargs):
    try:
        task = await ImpTask.get(id=task_id)
        for key, value in kwargs.items():
            setattr(task, key, value)
        await task.save(update_fields=list(kwargs.keys()))
    except Exception as save_error:
        logger.error(f"更新任务状态时出错: task_id={task_id}, error={save_error}")


async def mark_imptask_retry_exhausted(task_id: int, error_message: str):
    await _update_task_failed(task_id, f"自动重试已耗尽: {error_message}")


async def mark_imptask_execute_retry_exhausted(task_id: int, error_message: str):
    try:
        task = await ImpTask.get(id=task_id)
        if task.execute_status == "manual_stopped":
            return
        task.execute_status = "failed"
        task.execute_message = f"自动重试已耗尽: {error_message[:450]}"
        task.executed_at = datetime.now()
        task.execute_celery_task_id = None
        task.execute_stop_requested = False
        await task.save(update_fields=["execute_status", "execute_message", "executed_at", "execute_celery_task_id", "execute_stop_requested"])
    except Exception as save_error:
        logger.error(f"更新导入执行重试耗尽状态时出错: task_id={task_id}, error={save_error}")


async def submit_imptask_execute(task_id: int, user_id: int, username: str):
    task = await ImpTask.get(id=task_id)
    task.execute_status = "processing"
    task.execute_message = "导入执行已进入后台队列，等待Worker处理"
    task.executed_at = datetime.now()
    task.executor_user_id = user_id
    task.executor_username = username
    task.execute_stop_requested = False
    task.stopped_at = None
    await task.save(update_fields=[
        "execute_status",
        "execute_message",
        "executed_at",
        "executor_user_id",
        "executor_username",
        "execute_stop_requested",
        "stopped_at",
    ])

    celery_task_id = dispatch_imptask_execute(task_id, user_id, username)
    if celery_task_id:
        task.execute_celery_task_id = celery_task_id
        await task.save(update_fields=["execute_celery_task_id"])
        logger.info(f"导入执行任务已提交到Celery: task_id={task_id}, celery_task_id={celery_task_id}")
        return celery_task_id

    task.execute_celery_task_id = None
    await task.save(update_fields=["execute_celery_task_id"])
    bg_task = asyncio.create_task(execute_imptask_sql(task_id, user_id, username))
    _register_local_task(_LOCAL_EXECUTE_TASKS, task_id, bg_task)
    logger.info(f"Celery未启用或不可用，导入执行任务已提交到本地后台: task_id={task_id}")
    return None


async def execute_imptask_sql(
    task_id: int,
    user_id: int,
    username: str,
    raise_retryable: bool = False,
):
    task = await ImpTask.get(id=task_id)
    if task.status != "completed":
        raise ValueError("任务未完成，不能执行")
    if not task.sql_file_path or not os.path.exists(task.sql_file_path):
        raise FileNotFoundError("SQL文件不存在")
    if not task.target_conn_id:
        raise ValueError("任务未配置目标连接")

    try:
        await _raise_if_execute_stop_requested(task_id)
        task.execute_status = "processing"
        task.execute_message = "正在读取SQL文件"
        task.executed_at = datetime.now()
        task.executor_user_id = user_id
        task.executor_username = username
        await task.save(update_fields=[
            "execute_status",
            "execute_message",
            "executed_at",
            "executor_user_id",
            "executor_username",
        ])

        with open(task.sql_file_path, "r", encoding="utf-8") as file_obj:
            sql_text = file_obj.read()

        current_sha = calc_sha256(sql_text)
        if task.sql_sha256 and task.sql_sha256 != current_sha:
            raise ValueError("SQL文件摘要校验失败，疑似被篡改")

        async def progress_cb(done: int, total: int, _stmt: str):
            await _raise_if_execute_stop_requested(task_id)
            if total <= 0:
                return
            percent = int(done / total * 100)
            task.execute_message = f"导入执行中: 已执行 {done}/{total} 条SQL"
            await task.save(update_fields=["execute_message"])
            logger.info(f"导入执行进度: task_id={task_id}, {done}/{total}, {percent}%")

        result = await execute_sql_on_connection(task.target_conn_id, sql_text, progress_cb=progress_cb)
        await _raise_if_execute_stop_requested(task_id)
        task.execute_status = "success"
        task.execute_message = f"执行成功，共执行 {result['executed_count']} 条语句"
        task.executed_at = datetime.now()
        task.executor_user_id = user_id
        task.executor_username = username
        task.execute_celery_task_id = None
        task.execute_stop_requested = False
        await task.save(update_fields=[
            "execute_status",
            "execute_message",
            "executed_at",
            "executor_user_id",
            "executor_username",
            "execute_celery_task_id",
            "execute_stop_requested",
        ])
        logger.info(f"导入执行完成: task_id={task_id}, executed_count={result['executed_count']}")
        return result
    except asyncio.CancelledError:
        await _mark_task_manual_stopped(task_id, target="execute")
        raise
    except ManualStopError:
        await _mark_task_manual_stopped(task_id, target="execute")
        return None
    except Exception as exc:
        logger.error(f"导入执行失败: task_id={task_id}, error={exc}", exc_info=True)
        if raise_retryable and isinstance(exc, RETRYABLE_ERRORS):
            task.execute_status = "processing"
            task.execute_message = f"导入执行遇到临时错误，等待自动重试: {str(exc)[:200]}"
            await task.save(update_fields=["execute_status", "execute_message"])
            raise RetryableImportError(str(exc)) from exc

        task.execute_status = "failed"
        task.execute_message = str(exc)[:500]
        task.executed_at = datetime.now()
        task.executor_user_id = user_id
        task.executor_username = username
        task.execute_celery_task_id = None
        task.execute_stop_requested = False
        await task.save(update_fields=[
            "execute_status",
            "execute_message",
            "executed_at",
            "executor_user_id",
            "executor_username",
            "execute_celery_task_id",
            "execute_stop_requested",
        ])
        raise


async def _mark_task_manual_stopped(task_id: int, target: str):
    task = await ImpTask.get_or_none(id=task_id)
    if not task:
        return
    task.stopped_at = datetime.now()
    if target == "execute":
        task.execute_status = "manual_stopped"
        task.execute_message = "任务已手动停止"
        task.execute_stop_requested = False
        task.execute_celery_task_id = None
        task.executed_at = datetime.now()
        await task.save(update_fields=[
            "stopped_at",
            "execute_status",
            "execute_message",
            "execute_stop_requested",
            "execute_celery_task_id",
            "executed_at",
        ])
        return

    task.status = "manual_stopped"
    task.message = "任务已手动停止"
    task.stop_requested = False
    task.process_celery_task_id = None
    task.completed_at = datetime.now()
    await task.save(update_fields=[
        "stopped_at",
        "status",
        "message",
        "stop_requested",
        "process_celery_task_id",
        "completed_at",
    ])
