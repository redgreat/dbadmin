import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import openpyxl

from app.models.alert import AlertSendLog, AlertSender
from app.models.conn import DBConnection
from app.models.report import ReportConfig, ReportGeneration
from app.models.task_notify import NotifyTaskRunLog, ReportSendTask, SqlAlertTask, TaskRunStatus
from app.services.excel_export_service import ExcelExportService
from app.services.report_service import ReportService
from app.services.sql_execution_service import SQLExecutionService
from app.services.wecom_bot_service import WecomBotService


class NotifyTaskExecutor:
    @staticmethod
    async def _create_run_log(task_type: str, task_ref_id: int) -> NotifyTaskRunLog:
        return await NotifyTaskRunLog.create(
            task_type=task_type,
            task_ref_id=task_ref_id,
            status=TaskRunStatus.RUNNING,
            start_time=datetime.now(),
        )

    @staticmethod
    async def _finish_run_log(
        run_log: NotifyTaskRunLog,
        status: str,
        output: Optional[str] = None,
        error: Optional[str] = None,
        result_json: Optional[dict] = None,
    ):
        run_log.status = status
        run_log.output = output
        run_log.error = error
        run_log.result_json = result_json
        run_log.end_time = datetime.now()
        run_log.duration = int((run_log.end_time - run_log.start_time).total_seconds())
        await run_log.save()

    @staticmethod
    async def _create_alert_send_log(
        sender: AlertSender,
        alert_text: str,
        send_status: int,
        response_text: Optional[str] = None,
    ):
        await AlertSendLog.create(
            sender_id=sender.id,
            sender_name=sender.sender_name,
            channel_type=sender.channel_type,
            channel_target=sender.channel_target,
            alert_text=alert_text,
            send_status=send_status,
            response_text=response_text,
            sent_at=datetime.now(),
        )

    @staticmethod
    async def execute_report_send_task(task_id: int) -> Dict[str, Any]:
        run_log = await NotifyTaskExecutor._create_run_log("report_send", task_id)
        task = await ReportSendTask.get_or_none(id=task_id).prefetch_related("report_config", "sender")
        if not task:
            await NotifyTaskExecutor._finish_run_log(run_log, TaskRunStatus.FAILED, error="任务不存在")
            return {"success": False, "message": "任务不存在"}

        try:
            sender = task.sender
            if not sender or not sender.is_enabled:
                raise ValueError("发送人不存在或已禁用")

            report_config = task.report_config
            if not report_config:
                raise ValueError("报表配置不存在")

            generation_name = f"{report_config.report_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            generation = await ReportGeneration.create(
                report_name=generation_name,
                report_config_id=report_config.id,
                generator="system-task",
                status="exporting",
            )

            # 执行生成并保留报表生成记录
            await ExcelExportService().export_report(generation.id)
            generation = await ReportGeneration.get(id=generation.id)
            if generation.status != "completed" or not generation.file_path:
                raise ValueError("报表生成失败")

            message = task.message_template or (
                f"定时报表已生成\n"
                f"报表：{report_config.report_name}\n"
                f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            text_resp = WecomBotService.send_text(sender.channel_target, message)

            file_resp = None
            if task.send_attachment and generation.file_path and os.path.exists(generation.file_path):
                file_resp = WecomBotService.send_file(sender.channel_target, generation.file_path)

            task.last_run_time = datetime.now()
            await task.save()

            await NotifyTaskExecutor._create_alert_send_log(
                sender=sender,
                alert_text=message,
                send_status=1,
                response_text=str({"text": text_resp, "file": file_resp}),
            )
            await NotifyTaskExecutor._finish_run_log(
                run_log=run_log,
                status=TaskRunStatus.SUCCESS,
                output="执行成功",
                result_json={"generation_id": generation.id, "file_path": generation.file_path},
            )
            return {"success": True, "message": "执行成功", "generation_id": generation.id}
        except Exception as exc:
            task.last_run_time = datetime.now()
            await task.save()
            await NotifyTaskExecutor._finish_run_log(run_log, TaskRunStatus.FAILED, error=str(exc))
            sender = await AlertSender.get_or_none(id=task.sender_id) if task.sender_id else None
            if sender:
                await NotifyTaskExecutor._create_alert_send_log(
                    sender=sender,
                    alert_text=f"定时报表任务执行失败: {task.task_name}",
                    send_status=0,
                    response_text=str(exc),
                )
            return {"success": False, "message": str(exc)}

    @staticmethod
    def _fill_message(template: str, first_row: Optional[dict], total: int, template_columns: List[str], total_placeholder: str):
        msg = template or ""
        msg = msg.replace(total_placeholder or "{{total}}", str(total))
        msg = msg.replace("{total}", str(total))
        if first_row and template_columns and "{}" in msg:
            values = [first_row.get(col, "") for col in template_columns]
            try:
                msg = msg.format(*values)
            except Exception:
                pass
        if first_row:
            try:
                msg = msg.format(**first_row, total=total)
            except Exception:
                pass
        return msg

    @staticmethod
    def _build_detail_excel(task_name: str, rows: List[dict]) -> Optional[str]:
        if not rows:
            return None
        file_dir = ExcelExportService()._get_file_dir()
        os.makedirs(file_dir, exist_ok=True)
        file_name = f"{task_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx".replace("/", "_")
        file_path = os.path.join(file_dir, file_name)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "detail"

        headers = list(rows[0].keys())
        for col_idx, header in enumerate(headers, 1):
            ws.cell(row=1, column=col_idx, value=header)
        for row_idx, row_data in enumerate(rows, 2):
            for col_idx, header in enumerate(headers, 1):
                ws.cell(row=row_idx, column=col_idx, value=row_data.get(header))
        wb.save(file_path)
        return file_path

    @staticmethod
    async def execute_sql_alert_task(task_id: int) -> Dict[str, Any]:
        run_log = await NotifyTaskExecutor._create_run_log("sql_alert", task_id)
        task = await SqlAlertTask.get_or_none(id=task_id).prefetch_related("db_connection", "sender")
        if not task:
            await NotifyTaskExecutor._finish_run_log(run_log, TaskRunStatus.FAILED, error="任务不存在")
            return {"success": False, "message": "任务不存在"}

        try:
            sender = task.sender
            if not sender or not sender.is_enabled:
                raise ValueError("发送人不存在或已禁用")

            db_conn = task.db_connection
            if not db_conn:
                raise ValueError("数据库连接不存在")

            is_valid, validate_msg = ReportService.validate_sql(task.sql_statement)
            if not is_valid:
                raise ValueError(validate_msg)

            rows, total = await SQLExecutionService.execute_query(db_conn=db_conn, sql=task.sql_statement, offset=0, limit=2000)
            template_columns = [item.strip() for item in (task.template_columns or "").split(",") if item.strip()]
            first_row = rows[0] if rows else None
            message = NotifyTaskExecutor._fill_message(
                template=task.message_template,
                first_row=first_row,
                total=total,
                template_columns=template_columns,
                total_placeholder=task.total_placeholder or "{{total}}",
            )
            if not message:
                message = f"SQL预警结果：共 {total} 条"

            text_resp = WecomBotService.send_text(sender.channel_target, message)
            file_path = None
            file_resp = None
            if task.send_detail_excel and rows:
                file_path = NotifyTaskExecutor._build_detail_excel(task.task_name, rows)
                if file_path and os.path.exists(file_path):
                    file_resp = WecomBotService.send_file(sender.channel_target, file_path)

            task.last_run_time = datetime.now()
            await task.save()
            await NotifyTaskExecutor._create_alert_send_log(
                sender=sender,
                alert_text=message,
                send_status=1,
                response_text=str({"text": text_resp, "file": file_resp}),
            )
            await NotifyTaskExecutor._finish_run_log(
                run_log=run_log,
                status=TaskRunStatus.SUCCESS,
                output="执行成功",
                result_json={"total": total, "detail_file": file_path},
            )
            return {"success": True, "message": "执行成功", "total": total}
        except Exception as exc:
            task.last_run_time = datetime.now()
            await task.save()
            await NotifyTaskExecutor._finish_run_log(run_log, TaskRunStatus.FAILED, error=str(exc))
            sender = await AlertSender.get_or_none(id=task.sender_id) if task.sender_id else None
            if sender:
                await NotifyTaskExecutor._create_alert_send_log(
                    sender=sender,
                    alert_text=f"SQL预警任务执行失败: {task.task_name}",
                    send_status=0,
                    response_text=str(exc),
                )
            return {"success": False, "message": str(exc)}
