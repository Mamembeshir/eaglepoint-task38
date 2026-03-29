from datetime import datetime, timezone
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from redis import asyncio as redis_async

from app.core.config import settings
from app.core.security import decode_token


logger = logging.getLogger("meritforge.middleware")


class UserRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_url: str, limit_per_minute: int = 120):
        super().__init__(app)
        self.redis = redis_async.from_url(redis_url, decode_responses=True)
        self.limit_per_minute = limit_per_minute

    async def dispatch(self, request: Request, call_next):
        identifier = request.client.host if request.client else "unknown"
        access_token = request.cookies.get(settings.access_cookie_name)
        if access_token:
            try:
                payload = decode_token(access_token)
                user_id = payload.get("sub")
                token_type = payload.get("type")
                if user_id and token_type == "access":
                    identifier = f"user:{user_id}"
            except Exception:
                pass

        minute_key = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        key = f"rate_limit:{identifier}:{minute_key}"
        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, 60)
            if current > self.limit_per_minute:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "limit": self.limit_per_minute,
                        "window": "1 minute",
                    },
                )
        except Exception:
            logger.warning(
                "rate_limit_redis_unavailable_fail_open",
                extra={"path": request.url.path, "identifier": identifier},
            )

        return await call_next(request)
