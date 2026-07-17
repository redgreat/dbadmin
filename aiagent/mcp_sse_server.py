"""
标准 MCP SSE 服务入口
使用官方 mcp Python SDK，提供符合 MCP 规范的 SSE 传输通信
运行在独立端口（默认 8502），可被 Hermes Agent、Cursor 等工具直接接入
"""
import contextvars
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

import mcp.types as types
from mcp.server import Server
from mcp.server.sse import SseServerTransport

# 工具注册（触发装饰器执行）
import aiagent.tools.conn_tools  # noqa: F401
import aiagent.tools.sql_tools  # noqa: F401
import aiagent.tools.order_tools  # noqa: F401
import aiagent.tools.wms_tools  # noqa: F401
import aiagent.tools.oa_tools  # noqa: F401
import aiagent.tools.report_tools  # noqa: F401
import aiagent.tools.imptask_tools  # noqa: F401
import aiagent.tools.approval_tools  # noqa: F401

from aiagent.tools.base import TOOL_REGISTRY
from aiagent.security.token_auth import verify_token
from aiagent.security.permission_checker import check_tool_permission
from aiagent.models.ai_tool_call_log import AiToolCallLog

# 每个请求的 Token 上下文变量（用于在工具调用时获取当前 token）
_current_token: contextvars.ContextVar = contextvars.ContextVar("current_token", default=None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化和关闭 Tortoise ORM"""
    from app.settings.database import get_tortoise_config
    db_config = get_tortoise_config()
    await Tortoise.init(config=db_config)
    yield
    await Tortoise.close_connections()


# ─────────────────────────────────────────────
# MCP Server 实例
# ─────────────────────────────────────────────
mcp_server = Server("dbadmin-mcp")
sse_transport = SseServerTransport("/messages")


@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出当前 Token 有权使用的所有工具"""
    token_obj = _current_token.get()
    result = []
    for name, entry in TOOL_REGISTRY.items():
        if token_obj and not await check_tool_permission(token_obj, name):
            continue
        definition = entry["definition"]
        result.append(types.Tool(
            name=name,
            description=definition.description,
            inputSchema=definition.schema,
        ))
    return result


@mcp_server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """调用指定工具"""
    token_obj = _current_token.get()

    if not token_obj:
        raise ValueError("未提供有效的身份验证令牌")

    if not await check_tool_permission(token_obj, name):
        raise ValueError(f"当前 Token 无权调用工具: {name}")

    entry = TOOL_REGISTRY.get(name)
    if not entry:
        raise ValueError(f"工具未找到: {name}")

    start = time.time()
    status = "success"
    error = None
    out = []
    try:
        # entry["handler"] 已包含参数校验逻辑，返回 list[dict]
        result = await entry["handler"](arguments)
        if isinstance(result, list):
            for r in result:
                text = r.get("text", str(r)) if isinstance(r, dict) else str(r)
                out.append(types.TextContent(type="text", text=text))
        else:
            out.append(types.TextContent(type="text", text=str(result)))
    except Exception as e:
        status = "error"
        error = str(e)
        out = [types.TextContent(type="text", text=f"工具执行异常: {e}")]

    duration = int((time.time() - start) * 1000)
    try:
        await AiToolCallLog.create(
            ai_token_id=token_obj.id,
            tool_name=name,
            tool_input=arguments,
            tool_output_summary=str(out)[:500],
            duration_ms=duration,
            status=status,
            error_message=error,
            caller_ip="mcp-sse",
            is_write_op=entry.get("is_write", False),
        )
    except Exception:
        pass  # 日志失败不影响工具结果返回

    return out


# ─────────────────────────────────────────────
# FastAPI 应用
# ─────────────────────────────────────────────
app = FastAPI(
    title="dbadmin MCP SSE Server",
    description="符合官方 MCP 协议的 SSE 工具调用服务，供 Hermes Agent、Cursor 等工具直接接入",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _auth_token(x_ai_token: str) -> object:
    """统一鉴权，失败时抛出 HTTP 401"""
    if not x_ai_token:
        raise HTTPException(status_code=401, detail="缺少 x-ai-token 请求头")
    try:
        token_obj = await verify_token(x_ai_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token 无效: {e}")
    if not token_obj:
        raise HTTPException(status_code=401, detail="Token 不存在或已禁用")
    return token_obj


@app.api_route("/sse", methods=["GET", "POST", "HEAD"])
async def handle_sse(request: Request, x_ai_token: str = Header(default="")):
    """MCP SSE 长连接入口，同时兼容部分客户端将 POST /sse 作为消息入口。"""
    token_obj = await _auth_token(x_ai_token)
    _current_token.set(token_obj)

    if request.method == "HEAD":
        return Response(status_code=200)

    if request.method == "POST":
        content_type = (request.headers.get("content-type") or "").lower()
        if request.query_params.get("session_id") or "application/json" in content_type:
            await sse_transport.handle_post_message(request.scope, request.receive, request._send)
            return

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )
    return Response()


@app.post("/messages")
async def handle_messages(request: Request, x_ai_token: str = Header(default="")):
    """
    MCP JSON-RPC 消息接收端点
    客户端通过此接口向服务端发送 initialize / tools/list / tools/call 等指令
    """
    token_obj = await _auth_token(x_ai_token)
    _current_token.set(token_obj)
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


if __name__ == "__main__":
    uvicorn.run(
        "aiagent.mcp_sse_server:app",
        host="0.0.0.0",
        port=8088,
        log_level="info",
    )
