from pydantic import BaseModel, Field

from aiagent.tools.base import _err, _ok, mcp_tool


class ExecuteSqlQueryInput(BaseModel):
    conn_name: str = Field(..., description="连接名称")
    sql: str = Field(..., description="要执行的 SELECT SQL")

@mcp_tool(
    name="execute_sql_query",
    description="在指定连接执行 SELECT SQL 查询，禁止执行 DDL 和 DML",
    input_model=ExecuteSqlQueryInput,
    is_write=False
)
async def execute_sql_query(args: ExecuteSqlQueryInput):
    # 占位
    if "update" in args.sql.lower() or "delete" in args.sql.lower() or "drop" in args.sql.lower():
        return _err("禁止执行修改数据的 SQL")
    return _ok([], "执行成功，返回 0 条记录")
