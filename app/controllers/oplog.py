from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException
from tortoise.expressions import Q
from math import ceil

from app.core.crud import CRUDBase
from app.models.oplog import OpLog
from app.schemas.oplog import (
    OpLogCreateRequest,
    OpLogUpdateRequest,
    OpLogQueryRequest,
    OpLogResponse,
    OpLogListResponse
)
from app.log import logger


class OpLogCRUD(CRUDBase[OpLog, OpLogCreateRequest, OpLogUpdateRequest]):
    """
    运维日志CRUD操作类
    """
    
    def get_schema_model(self):
        return OpLogResponse


class OpLogController:
    """
    运维日志控制器
    """
    
    def __init__(self):
        self.crud = OpLogCRUD(OpLog)
    
    async def create_oplog(self, request: OpLogCreateRequest) -> OpLogResponse:
        """
        创建运维日志记录
        """
        try:
            oplog = await self.crud.create(request)
            return await self.crud._to_schema(oplog)
        except Exception as e:
            logger.error(f"创建运维日志失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"创建运维日志失败: {str(e)}")
    
    async def get_oplog(self, oplog_id: int) -> OpLogResponse:
        """
        根据ID获取运维日志
        """
        try:
            oplog = await self.crud.get(oplog_id)
            return await self.crud._to_schema(oplog)
        except Exception as e:
            logger.error(f"获取运维日志失败: {str(e)}")
            raise HTTPException(status_code=404, detail="运维日志不存在")
    
    async def query_oplogs(self, request: OpLogQueryRequest) -> OpLogListResponse:
        """
        查询运维日志列表
        """
        try:
            # 构建查询条件
            search_conditions = Q()
            
            if request.logger:
                search_conditions &= Q(logger__icontains=request.logger)
            
            if request.operater:
                search_conditions &= Q(operater__icontains=request.operater)
            
            if request.start_date:
                search_conditions &= Q(final_modify_time__gte=request.start_date)
            
            if request.end_date:
                search_conditions &= Q(final_modify_time__lte=request.end_date)
            
            # 执行查询
            total, oplogs = await self.crud.list(
                page=request.page,
                page_size=request.page_size,
                search=search_conditions,
                order=["-final_modify_time", "-created_at"]
            )
            
            # 转换为响应模型
            records = []
            for oplog in oplogs:
                record = await self.crud._to_schema(oplog)
                records.append(record)
            
            # 计算分页信息
            total_pages = ceil(total / request.page_size)
            pagination = {
                "total": total,
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": total_pages,
                "has_next": request.page < total_pages,
                "has_prev": request.page > 1
            }
            
            return OpLogListResponse(
                records=records,
                pagination=pagination
            )
            
        except Exception as e:
            logger.error(f"查询运维日志失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"查询运维日志失败: {str(e)}")
    
    async def update_oplog(self, oplog_id: int, request: OpLogUpdateRequest) -> OpLogResponse:
        """
        更新运维日志
        """
        try:
            oplog = await self.crud.update(oplog_id, request)
            return await self.crud._to_schema(oplog)
        except Exception as e:
            logger.error(f"更新运维日志失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"更新运维日志失败: {str(e)}")
    
    async def delete_oplog(self, oplog_id: int) -> Dict[str, str]:
        """
        删除运维日志
        """
        try:
            await self.crud.remove(oplog_id)
            return {"message": "运维日志删除成功"}
        except Exception as e:
            logger.error(f"删除运维日志失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"删除运维日志失败: {str(e)}")
    
    @staticmethod
    async def create_operation_log(
        logger_type: str,
        operation_content: Dict[str, Any],
        operator: str,
        modify_time: Optional[datetime] = None
    ) -> OpLog:
        """
        创建运维操作日志的公共方法
        
        Args:
            logger_type: 操作类型
            operation_content: 操作内容
            operator: 操作人
            modify_time: 修改时间，默认为当前时间
        
        Returns:
            创建的运维日志对象
        """
        try:
            if modify_time is None:
                modify_time = datetime.now()
            
            oplog = await OpLog.create(
                logger=logger_type,
                chgmsg=operation_content,
                operater=operator,
                final_modify_time=modify_time
            )
            
            logger.info(f"运维日志记录成功: {logger_type} - {operator}")
            return oplog
            
        except Exception as e:
            logger.error(f"记录运维日志失败: {str(e)}")
            # 这里不抛出异常，避免影响主业务流程
            return None


# 创建控制器实例
oplog_controller = OpLogController()