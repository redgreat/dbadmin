"""
Excel导出服务 - 支持大数据量导出、分sheet、分文件、ZIP压缩
"""
import os
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional
import openpyxl
from openpyxl.workbook.workbook import Workbook
from app.models.report import ReportGeneration, ReportConfig
from app.models.conn import DBConnection
from app.services.sql_execution_service import SQLExecutionService
from app.log import logger
from app.core.config_loader import config


class ExcelExportService:
    """Excel导出服务"""

    # 从配置读取常量
    MAX_ROWS_PER_SHEET = config.report.max_rows_per_sheet
    MAX_SHEETS_PER_FILE = config.report.max_sheets_per_file
    PAGE_SIZE = config.report.page_size

    async def export_report(self, generation_id: int):
        """
        导出报表主流程
        :param generation_id: 报表生成记录ID
        """
        generation = None
        try:
            # 获取生成记录
            generation = await ReportGeneration.get_or_none(id=generation_id).prefetch_related("report_config")
            if not generation:
                logger.error(f"报表生成记录不存在: {generation_id}")
                return

            # 获取报表配置
            config = generation.report_config
            if not config:
                logger.error("报表配置不存在")
                await self._update_generation_status(
                    generation,
                    "failed",
                    error_msg="报表配置不存在"
                )
                return

            # 获取数据库连接
            db_conn = await DBConnection.get_or_none(id=config.db_connection_id)
            if not db_conn:
                logger.error("数据库连接不存在")
                await self._update_generation_status(
                    generation,
                    "failed",
                    error_msg="数据库连接不存在"
                )
                return

            # 记录执行日志
            execution_log = {
                "sql": config.sql_statement,
                "db_connection": {
                    "id": db_conn.id,
                    "name": db_conn.name,
                    "type": db_conn.db_type,
                    "host": db_conn.host,
                    "database": db_conn.database
                },
                "start_time": datetime.now().isoformat()
            }

            # 执行导出
            file_path = await self._execute_export(
                generation=generation,
                db_conn=db_conn,
                sql=config.sql_statement
            )

            # 更新执行日志
            execution_log["end_time"] = datetime.now().isoformat()
            execution_log["status"] = "success"
            execution_log["file_path"] = file_path

            # 更新生成记录状态
            generation.status = "completed"
            generation.completed_at = datetime.now()
            generation.file_path = file_path
            generation.execution_json = execution_log
            await generation.save()

            logger.info(f"报表导出成功: {generation.report_name}, 文件: {file_path}")

        except Exception as e:
            logger.error(f"报表导出失败: {str(e)}", exc_info=True)
            if generation:
                try:
                    await self._update_generation_status(
                        generation,
                        "failed",
                        error_msg=str(e)
                    )
                except Exception as update_error:
                    logger.error(f"更新状态失败: {str(update_error)}")

    async def _execute_export(
        self,
        generation: ReportGeneration,
        db_conn: DBConnection,
        sql: str
    ) -> str:
        """
        执行导出逻辑
        :return: 生成的文件路径
        """
        # 获取总数
        total_count = await SQLExecutionService.get_total_count(db_conn, sql)
        logger.info(f"报表 {generation.report_name} 总数据量: {total_count}")

        if total_count == 0:
            raise ValueError("查询结果为空，无法导出")

        # 计算需要的sheet数和文件数
        total_sheets = (total_count + self.MAX_ROWS_PER_SHEET - 1) // self.MAX_ROWS_PER_SHEET
        total_files = (total_sheets + self.MAX_SHEETS_PER_FILE - 1) // self.MAX_SHEETS_PER_FILE

        logger.info(f"需要 {total_sheets} 个sheet, {total_files} 个文件")

        # 创建文件存储目录
        file_dir = self._get_file_dir()
        os.makedirs(file_dir, exist_ok=True)

        # 生成的文件列表
        file_list = []

        # 分批导出
        current_row = 0
        current_sheet = 0
        current_file = 0
        wb = None
        ws = None
        headers = None

        try:
            while current_row < total_count:
                # 判断是否需要创建新文件
                if current_sheet % self.MAX_SHEETS_PER_FILE == 0:
                    # 保存上一个文件
                    if wb:
                        file_path = self._save_workbook(
                            wb,
                            file_dir,
                            generation.report_name,
                            current_file
                        )
                        file_list.append(file_path)

                    # 创建新工作簿
                    wb = openpyxl.Workbook(write_only=True)
                    current_file += 1
                    logger.info(f"创建第 {current_file} 个Excel文件")

                # 创建新sheet
                ws = wb.create_sheet(title=f"Sheet{current_sheet + 1}")
                current_sheet += 1
                logger.info(f"创建第 {current_sheet} 个sheet")

                # 写入数据到当前sheet
                rows_written, headers = await self._write_data_to_sheet(
                    ws=ws,
                    db_conn=db_conn,
                    sql=sql,
                    offset=current_row,
                    limit=self.MAX_ROWS_PER_SHEET,
                    headers=headers
                )

                current_row += rows_written
                logger.info(f"Sheet {current_sheet} 写入 {rows_written} 行，累计 {current_row}/{total_count}")

            # 保存最后一个文件
            if wb:
                file_path = self._save_workbook(
                    wb,
                    file_dir,
                    generation.report_name,
                    current_file
                )
                file_list.append(file_path)

            # 如果有多个文件，压缩成ZIP
            if len(file_list) > 1:
                zip_path = os.path.join(file_dir, f"{generation.report_name}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in file_list:
                        zipf.write(file_path, os.path.basename(file_path))

                # 删除临时Excel文件
                for file_path in file_list:
                    os.remove(file_path)

                logger.info(f"生成ZIP文件: {zip_path}")
                return zip_path
            else:
                # 单个文件直接返回
                return file_list[0]

        except Exception as e:
            # 清理临时文件
            for file_path in file_list:
                if os.path.exists(file_path):
                    os.remove(file_path)
            raise

    async def _write_data_to_sheet(
        self,
        ws,
        db_conn: DBConnection,
        sql: str,
        offset: int,
        limit: int,
        headers: Optional[List[str]] = None
    ) -> tuple[int, List[str]]:
        """
        写入数据到sheet
        :return: (写入的行数, 表头列表)
        """
        rows_written = 0
        batch_size = self.PAGE_SIZE
        original_headers = None  # 原始字段名，用于数据获取

        # 分批查询并写入
        while rows_written < limit:
            # 计算当前批次大小
            current_batch_size = min(batch_size, limit - rows_written)

            # 查询数据
            data, _ = await SQLExecutionService.execute_query(
                db_conn=db_conn,
                sql=sql,
                offset=offset + rows_written,
                limit=current_batch_size
            )

            if not data:
                break

            # 写入表头（仅第一次）
            if rows_written == 0 and headers is None:
                original_headers = list(data[0].keys())
                # 处理重复字段名，第二个及以后的重名字段添加_2, _3等后缀
                seen = {}
                unique_headers = []
                for h in original_headers:
                    if h in seen:
                        seen[h] += 1
                        unique_headers.append(f"{h}_{seen[h]}")
                    else:
                        seen[h] = 1
                        unique_headers.append(h)
                headers = unique_headers
                ws.append(headers)
            elif original_headers is None:
                original_headers = list(data[0].keys())

            # 写入数据行（使用原始字段名获取数据）
            for row in data:
                ws.append([row.get(h) for h in original_headers])

            rows_written += len(data)

            # 如果查询结果少于批次大小，说明数据已查完
            if len(data) < current_batch_size:
                break

        return rows_written, headers

    def _save_workbook(
        self,
        wb: Workbook,
        file_dir: str,
        report_name: str,
        file_index: int
    ) -> str:
        """
        保存工作簿
        """
        file_name = f"{report_name}_{file_index}.xlsx"
        file_path = os.path.join(file_dir, file_name)
        wb.save(file_path)
        logger.info(f"保存Excel文件: {file_path}")
        return file_path

    def _get_file_dir(self) -> str:
        """
        获取文件存储目录
        """
        now = datetime.now()
        dir_path = os.path.join(
            config.report.report_dir,
            str(now.year),
            f"{now.month:02d}",
            f"{now.day:02d}"
        )
        return dir_path

    async def _update_generation_status(
        self,
        generation: ReportGeneration,
        status: str,
        error_msg: Optional[str] = None
    ):
        """
        更新生成记录状态
        """
        try:
            generation.status = status
            generation.completed_at = datetime.now()

            if error_msg:
                execution_log = generation.execution_json or {}
                execution_log["error"] = error_msg
                execution_log["end_time"] = datetime.now().isoformat()
                generation.execution_json = execution_log

            await generation.save()
        except Exception as e:
            logger.error(f"更新生成记录状态失败: {str(e)}")
