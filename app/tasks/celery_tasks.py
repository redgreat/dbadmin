from app.core.celery_app import celery_app
from app.core.celery_runtime import run_async_with_tortoise


@celery_app.task(
    name="dbadmin.report.export",
    bind=True,
    ignore_result=False,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=12,
)
def export_report_task(self, generation_id: int):
    from app.services.excel_export_service import ExcelExportService, RetryableReportError

    try:
        return run_async_with_tortoise(ExcelExportService().export_report, generation_id, True)
    except RetryableReportError as exc:
        countdown = _retry_countdown(self.request.retries)
        if self.request.retries >= self.max_retries:
            run_async_with_tortoise(ExcelExportService().mark_retry_exhausted, generation_id, str(exc))
            raise
        raise self.retry(exc=exc, countdown=countdown)


def _retry_countdown(retries: int) -> int:
    return min(300, 15 * (2 ** retries))


@celery_app.task(
    name="dbadmin.imptask.process",
    bind=True,
    ignore_result=False,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=12,
)
def process_imptask_task(self, task_id: int):
    from app.services.imptask_processor import (
        RetryableImportError,
        mark_imptask_retry_exhausted,
        process_imptask,
    )

    try:
        # #region debug-point C:celery-task-received
        import json, urllib.request, os, time; _p='.dbg/excel-imptask-celery-fail.env'; _u,_s=os.environ.get('DEBUG_SERVER_URL','http://127.0.0.1:7777/event'),os.environ.get('DEBUG_SESSION_ID','excel-imptask-celery-fail'); exec("try:\n with open(_p,encoding='utf-8') as f: c=f.read();\n _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'C','location':'celery_tasks.process_imptask_task','msg':'[DEBUG] celery task received','data':{'request_id':getattr(self.request,'id',None),'task_id':task_id,'retries':getattr(self.request,'retries',None)},'ts':int(time.time()*1000)}).encode(), headers={'Content-Type':'application/json'}), timeout=2).read()
        # #endregion
        return run_async_with_tortoise(process_imptask, task_id, True)
    except RetryableImportError as exc:
        countdown = _retry_countdown(self.request.retries)
        if self.request.retries >= self.max_retries:
            run_async_with_tortoise(mark_imptask_retry_exhausted, task_id, str(exc))
            raise
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    name="dbadmin.imptask.execute",
    bind=True,
    ignore_result=False,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=12,
)
def execute_imptask_sql_task(self, task_id: int, user_id: int, username: str):
    from app.services.imptask_processor import (
        RetryableImportError,
        execute_imptask_sql,
        mark_imptask_execute_retry_exhausted,
    )

    try:
        # #region debug-point C:celery-task-received
        import json, urllib.request, os, time; _p='.dbg/excel-imptask-celery-fail.env'; _u,_s=os.environ.get('DEBUG_SERVER_URL','http://127.0.0.1:7777/event'),os.environ.get('DEBUG_SESSION_ID','excel-imptask-celery-fail'); exec("try:\n with open(_p,encoding='utf-8') as f: c=f.read();\n _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'C','location':'celery_tasks.execute_imptask_sql_task','msg':'[DEBUG] celery task received','data':{'request_id':getattr(self.request,'id',None),'task_id':task_id,'user_id':user_id,'retries':getattr(self.request,'retries',None)},'ts':int(time.time()*1000)}).encode(), headers={'Content-Type':'application/json'}), timeout=2).read()
        # #endregion
        return run_async_with_tortoise(execute_imptask_sql, task_id, user_id, username, True)
    except RetryableImportError as exc:
        countdown = _retry_countdown(self.request.retries)
        if self.request.retries >= self.max_retries:
            run_async_with_tortoise(mark_imptask_execute_retry_exhausted, task_id, str(exc))
            raise
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        # #region debug-point D:celery-task-exception
        import json, urllib.request, os, time; _p='.dbg/excel-imptask-celery-fail.env'; _u,_s=os.environ.get('DEBUG_SERVER_URL','http://127.0.0.1:7777/event'),os.environ.get('DEBUG_SESSION_ID','excel-imptask-celery-fail'); exec("try:\n with open(_p,encoding='utf-8') as f: c=f.read();\n _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'D','location':'celery_tasks.execute_imptask_sql_task','msg':'[DEBUG] celery task exception','data':{'request_id':getattr(self.request,'id',None),'task_id':task_id,'error':str(exc)},'ts':int(time.time()*1000)}).encode(), headers={'Content-Type':'application/json'}), timeout=2).read()
        # #endregion
        raise


@celery_app.task(
    name="dbadmin.excelimp.generate",
    bind=True,
    ignore_result=False,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=12,
)
def generate_excelimp_sql_task(self, file_path: str, filename: str, db_type: str, stamp: str):
    from app.services.excelimp_service import generate_sql_file_task
    from app.services.imptask_processor import RetryableImportError

    try:
        return generate_sql_file_task(file_path, filename, db_type, stamp)
    except (MemoryError, OSError, TimeoutError, ConnectionError) as exc:
        countdown = _retry_countdown(self.request.retries)
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(exc=RetryableImportError(str(exc)), countdown=countdown)


@celery_app.task(
    name="dbadmin.excelimp.execute",
    bind=True,
    ignore_result=False,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=12,
)
def execute_excelimp_sql_task(self, stamp: str, target_conn_id: int):
    from app.services.excelimp_service import execute_sql_file_task
    from app.services.imptask_processor import RetryableImportError

    try:
        return run_async_with_tortoise(execute_sql_file_task, stamp, target_conn_id)
    except (MemoryError, OSError, TimeoutError, ConnectionError) as exc:
        countdown = _retry_countdown(self.request.retries)
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(exc=RetryableImportError(str(exc)), countdown=countdown)


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
