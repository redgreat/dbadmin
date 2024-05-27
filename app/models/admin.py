from tortoise import fields

from app.schemas.menus import MenuType

from .base import BaseModel, TimestampMixin
from .enums import MethodType


class User(BaseModel, TimestampMixin):
    username = fields.CharField(max_length=20, unique=True, description="用户名称")
    alias = fields.CharField(max_length=30, null=True, description="姓名")
    email = fields.CharField(max_length=255, unique=True, description="邮箱")
    phone = fields.CharField(max_length=20, null=True, description="电话")
    password = fields.CharField(max_length=128, null=True, description="密码")
    is_active = fields.BooleanField(default=True, description="是否激活")
    is_superuser = fields.BooleanField(default=False, description="是否为超级管理员")
    last_login = fields.DatetimeField(null=True, description="最后登录时间")
    roles = fields.ManyToManyField("models.Role", related_name="user_roles")

    class Meta:
        table = "user"

    class PydanticMeta:
        # todo
        # computed = ["full_name"]
        ...


class Role(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, unique=True, description="角色名称")
    desc = fields.CharField(max_length=500, null=True, blank=True, description="角色描述")
    menus = fields.ManyToManyField("models.Menu", related_name="role_menus")
    apis = fields.ManyToManyField("models.Api", related_name="role_apis")

    class Meta:
        table = "role"


class Api(BaseModel, TimestampMixin):
    path = fields.CharField(max_length=100, description="API路径")
    method = fields.CharEnumField(MethodType, description="请求方法")
    summary = fields.CharField(max_length=500, description="请求简介")
    tags = fields.CharField(max_length=100, description="API标签")

    class Meta:
        table = "api"


class Menu(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=20, description="菜单名称")
    remark = fields.JSONField(null=True, description="保留字段", blank=True)
    menu_type = fields.CharEnumField(MenuType, null=True, blank=True, description="菜单类型")
    icon = fields.CharField(max_length=100, null=True, blank=True, description="菜单图标")
    path = fields.CharField(max_length=100, description="菜单路径")
    order = fields.IntField(default=0, description="排序")
    parent_id = fields.IntField(default=0, max_length=10, description="父菜单ID")
    is_hidden = fields.BooleanField(default=False, description="是否隐藏")
    component = fields.CharField(max_length=100, description="组件")
    keepalive = fields.BooleanField(default=True, description="存活")
    redirect = fields.CharField(max_length=100, null=True, blank=True, description="重定向")

    class Meta:
        table = "menu"


class OperationLog(BaseModel, TimestampMixin):
    id: int = fields.IntField(default=0, max_length=10, description="自增主键")
    user_id = fields.IntField(description="操作用户Id")
    user_name = fields.CharField(max_length=50, description="操作用户姓名")
    status_code = fields.IntField(description="状态编码")
    client_ip: str = Field(description="请求客户端地址")
    request_method: str = Field(description="请求方法")
    api_path: str = Field(description="请求API地址")
    system: str = Field(description="客户端操作系统")
    browser: str = Field(description="请求浏览器")
    summary: str = Field(description="操作用户姓名")
    route_name: str = Field(description="路由名称")
    description: str = Field(description="描述")
    tags: Optional[list] = Field([], description="标签")
    process_time: float = Field(description="处理时长")
    params: str = Field(description="调用参数")
    logtime: Optional[datetime] = Field(description="日志写入时间")

    class Meta:
        table = "operationlog"


# class Dept(BaseModel, TimestampMixin):
#     name = fields.CharField(max_length=20, unique=True, description="部门名称")
#     desc = fields.CharField(max_length=500, null=True, blank=True, description="菜单描述")
#     is_deleted = fields.BooleanField(default=False, description="软删除标记")
#     order = fields.IntField(default=0, description="排序")
#     parent_id = fields.IntField(default=0, max_length=10, description="父部门ID")
# 
#     class Meta:
#         table = "dept"
