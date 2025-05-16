import os
import json
import logging
import subprocess
import time
from datetime import datetime
import asyncio
from typing import Dict, Any, Optional, Tuple
import pathlib

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from tortoise import Tortoise

from app.models.task import Task, TaskLog, TaskType, TaskStatus
from app.settings.config import settings

logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器，负责管理和执行定时任务"""

    def __init__(self):
        """初始化调度器"""
        self.scheduler = None
        self.init_scheduler()

    def init_scheduler(self):
        """初始化APScheduler调度器"""
        # 使用内存作为作业存储
        jobstores = {
            'default': MemoryJobStore()
        }

        # 配置执行器
        executors = {
            'default': ThreadPoolExecutor(20),  # 线程池执行器，适合IO密集型任务
            'processpool': ProcessPoolExecutor(5)  # 进程池执行器，适合CPU密集型任务
        }

        # 作业默认配置
        job_defaults = {
            'coalesce': False,  # 是否合并执行
            'max_instances': 3  # 同一个作业的最大实例数
        }

        # 创建调度器
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'  # 设置时区
        )

    async def start(self):
        """启动调度器并加载所有启用的任务"""
        if not self.scheduler.running:
            self.scheduler.start()
            await self.load_tasks()
            logger.info("任务调度器已启动")

    async def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("任务调度器已关闭")

    async def load_tasks(self):
        """加载所有启用的任务"""
        try:
            # 检查 Task 表是否存在
            try:
                tasks = await Task.filter(status=True).all()
                for task in tasks:
                    await self.add_job(task)
                logger.info(f"已加载 {len(tasks)} 个任务")
            except Exception as e:
                logger.warning(f"加载任务失败，可能是 Task 表不存在: {str(e)}")
                logger.info("跳过加载任务，等待数据库表创建后再加载")
        except Exception as e:
            logger.error(f"加载任务时发生错误: {str(e)}")

    async def add_job(self, task: Task):
        """添加任务到调度器"""
        job_id = f"task_{task.id}"

        # 创建Cron触发器
        trigger = CronTrigger.from_crontab(task.cron)

        # 根据任务类型选择执行器
        if task.type == TaskType.PYTHON:
            executor = 'processpool'  # Python函数使用进程池执行器
        else:
            executor = 'default'  # 其他任务使用线程池执行器

        # 添加作业到调度器
        self.scheduler.add_job(
            self.execute_task,  # 执行函数
            trigger=trigger,  # 触发器
            id=job_id,  # 作业ID
            name=task.name,  # 作业名称
            executor=executor,  # 执行器
            replace_existing=True,  # 如果存在则替换
            kwargs={'task_id': task.id}  # 传递给执行函数的参数
        )

        # 更新下次执行时间
        job = self.scheduler.get_job(job_id)
        if job:
            task.next_run_time = job.next_run_time
            await task.save()

        logger.info(f"已添加任务 {job_id} 到调度器，下次执行时间: {task.next_run_time}")

    async def remove_job(self, task_id: int):
        """从调度器中移除任务"""
        job_id = f"task_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"已从调度器中移除任务 {job_id}")

    async def execute_task(self, task_id: int):
        """执行任务"""
        # 获取任务信息
        task = await Task.get_or_none(id=task_id)
        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return

        # 创建任务日志
        task_log = await TaskLog.create(
            task_id=task.id,
            status=TaskStatus.RUNNING,  # 初始状态为运行中
            start_time=datetime.now(),
            retry_count=0
        )

        # 更新任务上次执行时间
        task.last_run_time = task_log.start_time
        await task.save()

        logger.info(f"开始执行任务 {task.id}: {task.name}")

        # 执行任务，支持重试
        retry_count = 0
        while retry_count <= task.max_retries:
            if retry_count > 0:
                logger.info(f"重试任务 {task.id}，第 {retry_count}/{task.max_retries} 次尝试")
                task_log.retry_count = retry_count
                await task_log.save()

            try:
                # 根据任务类型执行不同的处理逻辑
                if task.type == TaskType.SHELL:
                    output, error = await self._execute_shell_command(task)
                elif task.type == TaskType.PYTHON:
                    output, error = await self._execute_python_function(task)
                elif task.type == TaskType.HTTP:
                    output, error = await self._execute_http_request(task)
                else:
                    error = f"不支持的任务类型: {task.type}"
                    output = None

                # 检查执行结果
                if error:
                    task_log.error = error
                    task_log.status = TaskStatus.FAILED
                    if retry_count < task.max_retries:
                        retry_count += 1
                        await asyncio.sleep(5)  # 重试前等待5秒
                        continue
                else:
                    task_log.output = output
                    task_log.status = TaskStatus.SUCCESS
                    break
            except Exception as e:
                logger.exception(f"执行任务 {task.id} 时发生错误")
                task_log.error = str(e)
                task_log.status = TaskStatus.FAILED
                if retry_count < task.max_retries:
                    retry_count += 1
                    await asyncio.sleep(5)
                    continue

        # 更新任务日志
        task_log.end_time = datetime.now()
        task_log.duration = int((task_log.end_time - task_log.start_time).total_seconds())
        await task_log.save()

        # 更新下次执行时间
        job = self.scheduler.get_job(f"task_{task.id}")
        if job:
            task.next_run_time = job.next_run_time
            await task.save()

        logger.info(f"任务 {task.id} 执行完成，状态: {task_log.status}")
        return task_log.status == TaskStatus.SUCCESS

    async def _execute_shell_command(self, task: Task) -> Tuple[Optional[str], Optional[str]]:
        """执行Shell命令"""
        try:
            # 准备环境变量
            env = os.environ.copy()
            if task.env_vars:
                for line in task.env_vars.splitlines():
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env[key.strip()] = value.strip()

            # 准备命令
            command = task.command
            if task.args:
                try:
                    args = json.loads(task.args)
                    if isinstance(args, dict):
                        for k, v in args.items():
                            command += f" --{k}={v}"
                    elif isinstance(args, list):
                        command += " " + " ".join(args)
                except json.JSONDecodeError:
                    command += f" {task.args}"

            logger.info(f"执行Shell命令: {command}")

            # 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=task.work_dir,
                env=env
            )

            # 设置超时
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=task.timeout if task.timeout > 0 else None
                )

                stdout_text = stdout.decode('utf-8', errors='replace')
                stderr_text = stderr.decode('utf-8', errors='replace')

                if process.returncode != 0:
                    return stdout_text, stderr_text
                return stdout_text, None
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                return None, f"命令执行超时，超过 {task.timeout} 秒"

        except Exception as e:
            logger.exception(f"执行Shell命令时发生错误，任务ID: {task.id}")
            return None, str(e)

    async def _execute_python_function(self, task: Task) -> Tuple[Optional[str], Optional[str]]:
        """执行Python函数"""
        try:
            # 准备环境变量
            env = os.environ.copy()
            if task.env_vars:
                for line in task.env_vars.splitlines():
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env[key.strip()] = value.strip()

            # 准备命令
            command = f"python {task.command}"
            if task.args:
                try:
                    args = json.loads(task.args)
                    if isinstance(args, dict):
                        for k, v in args.items():
                            command += f" --{k}={v}"
                    elif isinstance(args, list):
                        command += " " + " ".join(args)
                except json.JSONDecodeError:
                    command += f" {task.args}"

            logger.info(f"执行Python函数: {command}")

            # 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=task.work_dir,
                env=env
            )

            # 设置超时
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=task.timeout if task.timeout > 0 else None
                )

                stdout_text = stdout.decode('utf-8', errors='replace')
                stderr_text = stderr.decode('utf-8', errors='replace')

                if process.returncode != 0:
                    return stdout_text, stderr_text
                return stdout_text, None
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                return None, f"Python函数执行超时，超过 {task.timeout} 秒"

        except Exception as e:
            logger.exception(f"执行Python函数时发生错误，任务ID: {task.id}")
            return None, str(e)

    async def _execute_http_request(self, task: Task) -> Tuple[Optional[str], Optional[str]]:
        """执行HTTP请求"""
        try:
            url = task.command
            method = "GET"
            headers = {}
            data = None

            # 解析参数
            if task.args:
                try:
                    args = json.loads(task.args)
                    if isinstance(args, dict):
                        method = args.get("method", "GET").upper()
                        headers = args.get("headers", {})
                        data = args.get("data")
                except json.JSONDecodeError:
                    return None, f"无效的JSON参数: {task.args}"

            logger.info(f"执行HTTP请求: {method} {url}")

            # 设置超时
            timeout = task.timeout if task.timeout > 0 else None

            # 执行请求
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data if method in ["POST", "PUT", "PATCH"] else None,
                params=data if method == "GET" else None,
                timeout=timeout
            )

            # 检查响应
            response.raise_for_status()
            return response.text, None

        except requests.exceptions.Timeout:
            return None, f"HTTP请求超时，超过 {task.timeout} 秒"
        except requests.exceptions.RequestException as e:
            return None, str(e)
        except Exception as e:
            logger.exception(f"执行HTTP请求时发生错误，任务ID: {task.id}")
            return None, str(e)

# 创建全局调度器实例
scheduler = TaskScheduler()
