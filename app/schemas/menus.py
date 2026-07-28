from enum import StrEnum

from pydantic import BaseModel, Field


class MenuType(StrEnum):
    CATALOG = "catalog"  # 目录
    MENU = "menu"  # 菜单


class BaseMenu(BaseModel):
    id: int
    name: str
    path: str
    remark: dict | None
    menu_type: MenuType | None
    icon: str | None
    order: int
    parent_id: int
    is_hidden: bool
    component: str
    keepalive: bool
    redirect: str | None
    children: list["BaseMenu"] | None


class MenuCreate(BaseModel):
    menu_type: MenuType = Field(default=MenuType.CATALOG.value)
    name: str = Field(json_schema_extra={"example": "用户管理"})
    icon: str | None = "ph:user-list-bold"
    path: str = Field(json_schema_extra={"example": "/system/user"})
    order: int | None = Field(json_schema_extra={"example": 1})
    parent_id: int | None = Field(json_schema_extra={"example": 0}, default=0)
    is_hidden: bool | None = False
    component: str = Field(default="Layout", json_schema_extra={"example": "/system/user"})
    keepalive: bool | None = True
    redirect: str | None = ""


class MenuUpdate(BaseModel):
    id: int
    menu_type: MenuType | None = Field(json_schema_extra={"example": MenuType.CATALOG.value})
    name: str | None = Field(json_schema_extra={"example": "用户管理"})
    icon: str | None = "ph:user-list-bold"
    path: str | None = Field(json_schema_extra={"example": "/system/user"})
    order: int | None = Field(json_schema_extra={"example": 1})
    parent_id: int | None = Field(json_schema_extra={"example": 0})
    is_hidden: bool | None = False
    component: str = Field(json_schema_extra={"example": "/system/user"})
    keepalive: bool | None = False
    redirect: str | None = ""
