from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    username: str
    module: str
    summary: str
    method: str
    path: str
    status: int
    response_time: int
    created_at: datetime
    updated_at: datetime


class AuditLogQuerySchema(BaseModel):
    username: Optional[str] = None
    module: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 10
