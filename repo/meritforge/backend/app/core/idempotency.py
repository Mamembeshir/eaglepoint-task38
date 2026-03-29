import base64
import hashlib
import json
import logging

from fastapi import Request
from redis import asyncio as redis_async
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.security import decode_token


logger = logging.getLogger("meritforge.middleware")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str, ttl_seconds: int = 86400):
        super().__init__(app)
        self.redis = redis_async.from_url(redis_url, decode_responses=True)
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _request_hash(request: Request, body: bytes) -> str:
        payload = hashlib.sha256()
        payload.update(request.method.encode("utf-8"))
        payload.update(request.url.path.encode("utf-8"))
        payload.update(request.url.query.encode("utf-8"))
        payload.update(body)
        return payload.hexdigest()

    @staticmethod
    def _user_identifier(request: Request) -> str:
        access_token = request.cookies.get(settings.access_cookie_name)
        if access_token:
            try:
                payload = decode_token(access_token)
                user_id = payload.get("sub")
                token_type = payload.get("type")
                if user_id and token_type == "access":
                    return str(user_id)
            except Exception:
                pass

        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    async def dispatch(self, request: Request, call_next):
        if request.method not in {"POST", "PUT"}:
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        user_identifier = self._user_identifier(request)
        key = f"idempotency:{user_identifier}:{idempotency_key}"

        try:
            cached = await self.redis.get(key)
        except Exception:
            logger.warning(
                "idempotency_redis_read_unavailable_fail_open",
                extra={"path": request.url.path, "user_identifier": user_identifier},
            )
            return await call_next(request)

        body = await request.body()
        body_sent = False

        async def receive():
            nonlocal body_sent
            if body_sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            body_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
        request_hash = self._request_hash(request, body)

        if cached:
            record = json.loads(cached)
            if record.get("request_hash") != request_hash:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "Idempotency key reuse with different payload"},
                )

            content = base64.b64decode(record.get("body_base64", ""))
            headers = record.get("headers", {})
            return Response(
                content=content,
                status_code=int(record.get("status_code", 200)),
                media_type=headers.get("content-type"),
                headers={k: v for k, v in headers.items() if k.lower() != "content-length"},
            )

        response = await call_next(request)
        body_chunks = [chunk async for chunk in response.body_iterator]
        response_body = b"".join(body_chunks)

        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        record = {
            "request_hash": request_hash,
            "status_code": response.status_code,
            "headers": headers,
            "body_base64": base64.b64encode(response_body).decode("utf-8"),
        }
        try:
            await self.redis.set(key, json.dumps(record), ex=self.ttl_seconds)
        except Exception:
            logger.warning(
                "idempotency_redis_write_unavailable_fail_open",
                extra={"path": request.url.path, "user_identifier": user_identifier},
            )

        return Response(
            content=response_body,
            status_code=response.status_code,
            media_type=response.media_type,
            headers=headers,
        )
