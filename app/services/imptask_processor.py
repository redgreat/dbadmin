"""
Excel导入任务后台处理器
"""
import os
import asyncio
from datetime import datetime
from app.models.imptask import ImpTask
from app.services.excelimp_service import generate_sql
from app.log import logger


async def submit_imptask(task_id: int):
    """
    提交Excel导入任务到后台处理

    Args:
        task_id: 任务ID
    """
    # 创建后台任务
    asyncio.create_task(_process_imptask_async(task_id))
    logger.info(f"任务已提交到后台处理: {task_id}")


async def _process_imptask_async(task_id: int):
    """
    异步处理Excel导入任务

    Args:
        task_id: 任务ID
    """
    try:
        # 获取任务
        task = await ImpTask.get(id=task_id)

        if not task:
            logger.error(f"任务不存在: {task_id}")
            return

        # 更新任务状态为处理中
        task.status = "processing"
        task.started_at = datetime.now()
        task.progress = 10
        task.message = "开始处理Excel文件..."
        await task.save()

        logger.info(f"开始处理Excel导入任务: {task_id}, 文件: {task.filename}")

        # 检查文件是否存在
        if not os.path.exists(task.file_path):
            raise FileNotFoundError(f"文件不存在: {task.file_path}")

        # 更新进度: 读取文件
        task.progress = 20
        task.message = "正在读取Excel文件..."
        await task.save()

        # 读取文件内容
        with open(task.file_path, 'rb') as f:
            file_content = f.read()

        # 更新进度: 解析Excel
        task.progress = 40
        task.message = "正在解析Excel数据..."
        await task.save()

        # 生成SQL - 使用线程池避免阻塞事件循环
        sql_result = await asyncio.to_thread(generate_sql, file_content, task.filename, task.db_type)

        # 更新进度: 保存SQL文件
        task.progress = 80
        task.message = "正在保存SQL文件..."
        await task.save()

        # 生成SQL文件路径
        sql_filename = f"sql_{task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        sql_file_path = os.path.join(os.path.dirname(task.file_path), sql_filename)

        # 保存SQL文件
        with open(sql_file_path, 'w', encoding='utf-8') as f:
            f.write(sql_result)

        # 更新任务状态为完成
        task.status = "completed"
        task.progress = 100
        task.message = "SQL生成完成"
        task.sql_file_path = sql_file_path
        task.sql_file_size = os.path.getsize(sql_file_path)
        task.completed_at = datetime.now()
        await task.save()

        logger.info(f"Excel导入任务完成: {task_id}, SQL文件: {sql_filename}")

    except Exception as e:
        logger.error(f"Excel导入任务失败: {task_id}, 错误: {str(e)}")
        await _update_task_failed(task_id, str(e))


async def _update_task_failed(task_id: int, error_message: str):
    """更新任务失败状态"""
    try:
        task = await ImpTask.get(id=task_id)
        task.status = "failed"
        task.error_message = error_message
        task.completed_at = datetime.now()
        await task.save()
    except Exception as save_error:
        logger.error(f"更新任务失败状态时出错: {save_error}")
