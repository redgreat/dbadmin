from typing import List

from fastapi import Query
from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.models.admin import AuditLog
from app.schemas.auditlog import AuditLogQuerySchema, AuditLogSchema


class AuditLogController(CRUDBase):
    def get_schema_model(self):
        return AuditLogSchema

    async def get_logs(self, query: AuditLogQuerySchema) -> tuple[List[AuditLogSchema], int]:
        filters = Q()
        if query.username:
            filters &= Q(username__icontains=query.username)
        if query.module:
            filters &= Q(module__icontains=query.module)
        if query.method:
            filters &= Q(method=query.method)
        if query.path:
            filters &= Q(path__icontains=query.path)
        if query.status is not None:
            filters &= Q(status=query.status)
        if query.start_time:
            filters &= Q(created_at__gte=query.start_time)
        if query.end_time:
            filters &= Q(created_at__lte=query.end_time)

        return await self._get_paginated_data(
            model=AuditLog,
            schema=AuditLogSchema,
            filters=filters,
            page=query.page,
            page_size=query.page_size,
            ordering=["-created_at"]
        )

    async def create_log(self, **kwargs) -> AuditLogSchema:
        log = await AuditLog.create(**kwargs)
        return await self._to_schema(log)
