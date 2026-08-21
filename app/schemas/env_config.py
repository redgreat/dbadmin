from pydantic import BaseModel
from typing import Optional


class EnvConfigCreate(BaseModel):
    """创建环境变量"""
    key: str
    value: str
    description: Optional[str] = None
    is_sensitive: bool = False


class EnvConfigUpdate(BaseModel):
    """更新环境变量"""
    value: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: Optional[bool] = None


class EnvConfigOut(BaseModel):
    """环境变量输出"""
    id: int
    key: str
    value: str
    description: Optional[str] = None
    is_sensitive: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PythonPackageCreate(BaseModel):
    """创建包"""
    name: str
    version: Optional[str] = None
    description: Optional[str] = None


class PythonPackageUpdate(BaseModel):
    """更新包"""
    version: Optional[str] = None
    description: Optional[str] = None
    is_installed: Optional[bool] = None


class PythonPackageOut(BaseModel):
    """包输出"""
    id: int
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    is_installed: bool = False
    installed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
