from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from user_agents import parse
import time
import datetime
import json

from .bgtask import BgTasks


class SimpleBaseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        response = await self.before_request(request) or self.app
        await response(request.scope, request.receive, send)
        await self.after_request(request)

    async def before_request(self, request: Request):
        return self.app

    async def after_request(self, request: Request):
        return None


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    async def before_request(self, request):
        await BgTasks.init_bg_tasks_obj()

    async def after_request(self, request):
        await BgTasks.execute_tasks()


def register_operation_record_middleware(app: FastAPI):
    """
    操作记录中间件
    用于将使用认证的操作全部记录到 数据库中
    :param app:
    :return:
    """

    @app.middleware("http")
    async def operation_record_middleware(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        telephone = request.scope.get('telephone', None)
        user_id = request.scope.get('user_id', None)
        user_name = request.scope.get('user_name', None)
        route = request.scope.get('route')
        process_time = time.time() - start_time
        user_agent = parse(request.headers.get("user-agent"))
        system = f"{user_agent.os.family} {user_agent.os.version_string}"
        browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
        query_params = dict(request.query_params.multi_items())
        path_params = request.path_params
        if isinstance(request.scope.get('body'), str):
            body = request.scope.get('body')
        else:
            body = request.scope.get('body').decode()
            if body:
                body = json.loads(body)
        params = {
            "body": body,
            "query_params": query_params if query_params else None,
            "path_params": path_params if path_params else None,
        }
        content_length = response.raw_headers[0][1]
        assert isinstance(route, APIRoute)
        document = {
            "process_time": process_time,
            "telephone": telephone,
            "user_id": user_id,
            "user_name": user_name,
            "request_api": request.url.__str__(),
            "client_ip": request.client.host,
            "system": system,
            "browser": browser,
            "request_method": request.method,
            "api_path": route.path,
            "summary": route.summary,
            "description": route.description,
            "tags": route.tags,
            "route_name": route.name,
            "status_code": response.status_code,
            "content_length": content_length,
            "create_datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "params": json.dumps(params)
        }
        # await OperationRecordDal(mongo_getter(request)).create_data(document)
        return response
