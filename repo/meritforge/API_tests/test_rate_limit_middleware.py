import os
import time
import unittest

import httpx


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


if __name__ == "__main__":
    unittest.main()
