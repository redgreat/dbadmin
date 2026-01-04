from typing import Optional, Tuple

from app.core.crud import CRUDBase
from app.models.conn import DBConnection
from app.schemas.conn import DBConnectionCreate, DBConnectionUpdate
import asyncpg
import aiomysql
from app.services.db_pool import db_pool
from app.utils.password import get_password_hash


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
        try:
            await db_pool.register_pool(
                conn_id=obj.id,
                db_type=obj_in.db_type,
                host=obj_in.host,
                port=obj_in.port,
                username=obj_in.username,
                password=obj_in.password,
                database=obj_in.database,
                params=obj_in.params,
            )
        except Exception:
            pass
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
        try:
            if obj_in.password:
                await db_pool.register_pool(
                    conn_id=obj.id,
                    db_type=obj_in.db_type or obj.db_type,
                    host=obj_in.host or obj.host,
                    port=obj_in.port or obj.port,
                    username=obj_in.username or obj.username,
                    password=obj_in.password,
                    database=obj_in.database or obj.database,
                    params=obj_in.params or obj.params,
                )
        except Exception:
            pass
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
            password = password
            database = conn.database
            params = conn.params
        
        if not all([db_type, host, port, username, password, database]):
            return False, "缺少必要的连接参数"
        
        # 测试连接
        try:
            if db_type == "postgresql":
                conn = await asyncpg.connect(
                    host=host,
                    port=port,
                    user=username,
                    password=password,
                    database=database,
                    timeout=5,
                )
                await conn.execute("SELECT 1")
                await conn.close()
                return True, "连接成功"
            elif db_type == "mysql":
                conn = await aiomysql.connect(
                    host=host,
                    port=port,
                    user=username,
                    password=password,
                    db=database,
                    connect_timeout=5,
                )
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                conn.close()
                return True, "连接成功"
            else:
                return False, f"不支持的数据库类型: {db_type}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"


conn_controller = DBConnectionController()
