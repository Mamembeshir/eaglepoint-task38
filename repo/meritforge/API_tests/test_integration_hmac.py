import hashlib
import hmac
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.config import settings
from test_helpers import create_test_client


def _sign(secret: str, timestamp: str, payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    msg = f"{timestamp}.{body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


class IntegrationHmacApiTests(unittest.TestCase):
    def setUp(self):
        self.original_keys = dict(settings.integration_hmac_keys)
        self.original_rate_limit = settings.user_rate_limit_per_minute
        settings.integration_hmac_keys = {
            "integration-key-a": "integration-secret-a",
            "integration-key-b": "integration-secret-b",
        }
        settings.user_rate_limit_per_minute = 500

        class _FakeAsyncRedis:
            def __init__(self):
                self.store: dict[str, str] = {}
                self.counters: dict[str, int] = {}

            async def get(self, key: str):
                return self.store.get(key)

            async def set(self, key: str, value: str, ex: int | None = None, nx: bool | None = None):
                if nx and key in self.store:
                    return False
                self.store[key] = value
                return True

            async def incr(self, key: str) -> int:
                self.counters[key] = self.counters.get(key, 0) + 1
                return self.counters[key]

            async def expire(self, key: str, seconds: int) -> bool:
                return True

        self._redis_instance = _FakeAsyncRedis()
        self.idem_patch = patch("app.core.idempotency.redis_async.from_url", return_value=self._redis_instance)
        self.rate_patch = patch("app.core.rate_limit.redis_async.from_url", return_value=self._redis_instance)
        self.idem_patch.start()
        self.rate_patch.start()
        self.client = create_test_client(include_middleware=True)

    def tearDown(self):
        self.client.close()
        self.idem_patch.stop()
        self.rate_patch.stop()
        settings.integration_hmac_keys = self.original_keys
        settings.user_rate_limit_per_minute = self.original_rate_limit

    def test_valid_signature_returns_success(self):
        payload = {"hello": "world", "number": 7}
        timestamp = datetime.now(timezone.utc).isoformat()
        signature = _sign("integration-secret-a", timestamp, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": signature,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["echo"], payload)

    def test_wrong_secret_returns_401(self):
        payload = {"action": "sync"}
        timestamp = datetime.now(timezone.utc).isoformat()
        bad_signature = _sign("wrong-secret", timestamp, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": bad_signature,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_stale_timestamp_returns_401(self):
        payload = {"event": "old"}
        stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        signature = _sign("integration-secret-a", stale_ts, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": stale_ts,
                "X-MeritForge-Signature": signature,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_headers_returns_401(self):
        response = self.client.post("/api/v1/integration/echo", json={"hello": "world"})
        self.assertEqual(response.status_code, 401)

    def test_wrong_key_id_returns_401(self):
        payload = {"hello": "world"}
        timestamp = datetime.now(timezone.utc).isoformat()
        signature = _sign("integration-secret-a", timestamp, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": "nonexistent-key",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": signature,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_valid_signature_with_middleware_stack_returns_200(self):
        payload = {"source": "middleware-stack"}
        timestamp = datetime.now(timezone.utc).isoformat()
        signature = _sign("integration-secret-a", timestamp, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": signature,
            },
        )

        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
