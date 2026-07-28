from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class BaseUser(BaseModel):
    id: int
    email: EmailStr | None = None
    username: str | None = None
    is_active: bool | None = True
    is_superuser: bool | None = False
    created_at: datetime | None
    updated_at: datetime | None
    last_login: datetime | None
    roles: list | None = []
    conn_ids: list[int] | None = []


class UserCreate(BaseModel):
    email: EmailStr = Field(json_schema_extra={"example": "admin@qq.com"})
    username: str = Field(json_schema_extra={"example": "admin"})
    password: str = Field(json_schema_extra={"example": "123456"})
    is_active: bool | None = True
    is_superuser: bool | None = False
    role_ids: list[int] | None = []
    conn_ids: list[int] | None = []

    def create_dict(self):
        return self.model_dump(exclude_unset=True, exclude={"role_ids", "conn_ids"})


class UserUpdate(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_active: bool | None = True
    is_superuser: bool | None = False
    role_ids: list[int] | None = []
    conn_ids: list[int] | None = None


class UpdatePassword(BaseModel):
    old_password: str = Field(description="旧密码")
    new_password: str = Field(description="新密码")
