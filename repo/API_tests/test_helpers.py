from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.core.config import settings
from app.core.idempotency import IdempotencyMiddleware
from app.core.rate_limit import UserRateLimitMiddleware


def create_test_app(include_middleware: bool = False) -> FastAPI:
    app = FastAPI()
    if include_middleware:
        app.add_middleware(
            UserRateLimitMiddleware,
            redis_url=settings.redis_url,
            limit_per_minute=settings.user_rate_limit_per_minute,
        )
        app.add_middleware(
            IdempotencyMiddleware,
            redis_url=settings.redis_url,
        )
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(api_router)
    return app


def create_test_client(include_middleware: bool = False) -> TestClient:
    return TestClient(create_test_app(include_middleware=include_middleware))
