import os
import time
import unittest
import uuid

import httpx
from sqlalchemy import text

from app.core.database import SessionLocal


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


def _new_email(prefix: str) -> str:
    return f"{prefix}.{TEST_RUN_TAG}.{uuid.uuid4().hex[:8]}@example.com"


def _register_and_login(email: str, password: str = "Password123") -> httpx.Client:
    client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
    registered = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    if registered.status_code not in {201, 409}:
        raise RuntimeError(f"Registration failed: {registered.status_code} {registered.text}")
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if login.status_code != 200:
        raise RuntimeError(f"Login failed: {login.status_code} {login.text}")
    return client


class DbBackedWorkflowIntegrationTests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()

    def test_student_end_to_end_profile_and_topics_flow(self):
        email = _new_email("flow-student")
        client = _register_and_login(email)
        try:
            me = client.get("/api/v1/users/me")
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["email"], email)

            update = client.patch("/api/v1/users/me", json={"display_name": f"student-{uuid.uuid4().hex[:6]}"})
            self.assertEqual(update.status_code, 200)

            sub = client.post("/api/v1/users/me/topic-subscriptions", json={"topic": "interview-skills"})
            self.assertEqual(sub.status_code, 201)

            listed = client.get("/api/v1/users/me/topic-subscriptions")
            self.assertEqual(listed.status_code, 200)
            self.assertTrue(any(item["topic"] == "interview-skills" for item in listed.json()))
        finally:
            client.close()

    def test_auth_and_protected_access_flow(self):
        email = _new_email("flow-protected")
        anon = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            unauthorized = anon.get("/api/v1/users/me")
            self.assertEqual(unauthorized.status_code, 401)
        finally:
            anon.close()

        client = _register_and_login(email)
        try:
            authorized = client.get("/api/v1/users/me")
            self.assertEqual(authorized.status_code, 200)
            self.assertEqual(authorized.json()["email"], email)
        finally:
            client.close()


def tearDownModule():
    # Cleanup hook: direct DB access allowed only here.
    db = SessionLocal()
    try:
        pattern = f"%.{TEST_RUN_TAG}.%@example.com"
        db.execute(text("DELETE FROM refresh_tokens WHERE user_id IN (SELECT id FROM users WHERE email LIKE :pattern)"), {"pattern": pattern})
        db.execute(text("DELETE FROM user_topic_subscriptions WHERE user_id IN (SELECT id FROM users WHERE email LIKE :pattern)"), {"pattern": pattern})
        db.execute(text("DELETE FROM bookmarks WHERE user_id IN (SELECT id FROM users WHERE email LIKE :pattern)"), {"pattern": pattern})
        db.execute(text("DELETE FROM users WHERE email LIKE :pattern"), {"pattern": pattern})
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    unittest.main()
