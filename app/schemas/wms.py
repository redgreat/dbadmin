from typing import List
from decimal import Decimal

from pydantic import BaseModel, Field, validator


class WmsDeleteBatchIn(BaseModel):
    """批量删除入参"""
    stock_ids: List[str] = Field(default_factory=list, description="单据Id列表，逗号分隔后端已拆分")
    operator_id: str = Field(default="", description="操作人Id（GUID格式）")


class WmsRestoreLogicalIn(BaseModel):
    """逻辑删除恢复入参"""
    stock_id: str = Field(..., description="单据Id")
    operator_id: str = Field(..., description="删除人Id（GUID格式）")


class WmsValidateRequest(BaseModel):
    """单据验证请求"""
    stock_ids: List[str] = Field(default_factory=list, description="单据Id列表")
    validate_type: str = Field(..., description="验证类型: logical_delete, physical_delete, restore")


class PriceQueryIn(BaseModel):
    """价格查询入参"""
    stock_code: str = Field(default="", description="入库单编码")
    material_name: str = Field(default="", description="物料名称")
    new_price: str = Field(default="", description="修改后价格")

    @validator('new_price')
    def validate_price(cls, v):
        if v:  # 非空时验证格式
            try:
                Decimal(v)  # 验证是否为有效数字
            except:
                raise ValueError('价格格式不正确，应为有效的数字')
        return v


class PriceModifyIn(BaseModel):
    """价格修改入参"""
    detail_id: str = Field(..., description="明细Id")
    new_price: str = Field(..., description="修改后价格")

    @validator('new_price')
    def validate_price(cls, v):
        try:
            Decimal(v)  # 验证是否为有效数字
        except:
            raise ValueError('价格格式不正确，应为有效的数字')
        return v


class PriceQueryResult(BaseModel):
    """价格查询结果"""
    detail_id: str = Field(..., description="明细Id")
    material_name: str = Field(..., description="物料名称")
    original_price: str = Field(..., description="原价格")
    new_price: str = Field(..., description="新价格")


# FCC关联功能相关模型
class RelationItem(BaseModel):
    """FCC报销单与仓储对账单对应关系"""
    fcc_no: str = Field(..., description="FCC报销单号")
    wms_nos: List[str] = Field(..., description="仓储对账单号列表")


class FccParseIn(BaseModel):
    """解析请求模型"""
    input_text: str = Field(..., description="批量输入文本")


class FccValidateIn(BaseModel):
    """验证请求模型"""
    relations: List[RelationItem] = Field(..., description="对应关系列表")


class FccSubmitIn(BaseModel):
    """提交请求模型"""
    relations: List[RelationItem] = Field(..., description="对应关系列表")


class ParseResult(BaseModel):
    """解析结果模型"""
    relations: List[RelationItem] = Field(..., description="对应关系列表")
    total_fcc: int = Field(..., description="FCC报销单总数")
    total_wms: int = Field(..., description="仓储对账单总数")


class ValidateResult(BaseModel):
    """验证结果模型"""
    valid: bool = Field(..., description="是否验证通过")
    not_found_fcc: List[str] = Field(default_factory=list, description="不存在的FCC报销单列表")
    not_found_wms: List[str] = Field(default_factory=list, description="不存在的仓储对账单列表")
    message: str = Field(..., description="验证消息")


class TaskProgress(BaseModel):
    """任务进度模型"""
    total: int = Field(..., description="总数")
    processed: int = Field(..., description="已处理数")
    success: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")


class FailedItem(BaseModel):
    """失败项模型"""
    fcc_no: str = Field(..., description="FCC报销单号")
    wms_no: str = Field(..., description="仓储对账单号")
    reason: str = Field(..., description="失败原因")


class TaskResult(BaseModel):
    """任务结果模型"""
    success_count: int = Field(..., description="成功数量")
    failed_items: List[FailedItem] = Field(default_factory=list, description="失败项列表")


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, processing, completed, failed")
    progress: TaskProgress = Field(..., description="任务进度")
    result: TaskResult = None  # type: ignore
    created_at: str = Field(..., description="创建时间")
    finished_at: str = None  # type: ignore
