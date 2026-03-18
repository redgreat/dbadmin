from typing import Optional, List, Dict, Any
from datetime import datetime

from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.models.dict import Dict
from app.schemas.dict import DictCreate, DictUpdate


class DictController(CRUDBase[Dict, DictCreate, DictUpdate]):
    def __init__(self):
        super().__init__(model=Dict)

    async def get_by_code(self, code: str) -> Optional[Dict]:
        """根据编码获取字典"""
        return await self.model.filter(code=code, deleted=False).first()

    async def get_children_by_parent_code(self, parent_code: str) -> List[Dict]:
        """根据父级编码获取子级字典列表"""
        return await self.model.filter(parent_code=parent_code, deleted=False).order_by("created_at")

    async def get_root_dicts(self) -> List[Dict]:
        """获取根级字典（parent_code为空）"""
        return await self.model.filter(parent_code__isnull=True, deleted=False).order_by("created_at")

    async def check_code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        """检查编码是否已存在"""
        query = self.model.filter(code=code, deleted=False)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """检查名称是否已存在"""
        query = self.model.filter(name=name, deleted=False)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def has_children(self, code: str) -> bool:
        """检查是否存在子级字典"""
        return await self.model.filter(parent_code=code, deleted=False).exists()

    async def get_dict_tree(self) -> List[Dict[str, Any]]:
        """获取字典树形结构"""
        async def build_tree(parent_code: Optional[str] = None, level: int = 0) -> List[Dict[str, Any]]:
            if level >= 3:  # 最多三层
                return []

            if parent_code is None:
                dicts = await self.get_root_dicts()
            else:
                dicts = await self.get_children_by_parent_code(parent_code)

            result = []
            for dict_item in dicts:
                dict_dict = await dict_item.to_dict()
                children = await build_tree(dict_item.code, level + 1)
                if children:
                    dict_dict["children"] = children
                result.append(dict_dict)

            return result

        return await build_tree()

    async def get_dict_options(self, code: str) -> List[Dict[str, Any]]:
        """根据编码获取字典选项（用于下拉框）"""
        async def build_options(parent_code: Optional[str] = None, level: int = 0) -> List[Dict[str, Any]]:
            if level >= 3:  # 最多三层
                return []

            if parent_code is None:
                dicts = await self.get_root_dicts()
            else:
                dicts = await self.get_children_by_parent_code(parent_code)

            result = []
            for dict_item in dicts:
                option = {
                    "label": dict_item.name,
                    "value": dict_item.code,
                }
                children = await build_options(dict_item.code, level + 1)
                if children:
                    option["children"] = children
                result.append(option)

            return result

        # 如果指定了code，从该code开始获取
        if code:
            dict_item = await self.get_by_code(code)
            if dict_item:
                return await build_options(code, 0)

        return await build_options()

    async def soft_delete(self, id: int) -> None:
        """软删除字典"""
        obj = await self.get(id=id)
        obj.deleted = True
        obj.deleted_at = datetime.now()
        await obj.save()

    async def list_with_filter(
        self, page: int, page_size: int, parent_code: Optional[str] = None
    ) -> tuple:
        """带筛选条件的分页查询"""
        query = self.model.filter(deleted=False)

        if parent_code is not None:
            if parent_code == "":
                # 查询根级字典
                query = query.filter(parent_code__isnull=True)
            else:
                query = query.filter(parent_code=parent_code)

        total = await query.count()
        items = await query.offset((page - 1) * page_size).limit(page_size).order_by("-created_at")
        return total, items


dict_controller = DictController()
