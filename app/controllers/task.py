import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.models.task import Task, TaskLog, TaskStatus, TaskType
from app.schemas.task import (
    TaskCreate,
    TaskInDB,
    TaskList,
    TaskLogInDB,
    TaskLogList,
    TaskUpdate,
)
from app.services.task_scheduler import scheduler


class TaskController:
    """定时任务控制器"""

    model = Task

    async def get_tasks(
        self,
        page: int = 1,
        limit: int = 10,
        name: Optional[str] = None,
        type: Optional[str] = None,
        status: Optional[bool] = None,
    ) -> TaskList:
        """获取任务列表"""
        # 构建查询条件
        query = self.model.all()

        if name:
            query = query.filter(name__icontains=name)
        if type:
            query = query.filter(type=type)
        if status is not None:
            query = query.filter(status=status)

        # 计算总数
        total = await query.count()

        # 分页查询
        items = await query.order_by("-id").offset((page - 1) * limit).limit(limit)

        # 转换为响应模型
        return TaskList(items=[TaskInDB.model_validate(item) for item in items], total=total)

    async def get_task(self, task_id: int) -> TaskInDB:
        """获取单个任务详情"""
        task = await self.model.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        return TaskInDB.model_validate(task)

    async def create_task(self, task_data: TaskCreate) -> TaskInDB:
        """创建新任务"""
        async with in_transaction():
            # 创建任务记录
            task = await self.model.create(**task_data.model_dump())

            # 如果任务状态为启用，则添加到调度器
            if task.status:
                await scheduler.add_job(task)

        return TaskInDB.model_validate(task)

    async def update_task(self, task_id: int, task_data: TaskUpdate) -> TaskInDB:
        """更新任务"""
        task = await self.model.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        # 更新前的状态
        old_status = task.status

        # 过滤掉None值，只更新提供的字段
        update_data = {k: v for k, v in task_data.model_dump().items() if v is not None}

        async with in_transaction():
            # 更新任务记录
            await task.update_from_dict(update_data).save()

            # 如果状态发生变化，更新调度器
            if "status" in update_data and old_status != task.status:
                if task.status:
                    # 启用任务，添加到调度器
                    await scheduler.add_job(task)
                else:
                    # 禁用任务，从调度器中移除
                    await scheduler.remove_job(task.id)
            elif task.status and ("cron" in update_data or "type" in update_data):
                # 如果Cron表达式或任务类型发生变化，需要重新添加到调度器
                await scheduler.add_job(task)

        # 重新获取任务，确保返回最新数据
        task = await self.model.get(id=task_id)
        return TaskInDB.model_validate(task)

    async def delete_task(self, task_id: int) -> bool:
        """删除任务"""
        task = await self.model.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        async with in_transaction():
            # 从调度器中移除任务
            await scheduler.remove_job(task_id)

            # 删除任务记录
            await task.delete()

        return True

    async def execute_task(self, task_id: int) -> Dict[str, Any]:
        """立即执行任务"""
        task = await self.model.get_or_none(id=task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        # 创建任务日志
        task_log = await TaskLog.create(
            task_id=task.id, status=TaskStatus.RUNNING, start_time=datetime.now(), retry_count=0
        )

        # 异步执行任务
        asyncio.create_task(scheduler.execute_task(task_id))

        return {"success": True, "message": f"任务 {task_id} 已开始执行", "task_log_id": task_log.id}

    async def get_task_logs(
        self, task_id: Optional[int] = None, page: int = 1, limit: int = 10, status: Optional[str] = None
    ) -> TaskLogList:
        """获取任务执行日志"""
        # 构建查询条件
        query = TaskLog.all()

        if task_id:
            query = query.filter(task_id=task_id)
        if status:
            query = query.filter(status=status)

        # 计算总数
        total = await query.count()

        # 分页查询
        items = await query.order_by("-id").offset((page - 1) * limit).limit(limit)

        # 转换为响应模型
        return TaskLogList(items=[TaskLogInDB.model_validate(item) for item in items], total=total)

    async def get_task_log(self, log_id: int) -> TaskLogInDB:
        """获取单个任务日志详情"""
        log = await TaskLog.get_or_none(id=log_id)
        if not log:
            raise HTTPException(status_code=404, detail=f"任务日志 {log_id} 不存在")

        return TaskLogInDB.model_validate(log)


# 创建控制器实例
task_controller = TaskController()
