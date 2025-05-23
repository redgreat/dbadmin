from typing import Optional, Tuple

from app.core.crud import CRUDBase
from app.models.conn import DBConnection
from app.schemas.conn import DBConnectionCreate, DBConnectionUpdate
from app.services.db_connector import db_connector
from app.utils.password import get_password_hash, verify_password


class DBConnectionController(CRUDBase[DBConnection, DBConnectionCreate, DBConnectionUpdate]):
    def __init__(self):
        super().__init__(model=DBConnection)

    async def create(self, obj_in: DBConnectionCreate) -> DBConnection:
        """创建数据库连接，密码加密存储"""
        obj_dict = obj_in.model_dump()
        # 加密密码
        obj_dict["password"] = get_password_hash(obj_dict["password"])
        obj = self.model(**obj_dict)
        await obj.save()
        return obj

    async def update(self, id: int, obj_in: DBConnectionUpdate) -> DBConnection:
        """更新数据库连接，如果提供了新密码则加密存储"""
        obj_dict = obj_in.model_dump(exclude_unset=True, exclude={"id"})
        obj = await self.get(id=id)
        
        # 如果提供了新密码，则加密
        if "password" in obj_dict and obj_dict["password"]:
            obj_dict["password"] = get_password_hash(obj_dict["password"])
        
        obj = obj.update_from_dict(obj_dict)
        await obj.save()
        return obj

    async def get_by_name(self, name: str) -> Optional[DBConnection]:
        """根据名称获取数据库连接"""
        return await self.model.filter(name=name).first()

    async def test_connection(
        self, id: Optional[int] = None, db_type: Optional[str] = None, 
        host: Optional[str] = None, port: Optional[int] = None, 
        username: Optional[str] = None, password: Optional[str] = None, 
        database: Optional[str] = None, params: Optional[str] = None
    ) -> Tuple[bool, str]:
        """测试数据库连接"""
        # 如果提供了ID，则使用已保存的连接信息
        if id:
            conn = await self.get(id=id)
            db_type = conn.db_type
            host = conn.host
            port = conn.port
            username = conn.username
            # 这里需要解密密码，但我们使用的是单向加密，所以无法解密
            # 在实际应用中，应该使用可逆加密或其他方式存储密码
            password = password  # 如果没有提供新密码，则无法测试
            database = conn.database
            params = conn.params
        
        # 确保所有必要的参数都已提供
        if not all([db_type, host, port, username, password, database]):
            return False, "缺少必要的连接参数"
        
        # 测试连接
        return await db_connector.test_connection(
            db_type=db_type,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            params=params
        )


db_connection_controller = DBConnectionController()
