from typing import Optional, Tuple

from app.core.crud import CRUDBase
from app.models.conn import DBConnection
from app.schemas.conn import DBConnectionCreate, DBConnectionUpdate
from app.services.conn_manager import db_connector
from app.utils.password import get_password_hash, verify_password
from app.utils.encryption import encrypt_password, decrypt_password


class DBConnectionController(CRUDBase[DBConnection, DBConnectionCreate, DBConnectionUpdate]):
    def __init__(self):
        super().__init__(model=DBConnection)

    async def create(self, obj_in: DBConnectionCreate) -> DBConnection:
        """创建数据库连接，密码可逆加密存储"""
        obj_dict = obj_in.model_dump()
        obj_dict["password"] = encrypt_password(obj_dict["password"])
        obj = self.model(**obj_dict)
        await obj.save()
        return obj

    async def update(self, id: int, obj_in: DBConnectionUpdate) -> DBConnection:
        """更新数据库连接，如果提供了新密码则可逆加密存储"""
        obj_dict = obj_in.model_dump(exclude_unset=True, exclude={"id"})
        obj = await self.get(id=id)
        
        if "password" in obj_dict and obj_dict["password"]:
            obj_dict["password"] = encrypt_password(obj_dict["password"])
        
        obj = obj.update_from_dict(obj_dict)
        await obj.save()
        return obj

    async def get_by_name(self, name: str) -> Optional[DBConnection]:
        """根据名称获取数据库连接"""
        return await self.model.filter(name=name).first()
    
    async def get_decrypted_connection(self, id: int) -> Optional[dict]:
        """获取解密后的连接信息，用于实际数据库操作"""
        conn = await self.get(id=id)
        if not conn:
            return None
        
        # 解密密码
        decrypted_password = decrypt_password(conn.password)
        if not decrypted_password:
            return None
        
        return {
            "id": conn.id,
            "name": conn.name,
            "db_type": conn.db_type,
            "host": conn.host,
            "port": conn.port,
            "username": conn.username,
            "password": decrypted_password,
            "database": conn.database,
            "params": conn.params,
            "status": conn.status,
            "remark": conn.remark
        }

    async def test_connection(
        self, id: Optional[int] = None, db_type: Optional[str] = None, 
        host: Optional[str] = None, port: Optional[int] = None, 
        username: Optional[str] = None, password: Optional[str] = None, 
        database: Optional[str] = None, params: Optional[str] = None
    ) -> Tuple[bool, str]:
        """测试数据库连接"""
        conn = None
        if id:
            conn = await self.get(id=id)
            db_type = conn.db_type
            host = conn.host
            port = conn.port
            username = conn.username
            password = decrypt_password(conn.password)
            if not password:
                if conn:
                    conn.status = 2
                    await conn.save()
                return False, "无法解密密码，请重新设置连接密码"
            database = conn.database
            params = conn.params
        
        if not all([db_type, host, port, username, password, database]):
            if conn:
                conn.status = 2
                await conn.save()
            return False, "缺少必要的连接参数"
        
        success, message = await db_connector.test_connection(
            db_type=db_type,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            params=params
        )
        
        if conn:
            conn.status = 1 if success else 2  # 1-已连接, 2-未连接
            await conn.save()
        
        return success, message


conn_controller = DBConnectionController()
