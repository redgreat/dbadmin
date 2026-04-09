from app.core.celery_app import celery_app
from app.core.celery_runtime import run_async_with_tortoise


@celery_app.task(name="dbadmin.report.export")
def export_report_task(generation_id: int):
    from app.services.excel_export_service import ExcelExportService

    return run_async_with_tortoise(ExcelExportService().export_report, generation_id)


@celery_app.task(name="dbadmin.imptask.process")
def process_imptask_task(task_id: int):
    from app.services.imptask_processor import process_imptask

    return run_async_with_tortoise(process_imptask, task_id)


@celery_app.task(name="dbadmin.notify.report_send")
def execute_report_send_task(task_id: int):
    from app.services.notify_task_executor import NotifyTaskExecutor

    return run_async_with_tortoise(NotifyTaskExecutor.execute_report_send_task, task_id)


@celery_app.task(name="dbadmin.notify.sql_alert")
def execute_sql_alert_task(task_id: int):
    from app.services.notify_task_executor import NotifyTaskExecutor

    return run_async_with_tortoise(NotifyTaskExecutor.execute_sql_alert_task, task_id)
