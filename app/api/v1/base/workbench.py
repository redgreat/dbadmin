from fastapi import APIRouter

from app.core.dependency import DependAuth
from app.models import (
    AlertSendLog,
    DBConnection,
    Dict,
    OpLog,
    ReportGeneration,
    Task,
    TaskLog,
)
from app.models.task_notify import NotifyTaskRunLog, ReportSendTask, SqlAlertTask
from app.schemas.base import Success

router = APIRouter()

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _format_task_log(task: Task | None, log: TaskLog) -> dict:
    return {
        "task_id": log.task_id,
        "task_name": task.name if task else None,
        "status": log.status,
        "start_time": log.start_time.strftime(DATE_FORMAT) if log.start_time else None,
        "end_time": log.end_time.strftime(DATE_FORMAT) if log.end_time else None,
        "duration": log.duration,
        "error": log.error,
    }


@router.get("/workbench/summary", summary="工作台概览", dependencies=[DependAuth])
async def get_workbench_summary():
    """
    聚合工作台首页数据：各模块数量统计 + 最近任务日志 + 最近告警发送记录。
    """
    task_count = await Task.all().count()
    task_enabled_count = await Task.filter(status=True).count()

    task_log_count = await TaskLog.all().count()
    task_log_failed_count = await TaskLog.filter(status="failed").count()
    task_log_running_count = await TaskLog.filter(status="running").count()

    report_send_task_count = await ReportSendTask.all().count()
    sql_alert_task_count = await SqlAlertTask.all().count()
    notify_log_count = await NotifyTaskRunLog.all().count()

    alert_log_count = await AlertSendLog.all().count()
    alert_log_failed_count = await AlertSendLog.filter(send_status=0).count()

    oplog_count = await OpLog.all().count()
    report_generation_count = await ReportGeneration.filter_active().count()

    conn_count = await DBConnection.all().count()
    dict_count = await Dict.filter(deleted=False).count()

    # 最近任务日志（按 start_time 倒序，限10条）
    task_logs = await TaskLog.all().order_by("-start_time").limit(10)
    task_map = {t.id: t for t in await Task.all()}
    recent_task_logs = [
        _format_task_log(task_map.get(log.task_id), log) for log in task_logs
    ]

    # 最近告警发送记录（限5条）
    recent_alert_logs = await AlertSendLog.all().order_by("-sent_at").limit(5)
    alert_items = [
        {
            "sender_name": log.sender_name,
            "channel_type": log.channel_type,
            "send_status": log.send_status,
            "sent_at": log.sent_at.strftime(DATE_FORMAT),
            "alert_text": (log.alert_text or "")[:200],
        }
        for log in recent_alert_logs
    ]

    data = {
        "counts": {
            "task": task_count,
            "task_enabled": task_enabled_count,
            "task_log": task_log_count,
            "task_log_failed": task_log_failed_count,
            "task_log_running": task_log_running_count,
            "report_send_task": report_send_task_count,
            "sql_alert_task": sql_alert_task_count,
            "notify_log": notify_log_count,
            "alert_log": alert_log_count,
            "alert_log_failed": alert_log_failed_count,
            "oplog": oplog_count,
            "report_generation": report_generation_count,
            "conn": conn_count,
            "dict": dict_count,
        },
        "recent_task_logs": recent_task_logs,
        "recent_alert_logs": alert_items,
    }
    return Success(data=data)
