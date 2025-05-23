from fastapi import APIRouter, Body, Query
from tortoise.expressions import Q

from app.controllers.conn import db_connection_controller
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.conn import DBConnectionCreate, DBConnectionTest, DBConnectionUpdate

router = APIRouter()


@router.get("/list", summary="获取数据库连接列表")
async def list_connections(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    name: str = Query(None, description="连接名称"),
    db_type: str = Query(None, description="数据库类型"),
    status: bool = Query(None, description="连接状态"),
):
    """获取数据库连接列表"""
    q = Q()
    if name:
        q &= Q(name__contains=name)
    if db_type:
        q &= Q(db_type=db_type)
    if status is not None:
        q &= Q(status=status)
    
    total, conn_objs = await db_connection_controller.list(
        page=page, page_size=page_size, search=q, order=["-updated_at"]
    )
    data = [await obj.to_dict(exclude_fields=["password"]) for obj in conn_objs]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/get", summary="获取数据库连接详情")
async def get_connection(
    conn_id: int = Query(..., description="连接ID"),
):
    """获取数据库连接详情"""
    conn_obj = await db_connection_controller.get(id=conn_id)
    data = await conn_obj.to_dict(exclude_fields=["password"])
    return Success(data=data)


@router.post("/create", summary="创建数据库连接")
async def create_connection(
    conn_in: DBConnectionCreate,
):
    """创建数据库连接"""
    # 检查名称是否已存在
    existing = await db_connection_controller.get_by_name(conn_in.name)
    if existing:
        return Fail(code=400, msg="连接名称已存在")
    
    # 创建连接
    await db_connection_controller.create(obj_in=conn_in)
    return Success(msg="创建成功")


@router.post("/update", summary="更新数据库连接")
async def update_connection(
    conn_in: DBConnectionUpdate,
):
    """更新数据库连接"""
    # 检查ID是否存在
    try:
        await db_connection_controller.get(id=conn_in.id)
    except Exception:
        return Fail(code=404, msg="连接不存在")
    
    # 如果更新了名称，检查名称是否已存在
    if conn_in.name:
        existing = await db_connection_controller.get_by_name(conn_in.name)
        if existing and existing.id != conn_in.id:
            return Fail(code=400, msg="连接名称已存在")
    
    # 更新连接
    await db_connection_controller.update(id=conn_in.id, obj_in=conn_in)
    return Success(msg="更新成功")


@router.delete("/delete", summary="删除数据库连接")
async def delete_connection(
    conn_id: int = Query(..., description="连接ID"),
):
    """删除数据库连接"""
    try:
        await db_connection_controller.remove(id=conn_id)
        return Success(msg="删除成功")
    except Exception as e:
        return Fail(code=400, msg=f"删除失败: {str(e)}")


@router.post("/test", summary="测试数据库连接")
async def test_connection(
    conn_test: DBConnectionTest,
):
    """测试数据库连接"""
    success, message = await db_connection_controller.test_connection(
        id=conn_test.id,
        db_type=conn_test.db_type,
        host=conn_test.host,
        port=conn_test.port,
        username=conn_test.username,
        password=conn_test.password,
        database=conn_test.database,
        params=conn_test.params,
    )
    
    if success:
        return Success(msg=message)
    else:
        return Fail(code=400, msg=message)
