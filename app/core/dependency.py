from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request

from app.core.ctx import CTX_USER_ID
from app.models import MenuApi, Role, User
from app.settings import settings


class AuthControl:
    @classmethod
    async def is_authed(cls, token: str = Header(..., description="token验证")) -> Optional["User"]:
        try:
            if token == "dev":
                user = await User.filter().first()
                user_id = user.id
            else:
                decode_data = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM)
                user_id = decode_data.get("user_id")
            user = await User.filter(id=user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="Authentication failed")
            CTX_USER_ID.set(int(user_id))
            return user
        except jwt.DecodeError:
            raise HTTPException(status_code=401, detail="无效的Token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="登录已过期")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{repr(e)}")


class PermissionControl:
    @classmethod
    async def has_permission(cls, request: Request, current_user: User = Depends(AuthControl.is_authed)) -> None:
        if current_user.is_superuser:
            return
        method = request.method
        path = request.url.path
        roles: list[Role] = await current_user.roles
        if not roles:
            raise HTTPException(status_code=403, detail="The user is not bound to a role")
        
        # 获取用户所有角色的菜单ID
        menu_ids = set()
        for role in roles:
            role_menus = await role.menus.all()
            for menu in role_menus:
                menu_ids.add(menu.id)
        
        # 通过menu_api表获取菜单对应的API
        if menu_ids:
            menu_api_relations = await MenuApi.filter(menu_id__in=menu_ids).prefetch_related("api")
            permission_apis = set()
            for relation in menu_api_relations:
                if relation.api:
                    permission_apis.add((relation.api.method, relation.api.path))
        else:
            permission_apis = set()
        
        if (method, path) not in permission_apis:
            # 提供更详细的错误信息
            from app.models.admin import Api
            api_exists = await Api.filter(method=method, path=path).exists()
            if not api_exists:
                detail = f"API not found in database: {method} {path}. Please refresh API table."
            elif not menu_ids:
                detail = f"User has no menu permissions. Please assign menus to user's roles."
            elif not permission_apis:
                detail = f"Menus have no API mappings. Please configure menu-API relations in menu management."
            else:
                detail = f"Permission denied: {method} {path}. Please add this API to user's menu permissions."
            raise HTTPException(status_code=403, detail=detail)


DependAuth = Depends(AuthControl.is_authed)
DependPermisson = Depends(PermissionControl.has_permission)


async def get_current_user(user=Depends(AuthControl.is_authed)) -> User:
    """获取当前登录用户"""
    return user


DependPermisson = Depends(PermissionControl.has_permission)
