from app.core.celery_app import celery_app
from app.core.celery_runtime import run_async_with_tortoise


@celery_app.task(name="dbadmin.report.export", time_limit=7200, soft_time_limit=6300)
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


@celery_app.task(name="dbadmin.simtrans.sync", bind=True, ignore_result=False, time_limit=7200, soft_time_limit=6300)
def sync_simtrans_task(self, receipt_numbers_text: str):
    from app.log import logger
    from app.services.simtrans import sim_trans_service

    async def runner():
        async def progress_cb(payload):
            self.update_state(state="PROGRESS", meta=payload)

        try:
            result = await sim_trans_service.sync_sim_cards(receipt_numbers_text, progress_cb=progress_cb)
            await progress_cb({
                "stage": "done",
                "message": result.get("message", "同步完成"),
                "progress": 100,
                "result": result,
            })
            return result
        except Exception as exc:
            logger.error(f"SIM同步Celery任务失败: task_id={self.request.id}, error={exc}", exc_info=True)
            await progress_cb({
                "stage": "failed",
                "message": str(exc),
                "progress": 100,
                "error": str(exc),
            })
            raise

    return run_async_with_tortoise(runner)
