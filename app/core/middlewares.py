import re
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.dependency import AuthControl
from app.models.admin import AuditLog, User
from app.utils.audit_log import (
    should_skip_request_body,
    should_skip_response_body,
    truncate_body_text,
)

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


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, methods: list, exclude_paths: list):
        super().__init__(app)
        self.methods = methods
        self.exclude_paths = exclude_paths

    @staticmethod
    def _wrap_request_with_body(request: Request, body: bytes) -> Request:
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        return Request(request.scope, receive)

    @staticmethod
    async def _read_request_body(request: Request) -> tuple[Request, str]:
        if should_skip_request_body(request):
            return request, ""

        body_bytes = await request.body()
        request = HttpAuditLogMiddleware._wrap_request_with_body(request, body_bytes)
        if not body_bytes:
            return request, ""
        try:
            return request, body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return request, ""

    @staticmethod
    async def _read_response_body(response: Response) -> tuple[Response, str]:
        body_chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            body_chunks.append(chunk)
        body_bytes = b"".join(body_chunks)
        new_response = Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        if not body_bytes:
            return new_response, ""
        try:
            return new_response, body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return new_response, ""

    async def get_request_log(
        self, request: Request, response: Response, request_body: str, response_body: str
    ) -> dict:
        """
        根据request和response对象获取对应的日志记录数据
        """
        data: dict = {
            "path": request.url.path,
            "status": response.status_code,
            "method": request.method,
            "request_body": truncate_body_text(request_body),
            "response_body": truncate_body_text(response_body),
        }

        # 路由信息
        app: FastAPI = request.app
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and route.path_regex.match(request.url.path)
                and request.method in route.methods
            ):
                data["module"] = ",".join(route.tags)
                data["summary"] = route.summary
        # 获取用户信息
        try:
            token = request.headers.get("token")
            user_obj = None
            if token:
                user_obj: User = await AuthControl.is_authed(token)
            data["user_id"] = user_obj.id if user_obj else 0
            data["username"] = user_obj.username if user_obj else ""
        except Exception:
            data["user_id"] = 0
            data["username"] = ""
        return data

    async def before_request(self, request: Request):
        pass

    async def after_request(
        self,
        request: Request,
        response: Response,
        process_time: int,
        request_body: str,
        response_body: str,
    ):
        if request.method in self.methods:
            for path in self.exclude_paths:
                if re.search(path, request.url.path, re.I) is not None:
                    return
            data: dict = await self.get_request_log(
                request=request,
                response=response,
                request_body=request_body,
                response_body=response_body,
            )
            data["response_time"] = process_time
            await AuditLog.create(**data)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time: datetime = datetime.now()
        await self.before_request(request)

        request, request_body = await self._read_request_body(request)
        response = await call_next(request)

        if should_skip_response_body(request, response):
            response_body = ""
        else:
            response, response_body = await self._read_response_body(response)

        end_time: datetime = datetime.now()
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)
        await self.after_request(request, response, process_time, request_body, response_body)
        return response
