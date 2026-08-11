from fastapi.routing import APIRoute, _IncludedRouter
from tortoise import connections

from app.core.crud import CRUDBase
from app.log import logger
from app.models.admin import Api
from app.schemas.apis import ApiCreate, ApiUpdate


def collect_api_routes(routes) -> list[APIRoute]:
    """递归遍历路由列表，收集所有需要鉴权的 APIRoute。"""
    result = []
    for route in routes:
        if isinstance(route, _IncludedRouter):
            result.extend(collect_api_routes(route.original_router.routes))
        elif isinstance(route, APIRoute) and len(route.dependencies) > 0:
            result.append(route)
    return result


class ApiController(CRUDBase[Api, ApiCreate, ApiUpdate]):
    def __init__(self):
        super().__init__(model=Api)

    async def sync_api_sequence(self):
        """同步PostgreSQL自增序列，避免手工插入ID后刷新API主键冲突。"""
        try:
            conn = connections.get("default")
            await conn.execute_query(
                """
                SELECT setval(
                    pg_get_serial_sequence('"api"', 'id'),
                    GREATEST(
                        COALESCE((SELECT MAX(id) FROM "api"), 0),
                        COALESCE((SELECT last_value FROM api_id_seq), 0)
                    ),
                    true
                )
                """
            )
        except Exception as e:
            logger.debug(f"同步API序列跳过或失败: {e}")

    async def refresh_api(self):
        from app.main import app

        api_routes = collect_api_routes(app.routes)

        all_api_list = []
        for route in api_routes:
            all_api_list.append((sorted(route.methods)[0], route.path_format))

        delete_api = []
        for api in await Api.all():
            if (api.method, api.path) not in all_api_list:
                delete_api.append((api.method, api.path))
        for item in delete_api:
            method, path = item
            logger.debug(f"API Deleted {method} {path}")
            await Api.filter(method=method, path=path).delete()

        await self.sync_api_sequence()

        for route in api_routes:
            method = sorted(route.methods)[0]
            path = route.path_format
            summary = route.summary
            tags = list(route.tags)[0]
            api_obj = await Api.filter(method=method, path=path).first()
            if api_obj:
                await api_obj.update_from_dict(dict(method=method, path=path, summary=summary, tags=tags)).save()
            else:
                logger.debug(f"API Created {method} {path}")
                await Api.create(**dict(method=method, path=path, summary=summary, tags=tags))


api_controller = ApiController()
