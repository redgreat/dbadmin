import asyncio
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from tortoise.expressions import Q

from app.models.alert import AlertSender
from app.models.conn import DBConnection
from app.models.report import ReportConfig
from app.models.task_notify import NotifyTaskRunLog, ReportSendTask, SqlAlertTask
from app.schemas.task_notify import (
    ReportSendTaskCreate,
    ReportSendTaskUpdate,
    SqlAlertTaskCreate,
    SqlAlertTaskUpdate,
)
from app.services.notify_task_executor import NotifyTaskExecutor
from app.services.report_service import ReportService
from app.services.task_scheduler import scheduler


class TaskNotifyController:
    @staticmethod
    async def list_report_send_tasks(page: int, page_size: int, task_name: Optional[str], status: Optional[bool]):
        query = ReportSendTask.all().prefetch_related("report_config", "sender")
        if task_name:
            query = query.filter(task_name__icontains=task_name)
        if status is not None:
            query = query.filter(status=status)
        total = await query.count()
        items = await query.order_by("-id").offset((page - 1) * page_size).limit(page_size)
        data = []
        for item in items:
            item_dict = await item.to_dict()
            report_config = item.report_config
            sender = item.sender
            item_dict["report_config_name"] = report_config.report_name if report_config else ""
            item_dict["sender_name"] = sender.sender_name if sender else ""
            data.append(item_dict)
        return total, data

    @staticmethod
    async def create_report_send_task(task_in: ReportSendTaskCreate, user_id: int):
        report_config = await ReportConfig.get_or_none(id=task_in.report_config_id, deleted=0)
        if not report_config:
            raise HTTPException(status_code=400, detail="报表配置不存在")
        sender = await AlertSender.get_or_none(id=task_in.sender_id, channel_type="wechat_group")
        if not sender:
            raise HTTPException(status_code=400, detail="发送人不存在或非企业微信群类型")
        task = await ReportSendTask.create(**task_in.model_dump(), created_by=user_id, updated_by=user_id)
        if task.status:
            await scheduler.add_report_send_job(task)
        return task

    @staticmethod
    async def update_report_send_task(task_in: ReportSendTaskUpdate, user_id: int):
        task = await ReportSendTask.get_or_none(id=task_in.id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        update_data = task_in.model_dump(exclude_unset=True, exclude={"id"})
        if "report_config_id" in update_data:
            report_config = await ReportConfig.get_or_none(id=update_data["report_config_id"], deleted=0)
            if not report_config:
                raise HTTPException(status_code=400, detail="报表配置不存在")
        if "sender_id" in update_data:
            sender = await AlertSender.get_or_none(id=update_data["sender_id"], channel_type="wechat_group")
            if not sender:
                raise HTTPException(status_code=400, detail="发送人不存在或非企业微信群类型")

        update_data["updated_by"] = user_id
        old_status = task.status
        await task.update_from_dict(update_data).save()

        if old_status != task.status:
            if task.status:
                await scheduler.add_report_send_job(task)
            else:
                await scheduler.remove_report_send_job(task.id)
        elif task.status and ("cron" in update_data):
            await scheduler.add_report_send_job(task)
        return task

    @staticmethod
    async def delete_report_send_task(task_id: int):
        task = await ReportSendTask.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        await scheduler.remove_report_send_job(task_id)
        await task.delete()

    @staticmethod
    async def execute_report_send_task(task_id: int):
        task = await ReportSendTask.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        asyncio.create_task(NotifyTaskExecutor.execute_report_send_task(task_id=task_id))
        return {"success": True, "message": "任务已开始执行"}

    @staticmethod
    async def list_sql_alert_tasks(page: int, page_size: int, task_name: Optional[str], status: Optional[bool]):
        query = SqlAlertTask.all().prefetch_related("db_connection", "sender")
        if task_name:
            query = query.filter(task_name__icontains=task_name)
        if status is not None:
            query = query.filter(status=status)
        total = await query.count()
        items = await query.order_by("-id").offset((page - 1) * page_size).limit(page_size)
        data = []
        for item in items:
            item_dict = await item.to_dict()
            db_conn = item.db_connection
            sender = item.sender
            item_dict["db_connection_name"] = db_conn.name if db_conn else ""
            item_dict["sender_name"] = sender.sender_name if sender else ""
            data.append(item_dict)
        return total, data

    @staticmethod
    async def create_sql_alert_task(task_in: SqlAlertTaskCreate, user_id: int):
        db_conn = await DBConnection.get_or_none(id=task_in.db_connection_id)
        if not db_conn:
            raise HTTPException(status_code=400, detail="数据库连接不存在")
        sender = await AlertSender.get_or_none(id=task_in.sender_id, channel_type="wechat_group")
        if not sender:
            raise HTTPException(status_code=400, detail="发送人不存在或非企业微信群类型")
        is_valid, validate_msg = ReportService.validate_sql(task_in.sql_statement)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validate_msg)

        task = await SqlAlertTask.create(**task_in.model_dump(), created_by=user_id, updated_by=user_id)
        if task.status:
            await scheduler.add_sql_alert_job(task)
        return task

    @staticmethod
    async def update_sql_alert_task(task_in: SqlAlertTaskUpdate, user_id: int):
        task = await SqlAlertTask.get_or_none(id=task_in.id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        update_data = task_in.model_dump(exclude_unset=True, exclude={"id"})
        if "db_connection_id" in update_data:
            db_conn = await DBConnection.get_or_none(id=update_data["db_connection_id"])
            if not db_conn:
                raise HTTPException(status_code=400, detail="数据库连接不存在")
        if "sender_id" in update_data:
            sender = await AlertSender.get_or_none(id=update_data["sender_id"], channel_type="wechat_group")
            if not sender:
                raise HTTPException(status_code=400, detail="发送人不存在或非企业微信群类型")
        if "sql_statement" in update_data:
            is_valid, validate_msg = ReportService.validate_sql(update_data["sql_statement"])
            if not is_valid:
                raise HTTPException(status_code=400, detail=validate_msg)

        update_data["updated_by"] = user_id
        old_status = task.status
        await task.update_from_dict(update_data).save()

        if old_status != task.status:
            if task.status:
                await scheduler.add_sql_alert_job(task)
            else:
                await scheduler.remove_sql_alert_job(task.id)
        elif task.status and ("cron" in update_data):
            await scheduler.add_sql_alert_job(task)
        return task

    @staticmethod
    async def delete_sql_alert_task(task_id: int):
        task = await SqlAlertTask.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        await scheduler.remove_sql_alert_job(task_id)
        await task.delete()

    @staticmethod
    async def execute_sql_alert_task(task_id: int):
        task = await SqlAlertTask.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        asyncio.create_task(NotifyTaskExecutor.execute_sql_alert_task(task_id=task_id))
        return {"success": True, "message": "任务已开始执行"}

    @staticmethod
    async def list_notify_task_logs(
        page: int,
        page_size: int,
        task_type: Optional[str] = None,
        task_ref_id: Optional[int] = None,
        status: Optional[str] = None,
    ):
        query = NotifyTaskRunLog.all()
        search = Q()
        if task_type:
            search &= Q(task_type=task_type)
        if task_ref_id:
            search &= Q(task_ref_id=task_ref_id)
        if status:
            search &= Q(status=status)
        query = query.filter(search)
        total = await query.count()
        items = await query.order_by("-id").offset((page - 1) * page_size).limit(page_size)
        data = [await item.to_dict() for item in items]
        return total, data


task_notify_controller = TaskNotifyController()
