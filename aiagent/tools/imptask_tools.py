import os

import httpx
from pydantic import BaseModel, Field

from app.core.config_loader import get_config

from .base import _err, _ok, mcp_tool


class QueryImptaskStatusInput(BaseModel):
    task_id: str = Field(..., description="导入任务ID")

@mcp_tool(
    name="query_imptask_status",
    description="查询 Excel 导入任务进度（不包含上传，上传需走HTTP）",
    input_model=QueryImptaskStatusInput,
    is_write=False
)
async def query_imptask_status(args: QueryImptaskStatusInput):
    return _ok({"task_id": args.task_id, "progress": 100, "status": "finished"}, "查询成功")


class GfsCostManualImportInput(BaseModel):
    cost_sync_id: str | None = Field(default=None, description="指定同步批次ID，可为空")


def _get_gfs_sync_settings() -> tuple[str, str]:
    """获取 GFS 费用同步地址和令牌，优先读取配置文件。"""
    config = get_config()
    url = (config.gfs_sync.url or "").strip() or os.getenv("GFS_SYNC_URL", "").strip()
    api_key = (config.gfs_sync.api_key or "").strip() or os.getenv("GFS_SYNC_API_KEY", "").strip()
    return url, api_key


@mcp_tool(
    name="gfs_cost_manual_import",
    description="GFS费用手动导入：触发费用同步任务执行并返回执行结果摘要",
    input_model=GfsCostManualImportInput,
    is_write=True,
)
async def gfs_cost_manual_import(args: GfsCostManualImportInput):
    """触发 GFS 费用同步导入。"""
    url, api_key = _get_gfs_sync_settings()
    if not api_key:
        return _err("缺少 GFS 同步 API Key 配置", "请在 config/config.yml 的 gfs_sync.api_key 中配置后重试")

    if not url:
        return _err("缺少 GFS 同步 URL 配置", "请在 config/config.yml 的 gfs_sync.url 中配置后重试")

    payload = {}
    if args.cost_sync_id:
        payload["cost_sync_id"] = args.cost_sync_id

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            resp = await client.post(url, headers={"x-api-key": api_key}, json=payload or None)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        return _err(f"GFS费用导入触发失败: {e}", "请检查 GFS_SYNC_URL 可达性、API Key 是否正确、服务端日志是否报错")

    return _ok(data, "触发成功")
