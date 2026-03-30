import os
import time
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import UserRateLimitMiddleware


API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")


def _wait_for_backend_ready(retries: int = 30, delay_seconds: float = 1.0):
    for _ in range(retries):
        try:
            response = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(delay_seconds)
    raise RuntimeError(f"Backend at {API_BASE_URL} is not ready")


class RateLimitMiddlewareApiTests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)

    def tearDown(self):
        self.client.close()

    def test_health_endpoint_is_reachable_under_rate_limit(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_repeated_requests_eventually_hit_rate_limit(self):
        last_status = 200
        for _ in range(200):
            response = self.client.get("/health")
            last_status = response.status_code
            if last_status == 429:
                break

        self.assertEqual(last_status, 429)


class _FailingAsyncRedis:
    async def incr(self, _key: str) -> int:
        raise RuntimeError("redis unavailable")

    async def expire(self, _key: str, _seconds: int) -> bool:
        raise RuntimeError("redis unavailable")


class RateLimitFailClosedTests(unittest.TestCase):
    def test_fail_closed_returns_429_when_redis_unavailable(self):
        original = settings.rate_limit_fail_closed
        settings.rate_limit_fail_closed = True
        try:
            with patch("app.core.rate_limit.redis_async.from_url", return_value=_FailingAsyncRedis()):
                app = FastAPI()
                app.add_middleware(UserRateLimitMiddleware, redis_url="redis://ignored")

                @app.get("/health")
                def health():
                    return {"status": "ok"}

                client = TestClient(app)
                response = client.get("/health")
                client.close()

            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.json().get("mode"), "fail_closed")
        finally:
            settings.rate_limit_fail_closed = original


if __name__ == "__main__":
    unittest.main()
