from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DBConnectionBase(BaseModel):
    """数据库连接基础模式"""
    name: str = Field(..., description="连接名称")
    db_type: str = Field(..., description="数据库类型：mysql, postgresql, sqlite, oracle, sqlserver")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="端口")
    username: str = Field(..., description="用户名")
    database: str = Field(..., description="数据库名")
    params: Optional[str] = Field(None, description="连接参数")
    status: Optional[bool] = Field(False, description="连接状态")
    remark: Optional[str] = Field(None, description="备注")


class DBConnectionCreate(DBConnectionBase):
    """创建数据库连接请求模式"""
    password: str = Field(..., description="密码")


class DBConnectionUpdate(BaseModel):
    """更新数据库连接请求模式"""
    id: int
    name: Optional[str] = Field(None, description="连接名称")
    db_type: Optional[str] = Field(None, description="数据库类型：mysql, postgresql, sqlite, oracle, sqlserver")
    host: Optional[str] = Field(None, description="主机地址")
    port: Optional[int] = Field(None, description="端口")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    database: Optional[str] = Field(None, description="数据库名")
    params: Optional[str] = Field(None, description="连接参数")
    status: Optional[bool] = Field(None, description="连接状态")
    remark: Optional[str] = Field(None, description="备注")


class DBConnectionInDB(DBConnectionBase):
    """数据库中的连接模式"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DBConnectionList(BaseModel):
    """连接列表响应模式"""
    items: List[DBConnectionInDB]
    total: int


class DBConnectionTest(BaseModel):
    """测试连接请求模式"""
    id: Optional[int] = Field(None, description="连接ID，如果提供则使用已保存的连接信息")
    db_type: Optional[str] = Field(None, description="数据库类型：mysql, postgresql, sqlite, oracle, sqlserver")
    host: Optional[str] = Field(None, description="主机地址")
    port: Optional[int] = Field(None, description="端口")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    database: Optional[str] = Field(None, description="数据库名")
    params: Optional[str] = Field(None, description="连接参数")
