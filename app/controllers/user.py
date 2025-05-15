from datetime import datetime
from typing import List, Optional

from fastapi.exceptions import HTTPException

from app.core.crud import CRUDBase
from app.models.admin import User
from app.schemas.login import CredentialsSchema
from app.schemas.users import UserCreate, UserUpdate
from app.utils.password import get_password_hash, verify_password

from .role import role_controller


class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.model.filter(email=email).first()

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.model.filter(username=username).first()

    async def create_user(self, obj_in: UserCreate) -> User:
        obj_in.password = get_password_hash(password=obj_in.password)
        obj = await self.create(obj_in)
        return obj    
    
    async def update_last_login(self, id: int) -> None:
        user = await self.model.get(id=id)
        user.last_login = datetime.now()
        await user.save()

    async def authenticate(self, credentials: CredentialsSchema) -> tuple[Optional["User"], Optional[str]]:
        """验证用户登录
        
        Returns:
            tuple: (User, error_message)
            - 如果验证成功，返回 (user, None)
            - 如果验证失败，返回 (None, error_message)
        """
        user = await self.model.filter(username=credentials.username).first()
        if not user:
            return None, "无效的用户名"
        verified = verify_password(credentials.password, user.password)
        if not verified:
            return None, "密码错误"
        if not user.is_active:
            return None, "用户已被禁用"
        return user, None

    async def update_roles(self, user: User, role_ids: List[int]) -> None:
        await user.roles.clear()
        for role_id in role_ids:
            role_obj = await role_controller.get(id=role_id)
            await user.roles.add(role_obj)

    async def reset_password(self, user_id: int):
        user_obj = await self.get(id=user_id)
        if user_obj.is_superuser:
            raise HTTPException(status_code=403, detail="不允许重置超级管理员密码")
        user_obj.password = get_password_hash(password="123456")
        await user_obj.save()


user_controller = UserController()
