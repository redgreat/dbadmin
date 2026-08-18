import asyncio
import logging
from datetime import datetime

from fastapi import HTTPException
from tortoise.transactions import in_transaction

from app.models.script import PythonScript, ScriptRunLog

logger = logging.getLogger(__name__)


class ScriptController:
    """Python脚本控制器"""

    model = PythonScript

    async def get_scripts(
        self,
        page: int = 1,
        limit: int = 10,
        name: str | None = None,
        status: bool | None = None,
    ) -> dict:
        """获取脚本列表"""
        query = self.model.all()

        if name:
            query = query.filter(name__icontains=name)
        if status is not None:
            query = query.filter(status=status)

        total = await query.count()
        items = await query.order_by("-id").offset((page - 1) * limit).limit(limit)

        from app.schemas.script import PythonScriptInDB, PythonScriptList
        return PythonScriptList(
            items=[PythonScriptInDB.model_validate(item) for item in items],
            total=total
        ).model_dump(mode='json')

    async def get_script(self, script_id: int) -> dict:
        """获取单个脚本详情"""
        script = await self.model.get_or_none(id=script_id)
        if not script:
            raise HTTPException(status_code=404, detail=f"脚本 {script_id} 不存在")

        from app.schemas.script import PythonScriptInDB
        return PythonScriptInDB.model_validate(script).model_dump(mode='json')

    async def create_script(self, script_data: dict) -> dict:
        """创建新脚本"""
        async with in_transaction():
            script = await self.model.create(**script_data)

        from app.schemas.script import PythonScriptInDB
        return PythonScriptInDB.model_validate(script).model_dump(mode='json')

    async def update_script(self, script_id: int, script_data: dict) -> dict:
        """更新脚本"""
        script = await self.model.get_or_none(id=script_id)
        if not script:
            raise HTTPException(status_code=404, detail=f"脚本 {script_id} 不存在")

        update_data = {k: v for k, v in script_data.items() if v is not None}

        async with in_transaction():
            await script.update_from_dict(update_data).save()

        script = await self.model.get(id=script_id)
        from app.schemas.script import PythonScriptInDB
        return PythonScriptInDB.model_validate(script).model_dump(mode='json')

    async def delete_script(self, script_id: int) -> bool:
        """删除脚本"""
        script = await self.model.get_or_none(id=script_id)
        if not script:
            raise HTTPException(status_code=404, detail=f"脚本 {script_id} 不存在")

        async with in_transaction():
            await script.delete()

        return True

    async def execute_script(self, script_id: int) -> dict:
        """执行脚本"""
        script = await self.model.get_or_none(id=script_id)
        if not script:
            raise HTTPException(status_code=404, detail=f"脚本 {script_id} 不存在")

        # 创建执行日志
        run_log = await ScriptRunLog.create(
            script_id=script.id,
            status="running",
            start_time=datetime.now()
        )

        # 异步执行脚本
        asyncio.create_task(self._run_script(script, run_log))

        return {
            "success": True,
            "message": f"脚本 {script_id} 已开始执行",
            "log_id": run_log.id
        }

    async def _run_script(self, script: PythonScript, run_log: ScriptRunLog):
        """后台执行脚本"""
        import os
        import subprocess
        import tempfile

        try:
            # 将脚本内容写入临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(script.code)
                temp_file = f.name

            # 执行脚本
            process = subprocess.Popen(
                ['python', temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd='/home/app'
            )

            try:
                stdout, stderr = process.communicate(timeout=3600)
                stdout_text = stdout.decode('utf-8', errors='replace')
                stderr_text = stderr.decode('utf-8', errors='replace')

                if process.returncode == 0:
                    run_log.output = stdout_text
                    run_log.status = "success"
                else:
                    run_log.output = stdout_text
                    run_log.error = stderr_text
                    run_log.status = "failed"
            except subprocess.TimeoutExpired:
                process.kill()
                run_log.error = "脚本执行超时"
                run_log.status = "failed"
            finally:
                # 删除临时文件
                os.unlink(temp_file)

        except Exception as e:
            logger.exception(f"执行脚本 {script.id} 时发生错误")
            run_log.error = str(e)
            run_log.status = "failed"
        finally:
            # 更新执行日志
            start_time = run_log.start_time
            end_time = datetime.now()
            run_log.end_time = end_time
            if start_time:
                run_log.duration = int((end_time - start_time).total_seconds())
            await run_log.save()

    async def get_run_logs(
        self,
        script_id: int | None = None,
        page: int = 1,
        limit: int = 10,
        status: str | None = None,
    ) -> dict:
        """获取脚本执行日志"""
        query = ScriptRunLog.all()

        if script_id:
            query = query.filter(script_id=script_id)
        if status:
            query = query.filter(status=status)

        total = await query.count()
        items = await query.order_by("-id").offset((page - 1) * limit).limit(limit)

        from app.schemas.script import ScriptRunLogInDB, ScriptRunLogList
        return ScriptRunLogList(
            items=[ScriptRunLogInDB.model_validate(item) for item in items],
            total=total
        ).model_dump(mode='json')

    async def get_run_log(self, log_id: int) -> dict:
        """获取单个执行日志详情"""
        log = await ScriptRunLog.get_or_none(id=log_id)
        if not log:
            raise HTTPException(status_code=404, detail=f"执行日志 {log_id} 不存在")

        from app.schemas.script import ScriptRunLogInDB
        return ScriptRunLogInDB.model_validate(log).model_dump(mode='json')


script_controller = ScriptController()
