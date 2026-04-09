import asyncio
from typing import Optional

from app.log import logger
from app.settings.config import settings


def _safe_delay(task_name: str, func, *args) -> Optional[str]:
    try:
        async_result = func.delay(*args)
        task_id = getattr(async_result, "id", None)
        logger.info(f"[Celery] 已提交任务: {task_name}, task_id={task_id}, args={args}")
        return task_id
    except Exception as exc:
        logger.error(f"[Celery] 提交任务失败: {task_name}, error={exc}", exc_info=True)
        return None


def dispatch_report_export(generation_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED:
        return None
    from app.tasks.celery_tasks import export_report_task

    return _safe_delay("dbadmin.report.export", export_report_task, generation_id)


def dispatch_imptask(task_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED:
        return None
    from app.tasks.celery_tasks import process_imptask_task

    return _safe_delay("dbadmin.imptask.process", process_imptask_task, task_id)


def dispatch_notify_report_send(task_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED:
        return None
    from app.tasks.celery_tasks import execute_report_send_task

    return _safe_delay("dbadmin.notify.report_send", execute_report_send_task, task_id)


def dispatch_notify_sql_alert(task_id: int) -> Optional[str]:
    if not settings.CELERY_ENABLED:
        return None
    from app.tasks.celery_tasks import execute_sql_alert_task

    return _safe_delay("dbadmin.notify.sql_alert", execute_sql_alert_task, task_id)


def fallback_async(coro):
    asyncio.create_task(coro)
