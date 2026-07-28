from typing import Any, Generic, NewType, TypeVar

from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.models import Model

Total = NewType("Total", int)
ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    def get_schema_model(self):
        raise NotImplementedError

    async def _to_schema(self, obj: ModelType):
        """将数据库模型转换为 schema 模型"""
        schema_model = self.get_schema_model()
        obj_dict = {}
        for field_name in obj._meta.db_fields:
            value = getattr(obj, field_name)
            obj_dict[field_name] = value

        if hasattr(obj, 'created_at'):
            obj_dict['created_at'] = obj.created_at
        if hasattr(obj, 'updated_at'):
            obj_dict['updated_at'] = obj.updated_at

        return schema_model.model_validate(obj_dict)

    async def get(self, id: int) -> ModelType:
        return await self.model.get(id=id)

    async def list(self, page: int, page_size: int, search: Q = Q(), order: list = []) -> tuple[Total, list[ModelType]]:
        query = self.model.filter(search)
        return await query.count(), await query.offset((page - 1) * page_size).limit(page_size).order_by(*order)

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump()
        obj = self.model(**obj_dict)
        await obj.save()
        return obj

    async def update(self, id: int, obj_in: UpdateSchemaType | dict[str, Any]) -> ModelType:
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude={"id"})
        obj = await self.get(id=id)
        obj = obj.update_from_dict(obj_dict)
        await obj.save()
        return obj

    async def remove(self, id: int) -> None:
        obj = await self.get(id=id)
        await obj.delete()
