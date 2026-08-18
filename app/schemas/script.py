from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PythonScriptBase(BaseModel):
    """Python脚本基础模型"""
    name: str = Field(..., description="脚本名称")
    code: str = Field(..., description="脚本内容")
    description: str | None = Field(None, description="脚本描述")
    status: bool | None = Field(True, description="是否启用")


class PythonScriptCreate(PythonScriptBase):
    """创建脚本请求模型"""
    pass


class PythonScriptUpdate(BaseModel):
    """更新脚本请求模型"""
    name: str | None = Field(None, description="脚本名称")
    code: str | None = Field(None, description="脚本内容")
    description: str | None = Field(None, description="脚本描述")
    status: bool | None = Field(None, description="是否启用")


class PythonScriptInDB(PythonScriptBase):
    """数据库中的脚本模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PythonScriptList(BaseModel):
    """脚本列表响应模型"""
    items: list[PythonScriptInDB]
    total: int


class ScriptRunLogBase(BaseModel):
    """脚本执行日志基础模型"""
    script_id: int = Field(..., description="脚本ID")
    status: str = Field(..., description="执行状态: success, failed, running")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")
    duration: int | None = Field(None, description="执行时长(秒)")
    output: str | None = Field(None, description="执行输出")
    error: str | None = Field(None, description="错误信息")


class ScriptRunLogInDB(ScriptRunLogBase):
    """数据库中的脚本执行日志模型"""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScriptRunLogList(BaseModel):
    """脚本执行日志列表响应模型"""
    items: list[ScriptRunLogInDB]
    total: int


class ScriptExecuteResponse(BaseModel):
    """脚本执行响应模型"""
    success: bool
    message: str
    log_id: int | None = None
