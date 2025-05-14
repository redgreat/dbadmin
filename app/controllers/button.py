from typing import List
from fastapi import HTTPException

from app.core.crud import CRUDBase
from app.models.admin import Button, Role, User
from app.schemas.buttons import ButtonCreate, ButtonRead, ButtonUpdate


class ButtonController(CRUDBase[Button, ButtonCreate, ButtonUpdate]):
    def __init__(self):
        super().__init__(model=Button)

    def get_schema_model(self):
        return ButtonRead
        
    async def _to_schema_dict(self, obj) -> dict:
        """转换为按钮数据字典"""
        schema = await self._to_schema(obj)
        return schema.model_dump()

    async def create_button(self, data: ButtonCreate) -> ButtonRead:
        """创建按钮"""
        button = await Button.create(**data.model_dump())
        return await self._to_schema(button)

    async def update_button(self, button_id: int, data: ButtonUpdate) -> ButtonRead:
        """更新按钮"""
        button = await Button.get_or_none(id=button_id)
        if not button:
            raise HTTPException(status_code=404, detail="Button not found")
        
        await button.update_from_dict(data.model_dump()).save()
        return await self._to_schema(button)

    async def delete_button(self, button_id: int) -> None:
        """删除按钮"""
        button = await Button.get_or_none(id=button_id)
        if not button:
            raise HTTPException(status_code=404, detail="Button not found")
        await button.delete()

    async def get_menu_buttons(self, menu_id: int) -> List[dict]:
        """获取指定菜单下的所有按钮"""
        buttons = await Button.filter(menu_id=menu_id).order_by("order")
        return [await self._to_schema_dict(button) for button in buttons]

    async def get_all_buttons_by_menu(self) -> List[dict]:
        """获取所有按钮，按菜单分组返回"""
        buttons = await Button.all().prefetch_related('menu').order_by("menu_id", "order")
        menu_buttons = []
        current_menu = None
        current_buttons = []
        
        for button in buttons:
            menu = button.menu
            if not menu:
                continue
            
            if current_menu is None:
                current_menu = menu
            elif current_menu.id != menu.id:
                # 添加前一个菜单的按钮组
                menu_buttons.append({
                    "id": current_menu.id,
                    "name": current_menu.name,
                    "buttons": [await self._to_schema_dict(btn) for btn in current_buttons]
                })
                current_menu = menu
                current_buttons = []
                
            current_buttons.append(button)
        
        # 添加最后一个菜单的按钮组
        if current_menu and current_buttons:
            menu_buttons.append({
                "id": current_menu.id,
                "name": current_menu.name,
                "buttons": [await self._to_schema_dict(btn) for btn in current_buttons]
            })
            
        return menu_buttons

    async def get_role_buttons(self, role_id: int) -> List[dict]:
        """获取角色的按钮权限"""
        role = await Role.get_or_none(id=role_id).prefetch_related('buttons')
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        return [await self._to_schema_dict(button) for button in role.buttons]

    async def set_role_buttons(self, role_id: int, button_ids: List[int]) -> None:
        """设置角色的按钮权限"""
        role = await Role.get_or_none(id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
            
        # 清除现有按钮权限
        await role.buttons.clear()
        
        if button_ids:
            # 获取要设置的按钮
            buttons = await Button.filter(id__in=button_ids)
            # 设置新的按钮权限
            await role.buttons.add(*buttons)

    async def check_button_permission(self, user_id: int, menu_id: int, button_code: str) -> bool:
        """检查用户是否有按钮权限"""
        user = await User.get_or_none(id=user_id)
        if not user:
            return False
            
        # 超级管理员拥有所有权限
        if user.is_superuser:
            return True
            
        # 获取用户角色的按钮权限，使用预加载优化查询性能
        user_roles = await user.roles.all().prefetch_related('buttons')
        for role in user_roles:
            has_permission = any(
                button.menu_id == menu_id and button.code == button_code
                for button in role.buttons
            )
            if has_permission:
                return True
                
        return False


button_controller = ButtonController()
