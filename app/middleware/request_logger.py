import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        clear_contextvars()

        request_id = str(uuid.uuid4())

        client_ip = request.client.host if request.client else None

        if not client_ip:
            client_ip = request.headers.get("x-forwarded-for")

        bind_contextvars(
            request_id=request_id, method=request.method, path=request.url.path, ip=client_ip
        )

        start_time = time.time()

        logger.info("request_start")

        response = await call_next(request)

        duration = round((time.time() - start_time) * 1000)

        logger.info(
            "request_complete",
            status_code=response.status_code,
            duration_ms=duration,
        )

        return response
