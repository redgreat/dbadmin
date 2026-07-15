from pydantic import BaseModel, Field
from .base import mcp_tool, _ok

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
