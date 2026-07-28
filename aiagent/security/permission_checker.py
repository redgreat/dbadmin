from aiagent.models.ai_token import AiToken


async def check_tool_permission(token: AiToken, tool_name: str) -> bool:
    """检查Token是否有权限调用该工具"""
    # 如果没配置 allow_tools，代表全部允许
    if not token.allow_tools:
        return True

    return tool_name in token.allow_tools
