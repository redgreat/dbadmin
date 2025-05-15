from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException

from app.controllers.button import button_controller
from app.core.dependency import get_current_user, DependPermisson
from app.models.admin import User, Menu
from app.schemas.base import ResponseSchema
from app.schemas.buttons import ButtonCreate, ButtonRead, ButtonUpdate

router = APIRouter()


@router.post(
    "", response_model=ResponseSchema[ButtonRead],
    summary="创建按钮"
)
async def create_button(
    data: ButtonCreate,
    current_user: User = Depends(get_current_user)
) -> ResponseSchema[ButtonRead]:
    """创建按钮权限"""
    # 检查菜单是否存在
    menu = await Menu.get_or_none(id=data.menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail=f"Menu {data.menu_id} not found")
    button = await button_controller.create_button(data)
    return ResponseSchema(data=button)


@router.put(
    "/{button_id}", response_model=ResponseSchema[ButtonRead],
    summary="更新按钮"
)
async def update_button(
    button_id: int,
    data: ButtonUpdate,
    current_user: User = Depends(get_current_user)
) -> ResponseSchema[ButtonRead]:
    """更新按钮权限"""
    try:
        button = await button_controller.update_button(button_id, data)
        return ResponseSchema(data=button)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{button_id}", response_model=ResponseSchema,
    summary="删除按钮"
)
async def delete_button(
    button_id: int,
    current_user: User = Depends(get_current_user)
) -> ResponseSchema:
    """删除按钮权限"""
    try:
        await button_controller.delete_button(button_id)
        return ResponseSchema()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/list/menu/{menu_id}", response_model=ResponseSchema[List[dict]],
    summary="获取菜单按钮"
)
async def get_menu_buttons(
    menu_id: int,
    current_user: User = Depends(get_current_user)
) -> ResponseSchema[List[dict]]:
    """获取指定菜单下的所有按钮"""
    try:
        buttons = await button_controller.get_menu_buttons(menu_id)
        return ResponseSchema(data=buttons)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/menu-group", response_model=ResponseSchema[List[dict]],
    summary="获取所有按钮(按菜单分组)"
)
async def get_buttons_menu_group(
    current_user: User = Depends(get_current_user)
) -> ResponseSchema[List[dict]]:
    """获取所有按钮并按菜单分组返回"""
    try:
        buttons = await button_controller.get_all_buttons_by_menu()
        return ResponseSchema(data=buttons)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/role/{role_id}", response_model=ResponseSchema[List[dict]],
    summary="获取角色按钮"
)
async def get_role_buttons(
    role_id: int,
    current_user: User = Depends(get_current_user)
) -> ResponseSchema[List[dict]]:
    """获取角色的按钮权限"""
    try:
        buttons = await button_controller.get_role_buttons(role_id)
        return ResponseSchema(data=buttons)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/role/{role_id}", response_model=ResponseSchema,
    summary="设置角色按钮"
)
async def set_role_buttons(
    role_id: int,
    button_ids: List[int],
    current_user: User = Depends(get_current_user)
) -> ResponseSchema:
    """设置角色的按钮权限"""
    try:
        await button_controller.set_role_buttons(role_id, button_ids)
        return ResponseSchema()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/check", response_model=ResponseSchema[bool],
    summary="检查按钮权限"
)
async def check_button_permission(
    menu_id: int = Query(..., description="菜单ID"),
    button_code: str = Query(..., description="按钮代码"),
    current_user: User = Depends(get_current_user)
) -> ResponseSchema[bool]:
    """检查当前用户是否有指定按钮的权限"""
    try:
        has_permission = await button_controller.check_button_permission(
            current_user.id, menu_id, button_code
        )
        return ResponseSchema(data=has_permission)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))