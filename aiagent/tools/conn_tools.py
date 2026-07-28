from pydantic import BaseModel

from aiagent.tools.base import _ok, mcp_tool


class ListConnectionsInput(BaseModel):
    pass

@mcp_tool(
    name="list_connections",
    description="列出所有可用的数据库连接名称和类型",
    input_model=ListConnectionsInput,
    is_write=False
)
async def list_connections(args: ListConnectionsInput):
    # 这里占位，实际调用 conn_controller.get_all()
    # from app.controllers import conn_controller
    return _ok([{"name": "默认库", "type": "postgres"}], "查询成功")
