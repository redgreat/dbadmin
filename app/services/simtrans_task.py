import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.log import logger
from app.services.celery_dispatcher import dispatch_simtrans_sync
from app.services.simtrans import sim_trans_service


_LOCAL_TASKS: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _local_update(task_id: str, **kwargs):
    task = _LOCAL_TASKS.setdefault(task_id, {"task_id": task_id})
    task.update(kwargs)
    task["updated_at"] = _now()


async def _run_local_sync(task_id: str, receipt_numbers_text: str):
    async def progress_cb(payload: Dict[str, Any]):
        _local_update(task_id, status="running", **payload)

    try:
        _local_update(task_id, status="running", stage="queued", message="任务启动", progress=1)
        result = await sim_trans_service.sync_sim_cards(receipt_numbers_text, progress_cb=progress_cb)
        ok = bool(result.get("success"))
        _local_update(
            task_id,
            status="success" if ok else "failed",
            stage="done" if ok else "failed",
            message=result.get("message", "同步完成"),
            progress=100,
            result=result,
            error=None if ok else result.get("message"),
            finished_at=_now(),
        )
    except Exception as exc:
        logger.error(f"SIM同步后台任务失败: task_id={task_id}, error={exc}", exc_info=True)
        _local_update(
            task_id,
            status="failed",
            stage="failed",
            message=str(exc),
            progress=100,
            error=str(exc),
            finished_at=_now(),
        )


async def submit_simtrans_sync(receipt_numbers_text: str) -> Dict[str, Any]:
    celery_task_id = dispatch_simtrans_sync(receipt_numbers_text)
    if celery_task_id:
        return {
            "task_id": celery_task_id,
            "backend": "celery",
            "status": "queued",
            "message": "同步任务已提交到后台执行",
        }

    task_id = str(uuid.uuid4())
    _LOCAL_TASKS[task_id] = {
        "task_id": task_id,
        "backend": "local",
        "status": "queued",
        "stage": "queued",
        "message": "同步任务已提交到后台执行",
        "progress": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    asyncio.create_task(_run_local_sync(task_id, receipt_numbers_text))
    return _LOCAL_TASKS[task_id]


def _status_from_celery(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        from celery.result import AsyncResult
        from app.core.celery_app import celery_app

        async_result = AsyncResult(task_id, app=celery_app)
        state = async_result.state
        if state == "PENDING":
            return None
        if state in ("STARTED", "PROGRESS"):
            meta = async_result.info if isinstance(async_result.info, dict) else {}
            return {
                "task_id": task_id,
                "backend": "celery",
                "status": "running",
                "stage": meta.get("stage", "running"),
                "message": meta.get("message", "同步任务执行中"),
                "progress": meta.get("progress", 1),
                **meta,
            }
        if state == "SUCCESS":
            result = async_result.result if isinstance(async_result.result, dict) else {}
            ok = bool(result.get("success"))
            return {
                "task_id": task_id,
                "backend": "celery",
                "status": "success" if ok else "failed",
                "stage": "done" if ok else "failed",
                "message": result.get("message", "同步完成"),
                "progress": 100,
                "result": result,
                "error": None if ok else result.get("message"),
            }
        if state == "FAILURE":
            return {
                "task_id": task_id,
                "backend": "celery",
                "status": "failed",
                "stage": "failed",
                "message": str(async_result.info),
                "progress": 100,
                "error": str(async_result.info),
            }
    except Exception as exc:
        logger.warning(f"读取SIM同步Celery任务状态失败: task_id={task_id}, error={exc}")
    return None


def get_simtrans_sync_status(task_id: str) -> Dict[str, Any]:
    if task_id in _LOCAL_TASKS:
        return _LOCAL_TASKS[task_id]

    celery_status = _status_from_celery(task_id)
    if celery_status:
        return celery_status

    return {
        "task_id": task_id,
        "status": "queued",
        "stage": "queued",
        "message": "任务排队中或状态暂不可用",
        "progress": 0,
    }
