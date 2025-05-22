import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.controllers.auditlog import AuditLogController
from app.core.ctx import get_current_user


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip audit logging for some paths
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)

        # Calculate response time
        response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds

        try:
            # Get current user from context
            current_user = await get_current_user()
            user_id = current_user.id if current_user else 0
            username = current_user.username if current_user else ""

            # Get module name from path
            path = request.url.path
            module = path.split("/")[2] if len(path.split("/")) > 2 else ""

            # Create audit log
            controller = AuditLogController()
            await controller.create_log(
                user_id=user_id,
                username=username,
                module=module,
                summary=request.url.path,
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                response_time=response_time,
            )
        except Exception as e:
            # Log the error but don't interrupt the response
            print(f"Error creating audit log: {str(e)}")

        return response
