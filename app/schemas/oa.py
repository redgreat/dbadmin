from datetime import datetime

from pydantic import BaseModel, Field


class PositiveTimeRequest(BaseModel):
    """转正时间修改/验证入参"""

    codes: list[str] = Field(default_factory=list, description="人员工号列表")
    positive_time: datetime | None = Field(default=None, description="目标转正时间")
