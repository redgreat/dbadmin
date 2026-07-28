from datetime import datetime

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
    request_body: str | None = None
    response_body: str | None = None
    response_time: int
    created_at: datetime
    updated_at: datetime


class AuditLogQuerySchema(BaseModel):
    username: str | None = None
    module: str | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = 1
    page_size: int = 10
