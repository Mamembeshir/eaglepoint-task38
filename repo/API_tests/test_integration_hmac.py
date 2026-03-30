import hashlib
import hmac
import json
import os
import time
import unittest
from datetime import datetime, timedelta, timezone

import httpx


API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")
KEY_ID = "integration-key-a"
KEY_SECRET = "integration-secret-a"


def _sign(secret: str, timestamp: str, payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    msg = f"{timestamp}.{body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


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


class IntegrationHmacApiTests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)

    def tearDown(self):
        self.client.close()

    def test_valid_signature_returns_success(self):
        payload = {"hello": "world", "number": 7}
        timestamp = datetime.now(timezone.utc).isoformat()
        signature = _sign(KEY_SECRET, timestamp, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": KEY_ID,
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": signature,
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_wrong_secret_returns_401(self):
        payload = {"action": "sync"}
        timestamp = datetime.now(timezone.utc).isoformat()
        bad_signature = _sign("wrong-secret", timestamp, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": KEY_ID,
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": bad_signature,
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_stale_timestamp_returns_401(self):
        payload = {"event": "old"}
        stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
        signature = _sign(KEY_SECRET, stale_ts, payload)

        response = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": KEY_ID,
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
        signature = _sign(KEY_SECRET, timestamp, payload)

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


if __name__ == "__main__":
    unittest.main()
