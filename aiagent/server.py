import time

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

# 引入工具确保装饰器执行，注册工具
from aiagent.models.ai_tool_call_log import AiToolCallLog
from aiagent.security.permission_checker import check_tool_permission
from aiagent.security.token_auth import verify_token
from aiagent.tools.base import TOOL_REGISTRY

mcp_router = APIRouter()

class MCPCallRequest(BaseModel):
    tool: str
    arguments: dict

@mcp_router.get("/tools")
async def list_tools(x_ai_token: str = Header(default="")):
    token_obj = await verify_token(x_ai_token)
    tools = []
    for name, entry in TOOL_REGISTRY.items():
        if await check_tool_permission(token_obj, name):
            tools.append(entry["definition"].to_dict())
    return {"tools": tools}


@mcp_router.post("/call")
async def call_tool(
    req: MCPCallRequest,
    request: Request,
    x_ai_token: str = Header(default="")
):
    start = time.time()
    token_obj = await verify_token(x_ai_token)

    if not await check_tool_permission(token_obj, req.tool):
        raise HTTPException(status_code=403, detail=f"Token 无权调用工具: {req.tool}")

    entry = TOOL_REGISTRY.get(req.tool)
    if not entry:
        raise HTTPException(status_code=404, detail=f"工具不存在: {req.tool}")

    try:
        result = await entry["handler"](req.arguments)
        status = "success"
        error = None
    except Exception as e:
        result = [{"type": "text", "text": f"工具执行失败: {e!s}"}]
        status = "error"
        error = str(e)

    duration = int((time.time() - start) * 1000)

    # 记录调用日志
    await AiToolCallLog.create(
        ai_token_id=token_obj.id,
        tool_name=req.tool,
        tool_input=req.arguments,
        tool_output_summary=str(result)[:500],
        duration_ms=duration,
        status=status,
        error_message=error,
        caller_ip=request.client.host if request.client else "unknown",
        is_write_op=entry.get("is_write", False),
    )

    return {"content": result}
