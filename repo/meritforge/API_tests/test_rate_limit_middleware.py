import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import UserRateLimitMiddleware


class _FakeRateRedis:
    def __init__(self):
        self.counters: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, _key: str, _seconds: int) -> bool:
        return True


class _FailingRateRedis:
    async def incr(self, _key: str) -> int:
        raise RuntimeError("redis unavailable")

    async def expire(self, _key: str, _seconds: int) -> bool:
        return True


class RateLimitMiddlewareApiTests(unittest.TestCase):
    def setUp(self):
        self.redis_patch = patch("app.core.rate_limit.redis_async.from_url", return_value=_FakeRateRedis())
        self.redis_patch.start()

        app = FastAPI()
        app.add_middleware(UserRateLimitMiddleware, redis_url="redis://ignored", limit_per_minute=2)

        @app.get("/rate-limit/ping")
        def ping() -> dict:
            return {"ok": True}

        self.client = TestClient(app)

    def tearDown(self):
        self.redis_patch.stop()

    def test_exceeds_limit_returns_429(self):
        self.assertEqual(self.client.get("/rate-limit/ping").status_code, 200)
        self.assertEqual(self.client.get("/rate-limit/ping").status_code, 200)
        third = self.client.get("/rate-limit/ping")
        self.assertEqual(third.status_code, 429)

    def test_redis_failure_fails_open(self):
        self.redis_patch.stop()
        self.redis_patch = patch("app.core.rate_limit.redis_async.from_url", return_value=_FailingRateRedis())
        self.redis_patch.start()

        app = FastAPI()
        app.add_middleware(UserRateLimitMiddleware, redis_url="redis://ignored", limit_per_minute=2)

        @app.get("/rate-limit/ping-fail-open")
        def ping() -> dict:
            return {"ok": True}

        client = TestClient(app)
        self.assertEqual(client.get("/rate-limit/ping-fail-open").status_code, 200)

    def test_uses_configured_default_limit_value(self):
        original_limit = settings.user_rate_limit_per_minute
        settings.user_rate_limit_per_minute = 3
        try:
            app = FastAPI()
            app.add_middleware(
                UserRateLimitMiddleware,
                redis_url="redis://ignored",
                limit_per_minute=settings.user_rate_limit_per_minute,
            )

            @app.get("/rate-limit/ping-config")
            def ping() -> dict:
                return {"ok": True}

            client = TestClient(app)
            self.assertEqual(client.get("/rate-limit/ping-config").status_code, 200)
            self.assertEqual(client.get("/rate-limit/ping-config").status_code, 200)
            self.assertEqual(client.get("/rate-limit/ping-config").status_code, 200)
            self.assertEqual(client.get("/rate-limit/ping-config").status_code, 429)
        finally:
            settings.user_rate_limit_per_minute = original_limit


if __name__ == "__main__":
    unittest.main()
