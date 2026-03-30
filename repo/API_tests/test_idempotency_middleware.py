import os
import time
import unittest
import uuid
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.idempotency import IdempotencyMiddleware


API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")
TEST_RUN_TAG = uuid.uuid4().hex[:10]


def _wait_for_backend_ready(retries: int = 60, delay_seconds: float = 1.0):
    for _ in range(retries):
        try:
            response = httpx.get(f"{API_BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(delay_seconds)
    raise RuntimeError(f"Backend at {API_BASE_URL} is not ready")


def _register_and_login(client: httpx.Client, password: str = "Password123") -> str:
    email = f"idem.{TEST_RUN_TAG}.{uuid.uuid4().hex[:8]}@example.com"
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Idem Tester"},
    )
    if register.status_code not in {200, 201, 409}:
        raise RuntimeError(f"Register failed: {register.status_code} {register.text}")
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if login.status_code != 200:
        raise RuntimeError(f"Login failed: {login.status_code} {login.text}")
    return email


class IdempotencyMiddlewareApiTests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)

    def tearDown(self):
        self.client.close()

    def test_patch_same_key_same_body_returns_same_response(self):
        _register_and_login(self.client)
        key = f"idem-{uuid.uuid4()}"
        payload = {"display_name": f"idem-name-{uuid.uuid4().hex[:6]}"}

        first = self.client.patch("/api/v1/users/me", json=payload, headers={"Idempotency-Key": key})
        second = self.client.patch("/api/v1/users/me", json=payload, headers={"Idempotency-Key": key})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())

    def test_patch_same_key_different_body_returns_409(self):
        _register_and_login(self.client)
        key = f"idem-{uuid.uuid4()}"

        first = self.client.patch(
            "/api/v1/users/me",
            json={"display_name": f"idem-a-{uuid.uuid4().hex[:6]}"},
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.patch(
            "/api/v1/users/me",
            json={"display_name": f"idem-b-{uuid.uuid4().hex[:6]}"},
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(second.status_code, 409)

    def test_auth_login_with_idempotency_key_never_500(self):
        email = f"idem.login.{TEST_RUN_TAG}.{uuid.uuid4().hex[:8]}@example.com"
        self.client.post("/api/v1/auth/register", json={"email": email, "password": "Password123", "display_name": "Login Tester"})
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123"},
            headers={"Idempotency-Key": f"idem-{uuid.uuid4()}"},
        )
        self.assertIn(response.status_code, {200, 401})
        self.assertNotEqual(response.status_code, 500)


class _FailingAsyncRedis:
    async def get(self, _key: str):
        raise RuntimeError("redis unavailable")

    async def set(self, _key: str, _value: str, ex: int | None = None):
        raise RuntimeError("redis unavailable")


class IdempotencyFailClosedTests(unittest.TestCase):
    def test_fail_closed_returns_503_when_redis_read_unavailable(self):
        original = settings.idempotency_fail_closed
        settings.idempotency_fail_closed = True
        try:
            with patch("app.core.idempotency.redis_async.from_url", return_value=_FailingAsyncRedis()):
                app = FastAPI()
                app.add_middleware(IdempotencyMiddleware, redis_url="redis://ignored")

                @app.post("/echo")
                def echo(payload: dict):
                    return payload

                client = TestClient(app)
                response = client.post("/echo", json={"value": 1}, headers={"Idempotency-Key": "test-key"})
                client.close()

            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json().get("mode"), "fail_closed")
        finally:
            settings.idempotency_fail_closed = original


if __name__ == "__main__":
    unittest.main()
