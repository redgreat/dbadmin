# This is a temporary file for fixing formatting issues
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

    async def get_menu_buttons(self, menu_id: str | int) -> List[ButtonRead]:
        """获取菜单下的所有按钮"""
        if menu_id == "all":
            # 获取所有按钮，按菜单分组
            buttons = await Button.all().prefetch_related('menu').order_by("menu_id", "order")
            # 按菜单分组返回
            menu_buttons = {}
            for button in buttons:
                menu = button.menu
                if not menu:
                    continue
                if menu.id not in menu_buttons:
                    menu_buttons[menu.id] = {
                        "id": menu.id,
                        "name": menu.name,
                        "buttons": []
                    }
                menu_buttons[menu.id]["buttons"].append(await self._to_schema(button))
            return list(menu_buttons.values())
        else:
            # 获取指定菜单的按钮
            buttons = await Button.filter(menu_id=menu_id).order_by("order")
            return [await self._to_schema(button) for button in buttons]

    async def get_role_buttons(self, role_id: int) -> List[ButtonRead]:
        """获取角色的按钮权限"""
        role = await Role.get_or_none(id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        
        buttons = await role.buttons.all()
        return [await self._to_schema(button) for button in buttons]

    async def set_role_buttons(self, role_id: int, button_ids: List[int]) -> None:
        """设置角色的按钮权限"""
        role = await Role.get_or_none(id=role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # 清除现有按钮权限
        await role.buttons.clear()
        
        if button_ids:
            # 添加新的按钮权限
            buttons = await Button.filter(id__in=button_ids)
            if buttons:
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
