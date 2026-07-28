import functools
import json
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

TOOL_REGISTRY: dict[str, dict] = {}


class ToolDefinition:
    def __init__(self, name: str, description: str, schema: dict):
        self.name = name
        self.description = description
        self.schema = schema

    def to_dict(self):
        return {"name": self.name, "description": self.description, "inputSchema": self.schema}


def mcp_tool(
    name: str,
    description: str,
    input_model: type[BaseModel],
    is_write: bool = False,
):
    """MCP 工具注册装饰器"""
    def decorator(func):
        schema = input_model.model_json_schema()
        tool_def = ToolDefinition(name, description, schema)
        TOOL_REGISTRY[name] = {
            "definition": tool_def,
            "handler": func,
            "input_model": input_model,
            "is_write": is_write,
        }

        @functools.wraps(func)
        async def wrapper(arguments: dict) -> list[dict]:
            try:
                validated = input_model(**arguments)
                result = await func(validated)
                return result if isinstance(result, list) else [{"type": "text", "text": str(result)}]
            except Exception as e:
                return [{"type": "text", "text": json.dumps({
                    "success": False,
                    "error": str(e),
                    "suggestion": _suggest_fix(str(e))
                }, ensure_ascii=False)}]
        return wrapper
    return decorator


def _suggest_fix(error: str) -> str:
    if "不存在" in error or "not found" in error.lower():
        return "请先使用查询工具确认数据是否存在"
    if "权限" in error or "permission" in error.lower():
        return "该操作需要管理员权限"
    if "参数" in error or "invalid" in error.lower():
        return "请检查入参格式，参考工具的 inputSchema 说明"
    return "请联系系统管理员"


def _ok(data: Any, message: str = "") -> list[dict]:
    """标准成功返回"""
    return [{"type": "text", "text": json.dumps({
        "success": True, "data": data, "message": message
    }, ensure_ascii=False, default=str)}]


def _err(message: str, suggestion: str = "") -> list[dict]:
    """标准失败返回"""
    return [{"type": "text", "text": json.dumps({
        "success": False, "error": message, "suggestion": suggestion
    }, ensure_ascii=False)}]


async def _create_approval(
    op_type: str,
    op_params: dict,
    applicant_id: str,
    remark: str = "",
    op_module: str = "",
):
    """创建 DBA 审批单（写操作前必须调用）"""
    from aiagent.models.ai_approval import AiApproval

    date_str = datetime.now().strftime("%Y%m%d")
    seq = await AiApproval.filter(
        approval_no__startswith=f"OPS-{date_str}"
    ).count() + 1
    approval_no = f"OPS-{date_str}-{seq:03d}"

    reviewer_id, reviewer_name, reviewer_contact = await _lookup_dba_reviewer(op_type)
    op_description = f"{op_type} 审批申请"

    return await AiApproval.create(
        approval_no=approval_no,
        op_type=op_type,
        op_module=op_module or "OPS",
        op_params=op_params,
        op_description=op_description,
        applicant_id=applicant_id,
        reviewer_id=reviewer_id,
        reviewer_name=reviewer_name,
        reviewer_contact=reviewer_contact,
        remark=remark,
        status="pending",
        expires_at=datetime.now() + timedelta(hours=24),
    )


async def _notify_dba_wecom(approval) -> None:
    """[预留] 发送企业微信审批通知给 DBA。"""


async def _lookup_dba_reviewer(op_type: str) -> tuple[str, str, str]:
    """[预留] 从公司用户中心查询有权限的 DBA 审批人。"""
    return "dba_admin", "DBA管理员", "请联系系统管理员获取审批人信息"


def _build_wecom_message(approval) -> dict:
    return {
        "msgtype": "markdown",
        "markdown": {
            "content": (
                f"## 【dbadmin 运维审批】\n"
                f"> **申请单号**：{approval.approval_no}\n"
                f"> **操作类型**：{approval.op_description}\n"
                f"> **申请人**：{approval.applicant_name or approval.applicant_id}\n"
                f"> **申请备注**：{approval.remark or '无'}\n"
                f"> **审批截止**：{approval.expires_at.strftime('%m-%d %H:%M') if approval.expires_at else '24小时内'}\n"
                f"\n"
                f"请登录 [dbadmin系统](http://dbadmin.company.com/ai/approvals) 查看详情并审批。"
            )
        }
    }
