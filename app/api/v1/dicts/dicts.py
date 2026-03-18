import logging
from pypinyin import lazy_pinyin

from fastapi import APIRouter, Query

from app.controllers.dict import dict_controller
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.dict import *

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_code(name: str, parent_code: str = None) -> str:
    """根据名称生成编码"""
    # 使用pypinyin将中文转换为拼音首字母
    pinyin_list = lazy_pinyin(name)
    # 取每个拼音的首字母，组成编码前缀
    prefix = ''.join([py[0] if py else '' for py in pinyin_list]).lower()
    
    if not parent_code:
        # 一级字典：prefix_1
        return f"{prefix}_1"
    else:
        # 子级字典：parent_code-n
        # 从父级编码中提取基础部分
        if '-' in parent_code:
            base_code = parent_code.split('-')[0]
        else:
            base_code = parent_code.replace('_1', '')
        
        # 计算当前层级
        level = parent_code.count('-') + 2  # 父级层级+1
        
        if level == 2:
            # 二级字典：prefix_1-1
            return f"{base_code}_1-1"
        elif level == 3:
            # 三级字典：prefix_1-1-1
            return f"{base_code}_1-1-1"
        
        return f"{base_code}_1"


@router.get("/list", summary="查看字典列表")
async def list_dict(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    parent_code: str = Query(None, description="父级编码"),
):
    """分页查询字典列表"""
    total, items = await dict_controller.list_with_filter(
        page=page, page_size=page_size, parent_code=parent_code
    )
    data = [await item.to_dict() for item in items]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/tree", summary="获取字典树")
async def get_dict_tree():
    """获取字典树形结构"""
    tree_data = await dict_controller.get_dict_tree()
    return Success(data=tree_data)


@router.get("/options", summary="获取字典选项")
async def get_dict_options(
    code: str = Query(None, description="字典编码"),
):
    """根据编码获取字典选项（用于下拉框）"""
    options = await dict_controller.get_dict_options(code=code)
    return Success(data=options)


@router.get("/get", summary="查看字典详情")
async def get_dict(
    id: int = Query(..., description="字典ID"),
):
    """获取字典详情"""
    result = await dict_controller.get(id=id)
    return Success(data=await result.to_dict())


@router.post("/create", summary="创建字典")
async def create_dict(
    dict_in: DictCreate,
):
    """创建字典"""
    # 检查字典名称是否已存在
    if await dict_controller.check_name_exists(dict_in.name):
        return Fail(msg="字典名称已存在")
    
    # 自动生成编码
    code = generate_code(dict_in.name, dict_in.parent_code)
    
    # 确保编码唯一，如果重复则添加序号
    base_code = code
    counter = 1
    while await dict_controller.check_code_exists(code):
        if '-' in base_code:
            # 子级字典：prefix_1-n, prefix_1-1-n
            parts = base_code.rsplit('-', 1)
            code = f"{parts[0]}-{counter}"
        else:
            # 一级字典：prefix_n
            parts = base_code.rsplit('_', 1)
            code = f"{parts[0]}_{counter}"
        counter += 1
    
    # 检查父级编码是否存在
    if dict_in.parent_code:
        parent = await dict_controller.get_by_code(dict_in.parent_code)
        if not parent:
            return Fail(msg="父级字典不存在")
        
        # 检查层级深度（最多三层）
        level = 1
        current_code = parent.parent_code
        while current_code and level < 3:
            current_dict = await dict_controller.get_by_code(current_code)
            if current_dict:
                current_code = current_dict.parent_code
                level += 1
            else:
                break
        
        if level >= 3:
            return Fail(msg="字典层级不能超过三层")
    
    # 创建字典，使用自动生成的编码
    dict_data = dict_in.model_dump()
    dict_data['code'] = code
    await dict_controller.create(obj_in=dict_data)
    return Success(msg=f"创建成功，编码：{code}")


@router.post("/update", summary="更新字典")
async def update_dict(
    dict_in: DictUpdate,
):
    """更新字典"""
    # 获取原字典信息
    old_dict = await dict_controller.get(id=dict_in.id)
    
    # 如果修改了名称，检查是否重复
    if dict_in.name and dict_in.name != old_dict.name:
        if await dict_controller.check_name_exists(dict_in.name, exclude_id=dict_in.id):
            return Fail(msg="字典名称已存在")
    
    # 更新时只更新名称，不修改编码
    update_data = {'name': dict_in.name} if dict_in.name else {}
    
    await dict_controller.update(id=dict_in.id, obj_in=update_data)
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除字典")
async def delete_dict(
    id: int = Query(..., description="字典ID"),
):
    """删除字典（软删除）"""
    # 获取字典信息
    dict_obj = await dict_controller.get(id=id)

    # 检查是否存在子级字典
    if await dict_controller.has_children(dict_obj.code):
        return Fail(msg="存在子级字典，无法删除")

    # 执行软删除
    await dict_controller.soft_delete(id=id)
    return Success(msg="删除成功")
