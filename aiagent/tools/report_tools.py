from pydantic import BaseModel, Field

from .base import _ok, mcp_tool


class ListReportsInput(BaseModel):
    pass

@mcp_tool(
    name="list_reports",
    description="列出可用报表配置",
    input_model=ListReportsInput,
    is_write=False
)
async def list_reports(args: ListReportsInput):
    return _ok([], "查询成功")

class TriggerReportGenerationInput(BaseModel):
    report_id: int = Field(..., description="报表ID")

@mcp_tool(
    name="trigger_report_generation",
    description="触发报表生成（异步）",
    input_model=TriggerReportGenerationInput,
    is_write=True
)
async def trigger_report_generation(args: TriggerReportGenerationInput):
    return _ok({"report_id": args.report_id, "task_id": "celery_task_id"}, "触发成功，异步生成中")
