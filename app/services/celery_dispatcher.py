import asyncio
import time
from typing import Optional

from app.log import logger
from app.settings.config import settings

_WORKER_PROBE_CACHE = {"checked_at": 0.0, "alive": False}


def _has_active_worker() -> bool:
    if not settings.CELERY_REQUIRE_WORKER:
        return True

    now = time.time()
    if now - _WORKER_PROBE_CACHE["checked_at"] < 5:
        return _WORKER_PROBE_CACHE["alive"]

    try:
        from app.core.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=settings.CELERY_WORKER_PROBE_TIMEOUT)
        ping_result = inspect.ping() or {}
        alive = bool(ping_result)
    except Exception:
        alive = False

    _WORKER_PROBE_CACHE["checked_at"] = now
    _WORKER_PROBE_CACHE["alive"] = alive
    if not alive:
        logger.warning("[Celery] 未检测到可用Worker，回退本地异步执行")
    return alive


def _safe_delay(task_name: str, func, *args) -> Optional[str]:
    try:
        async_result = func.apply_async(args=args, retry=False)
        task_id = getattr(async_result, "id", None)
        logger.info(f"[Celery] 已提交任务: {task_name}, task_id={task_id}, args={args}")
        return task_id
    except Exception as exc:
        logger.error(f"[Celery] 提交任务失败: {task_name}, error={exc}", exc_info=True)
        return None


def dispatch_report_export(generation_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED or not _has_active_worker():
        return None
    from app.tasks.celery_tasks import export_report_task

    return _safe_delay("dbadmin.report.export", export_report_task, generation_id)


def dispatch_imptask(task_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED or not _has_active_worker():
        return None
    from app.tasks.celery_tasks import process_imptask_task

    return _safe_delay("dbadmin.imptask.process", process_imptask_task, task_id)


def dispatch_notify_report_send(task_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED or not _has_active_worker():
        return None
    from app.tasks.celery_tasks import execute_report_send_task

    return _safe_delay("dbadmin.notify.report_send", execute_report_send_task, task_id)


def dispatch_notify_sql_alert(task_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED or not _has_active_worker():
        return None
    from app.tasks.celery_tasks import execute_sql_alert_task

    return _safe_delay("dbadmin.notify.sql_alert", execute_sql_alert_task, task_id)


def fallback_async(coro):
    asyncio.create_task(coro)
