from typing import List

from app.core.crud import CRUDBase
from app.log import logger
from app.models.admin import Api, Menu, MenuApi, Role
from app.schemas.roles import RoleCreate, RoleUpdate


class RoleController(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def __init__(self):
        super().__init__(model=Role)

    async def is_exist(self, name: str) -> bool:
        return await self.model.filter(name=name).exists()

    async def update_roles(self, role: Role, menu_ids: List[int]) -> None:
        """
        更新角色权限
        菜单权限自动关联对应的API权限（通过menu_api表映射）
        
        Args:
            role: 角色对象
            menu_ids: 菜单ID列表
        """
        # 清空现有菜单权限
        await role.menus.clear()
        
        # 获取菜单对象并验证存在性
        valid_menu_ids = []
        
        for menu_id in menu_ids:
            menu_obj = await Menu.filter(id=menu_id).first()
            if menu_obj:
                valid_menu_ids.append(menu_id)
                await role.menus.add(menu_obj)
            else:
                logger.warning(f"菜单ID {menu_id} 不存在，已跳过")
        
        # 通过menu_api表获取菜单对应的API
        menu_api_relations = await MenuApi.filter(menu_id__in=valid_menu_ids).prefetch_related("api")
        
        # 收集所有API ID（去重）
        api_ids = set()
        for relation in menu_api_relations:
            if relation.api:
                api_ids.add(relation.api.id)
        
        # 更新角色的API权限（通过中间表role_menu_api）
        # 由于Role模型不再有apis字段，我们需要直接操作role_menu_api表
        # 但实际上我们改用另一种方式：在权限检查时动态计算
        
        logger.info(f"角色 {role.name} 权限更新完成: {len(valid_menu_ids)} 个菜单, 关联 {len(api_ids)} 个API")


role_controller = RoleController()
