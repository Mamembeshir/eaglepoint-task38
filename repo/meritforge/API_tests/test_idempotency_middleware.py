import unittest
import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.idempotency import IdempotencyMiddleware


class _FakeAsyncRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value
        return True


class _FailingAsyncRedis:
    async def get(self, _key: str):
        raise RuntimeError("redis unavailable")

    async def set(self, _key: str, _value: str, ex: int | None = None):
        raise RuntimeError("redis unavailable")


class IdempotencyMiddlewareApiTests(unittest.TestCase):
    def setUp(self):
        self.redis_patch = patch("app.core.idempotency.redis_async.from_url", return_value=_FakeAsyncRedis())
        self.redis_patch.start()
        app = FastAPI()
        app.add_middleware(IdempotencyMiddleware, redis_url="redis://ignored")

        @app.post("/idempotency/echo")
        def echo(payload: dict) -> dict:
            return {"ok": True, "echo": payload}

        self.client = TestClient(app)

    def tearDown(self):
        self.redis_patch.stop()

    def test_same_key_same_body_returns_same_response(self):
        key = f"idem-{uuid.uuid4()}"
        payload = {"value": 1}

        first = self.client.post("/idempotency/echo", json=payload, headers={"Idempotency-Key": key})
        second = self.client.post("/idempotency/echo", json=payload, headers={"Idempotency-Key": key})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, first.status_code)
        self.assertEqual(second.json(), first.json())

    def test_same_key_different_body_returns_409(self):
        key = f"idem-{uuid.uuid4()}"
        self.client.post("/idempotency/echo", json={"value": 1}, headers={"Idempotency-Key": key})
        second = self.client.post("/idempotency/echo", json={"value": 2}, headers={"Idempotency-Key": key})

        self.assertEqual(second.status_code, 409)

    def test_redis_failure_fails_open(self):
        self.redis_patch.stop()
        self.redis_patch = patch("app.core.idempotency.redis_async.from_url", return_value=_FailingAsyncRedis())
        self.redis_patch.start()

        app = FastAPI()
        app.add_middleware(IdempotencyMiddleware, redis_url="redis://ignored")

        @app.post("/idempotency/echo-fail-open")
        def echo(payload: dict) -> dict:
            return {"ok": True, "echo": payload}

        client = TestClient(app)
        response = client.post(
            "/idempotency/echo-fail-open",
            json={"value": 1},
            headers={"Idempotency-Key": f"idem-{uuid.uuid4()}"},
        )

        self.assertEqual(response.status_code, 200)

    def test_redis_failure_fails_closed_when_enabled(self):
        self.redis_patch.stop()
        self.redis_patch = patch("app.core.idempotency.redis_async.from_url", return_value=_FailingAsyncRedis())
        self.redis_patch.start()

        original = settings.idempotency_fail_closed
        settings.idempotency_fail_closed = True
        try:
            app = FastAPI()
            app.add_middleware(IdempotencyMiddleware, redis_url="redis://ignored")

            @app.post("/idempotency/echo-fail-closed")
            def echo(payload: dict) -> dict:
                return {"ok": True, "echo": payload}

            client = TestClient(app)
            response = client.post(
                "/idempotency/echo-fail-closed",
                json={"value": 1},
                headers={"Idempotency-Key": f"idem-{uuid.uuid4()}"},
            )

            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json().get("mode"), "fail_closed")
        finally:
            settings.idempotency_fail_closed = original


if __name__ == "__main__":
    unittest.main()
