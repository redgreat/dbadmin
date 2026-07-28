from datetime import datetime

from fastapi import HTTPException

from aiagent.models.ai_token import AiToken


async def verify_token(token_value: str) -> AiToken:
    """验证 AI Token 有效性"""
    if not token_value:
        raise HTTPException(status_code=401, detail="缺少 X-AI-Token 请求头")

    token_obj = await AiToken.filter(token=token_value, enabled=True).first()
    if not token_obj:
        raise HTTPException(status_code=401, detail="无效或已禁用的 Token")

    # 更新最后使用时间
    await AiToken.filter(id=token_obj.id).update(last_used_at=datetime.now())
    return token_obj
