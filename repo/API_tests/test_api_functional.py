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


def _register(client: httpx.Client, email: str, password: str = "Password123") -> httpx.Response:
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def _login(client: httpx.Client, email: str, password: str = "Password123") -> httpx.Response:
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


class AuthE2ETests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)

    def tearDown(self):
        self.client.close()

    def test_register_login_and_profile_flow(self):
        email = _new_email("auth-flow")

        registered = _register(self.client, email)
        self.assertEqual(registered.status_code, 201)

        login = _login(self.client, email)
        self.assertEqual(login.status_code, 200)

        me = self.client.get("/api/v1/users/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], email)

    def test_register_conflict(self):
        email = _new_email("auth-conflict")
        self.assertEqual(_register(self.client, email).status_code, 201)
        conflict = _register(self.client, email)
        self.assertEqual(conflict.status_code, 409)

    def test_login_invalid_credentials(self):
        email = _new_email("auth-invalid")
        invalid = _login(self.client, email)
        self.assertEqual(invalid.status_code, 401)

    def test_refresh_requires_cookie_then_succeeds_after_login(self):
        email = _new_email("auth-refresh")

        missing = self.client.post("/api/v1/auth/refresh")
        self.assertEqual(missing.status_code, 401)

        self.assertEqual(_register(self.client, email).status_code, 201)
        self.assertEqual(_login(self.client, email).status_code, 200)

        refreshed = self.client.post("/api/v1/auth/refresh")
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.json()["user"]["email"], email)

    def test_logout_clears_auth_session(self):
        email = _new_email("auth-logout")
        self.assertEqual(_register(self.client, email).status_code, 201)
        self.assertEqual(_login(self.client, email).status_code, 200)

        before = self.client.get("/api/v1/users/me")
        self.assertEqual(before.status_code, 200)

        logout = self.client.post("/api/v1/auth/logout")
        self.assertEqual(logout.status_code, 200)

        after = self.client.get("/api/v1/users/me")
        self.assertEqual(after.status_code, 401)


class UserAndTopicE2ETests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        self.email = _new_email("user-topic")
        self.assertEqual(_register(self.client, self.email).status_code, 201)
        self.assertEqual(_login(self.client, self.email).status_code, 200)

    def tearDown(self):
        self.client.close()

    def test_me_requires_auth_when_not_logged_in(self):
        anonymous = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            response = anonymous.get("/api/v1/users/me")
            self.assertEqual(response.status_code, 401)
        finally:
            anonymous.close()

    def test_topic_subscription_create_list_delete(self):
        create = self.client.post("/api/v1/users/me/topic-subscriptions", json={"topic": "Portfolio"})
        self.assertEqual(create.status_code, 201)
        created_topic = create.json().get("topic")

        listed = self.client.get("/api/v1/users/me/topic-subscriptions")
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(any(item["topic"] == created_topic for item in listed.json()))

        delete = self.client.delete("/api/v1/users/me/topic-subscriptions", params={"topic": created_topic})
        self.assertEqual(delete.status_code, 204)


class EngagementAndBookmarkE2ETests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        self.email = _new_email("engage-bookmark")
        self.assertEqual(_register(self.client, self.email).status_code, 201)
        self.assertEqual(_login(self.client, self.email).status_code, 200)

    def tearDown(self):
        self.client.close()

    def test_content_catalog_requires_auth(self):
        anonymous = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            response = anonymous.get("/api/v1/content")
            self.assertEqual(response.status_code, 401)
        finally:
            anonymous.close()

    def test_telemetry_event_is_accepted(self):
        response = self.client.post(
            "/api/v1/telemetry/events",
            json={"event_type": "play", "event_data": {"progress_percentage": 500}},
        )
        self.assertEqual(response.status_code, 201)

    def test_bookmark_invalid_content_returns_404(self):
        response = self.client.post(
            "/api/v1/bookmarks",
            json={"content_id": str(uuid.uuid4()), "is_favorite": True},
        )
        self.assertEqual(response.status_code, 404)

    def test_bookmark_listing_is_available_for_authenticated_user(self):
        response = self.client.get("/api/v1/bookmarks")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)


class IdempotencyE2ETests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        self.email = _new_email("idempotency")
        self.assertEqual(_register(self.client, self.email).status_code, 201)
        self.assertEqual(_login(self.client, self.email).status_code, 200)

    def tearDown(self):
        self.client.close()

    def test_patch_replay_with_same_idempotency_key(self):
        key = f"idem-{uuid.uuid4()}"
        payload = {"display_name": f"idem-{uuid.uuid4().hex[:6]}"}

        first = self.client.patch("/api/v1/users/me", json=payload, headers={"Idempotency-Key": key})
        second = self.client.patch("/api/v1/users/me", json=payload, headers={"Idempotency-Key": key})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())

    def test_patch_conflict_when_payload_changes(self):
        key = f"idem-{uuid.uuid4()}"
        first = self.client.patch(
            "/api/v1/users/me",
            json={"display_name": f"first-{uuid.uuid4().hex[:6]}"},
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.patch(
            "/api/v1/users/me",
            json={"display_name": f"second-{uuid.uuid4().hex[:6]}"},
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(second.status_code, 409)


class IntegrationHmacE2ETests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)

    def tearDown(self):
        self.client.close()

    @staticmethod
    def _sign(secret: str, timestamp: str, payload: dict) -> str:
        import hashlib
        import hmac
        import json

        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        msg = f"{timestamp}.{body}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def test_hmac_valid_and_invalid_requests(self):
        from datetime import datetime, timezone

        payload = {"hello": "world"}
        timestamp = datetime.now(timezone.utc).isoformat()
        good_sig = self._sign("integration-secret-a", timestamp, payload)
        bad_sig = self._sign("wrong-secret", timestamp, payload)

        good = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": good_sig,
            },
        )
        self.assertEqual(good.status_code, 200)

        bad = self.client.post(
            "/api/v1/integration/echo",
            json=payload,
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": bad_sig,
            },
        )
        self.assertEqual(bad.status_code, 401)

    def test_published_content_hmac_endpoint_accepts_valid_and_rejects_bad_signature(self):
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).isoformat()
        good_sig = self._sign("integration-secret-a", timestamp, {})
        bad_sig = self._sign("wrong-secret", timestamp, {})

        good = self.client.get(
            "/api/v1/integration/published-content?limit=5&offset=0",
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": good_sig,
            },
        )
        self.assertEqual(good.status_code, 200)

        bad = self.client.get(
            "/api/v1/integration/published-content?limit=5&offset=0",
            headers={
                "X-MeritForge-Key-Id": "integration-key-a",
                "X-MeritForge-Timestamp": timestamp,
                "X-MeritForge-Signature": bad_sig,
            },
        )
        self.assertEqual(bad.status_code, 401)


class AccessControlAndRouteCoverageE2ETests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        self.email = _new_email("access")
        self.assertEqual(_register(self.client, self.email).status_code, 201)
        self.assertEqual(_login(self.client, self.email).status_code, 200)

    def tearDown(self):
        self.client.close()

    def test_student_blocked_from_admin_and_reviewer_routes(self):
        sample_id = str(uuid.uuid4())
        self.assertEqual(self.client.get("/api/v1/review-workflow/queue").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/audit-logs").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/operations/metrics", params={"start_date": "2026-01-01", "end_date": "2026-01-02"}).status_code, 403)
        self.assertEqual(self.client.get("/api/v1/operations/metrics/export.csv", params={"start_date": "2026-01-01", "end_date": "2026-01-02"}).status_code, 403)
        self.assertEqual(
            self.client.post(
                f"/api/v1/review-workflow/stages/{sample_id}/decisions",
                json={"decision": "approve", "comments": "not allowed"},
            ).status_code,
            403,
        )

    def test_student_blocked_from_employer_routes(self):
        sample_id = str(uuid.uuid4())
        self.assertIn(
            self.client.post("/api/v1/employer/job-posts", json={"title": "x", "employer_name": "y"}).status_code,
            {403, 422},
        )
        self.assertEqual(self.client.get("/api/v1/employer/job-posts").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/employer/job-posts/{sample_id}/applications").status_code, 403)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/employer/applications/{sample_id}/status",
                json={"status": "under_review", "notes": "n/a"},
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get(f"/api/v1/employer/job-posts/{sample_id}/milestones").status_code, 403)

    def test_student_blocked_from_publishing_management_routes(self):
        sample_id = str(uuid.uuid4())
        self.assertEqual(
            self.client.post(
                f"/api/v1/publishing/content/{sample_id}/schedule",
                json={"scheduled_publish_at": "2030-01-01T00:00:00Z"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/publishing/content/{sample_id}/takedown",
                json={"reason": "not allowed"},
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get(f"/api/v1/publishing/content/{sample_id}/history").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/publishing/content/{sample_id}/visibility/{sample_id}").status_code, 403)

    def test_student_routes_return_expected_not_found_for_missing_entities(self):
        sample_id = str(uuid.uuid4())
        self.assertEqual(self.client.post(f"/api/v1/student/job-posts/{sample_id}/applications", json={"cover_letter": "ready"}).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/student/applications").status_code, 200)
        self.assertEqual(
            self.client.post(
                "/api/v1/annotations",
                json={
                    "content_id": sample_id,
                    "start_offset": 0,
                    "end_offset": 4,
                    "highlighted_text": "test",
                    "annotation_text": "note",
                },
            ).status_code,
            404,
        )

    def test_student_import_export_and_deletion_mark_flow(self):
        exported = self.client.get("/api/v1/users/me/export")
        self.assertEqual(exported.status_code, 200)

        imported = self.client.post(
            "/api/v1/users/me/import",
            json={
                "source": "e2e-test",
                "user": {
                    "display_name": f"imported-{uuid.uuid4().hex[:6]}",
                    "bio": "updated from import",
                },
            },
        )
        self.assertEqual(imported.status_code, 200)

        without_step_up = self.client.post(
            "/api/v1/users/me/deletion/mark",
            json={"reason": "e2e cleanup test"},
        )
        self.assertEqual(without_step_up.status_code, 403)

        step_up = self.client.post("/api/v1/auth/step-up", json={"password": "Password123"})
        self.assertEqual(step_up.status_code, 200)

        marked = self.client.post(
            "/api/v1/users/me/deletion/mark",
            json={"reason": "e2e cleanup test"},
        )
        self.assertEqual(marked.status_code, 200)

    def test_student_blocked_from_admin_risk_dictionary_and_cohort_listing(self):
        self.assertEqual(self.client.get("/api/v1/admin/risk-dictionary").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/admin/risk-dictionary",
                json={"term": f"term-{uuid.uuid4().hex[:6]}", "category": "policy", "severity": "low"},
            ).status_code,
            403,
        )
        self.assertEqual(self.client.patch(f"/api/v1/admin/risk-dictionary/{uuid.uuid4()}", json={"severity": "medium"}).status_code, 403)
        self.assertEqual(self.client.delete(f"/api/v1/admin/risk-dictionary/{uuid.uuid4()}").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/admin/cohorts").status_code, 403)

    def test_student_blocked_from_webhook_admin_routes(self):
        self.assertEqual(self.client.get("/api/v1/webhooks/configs").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/webhooks/configs",
                json={
                    "name": "e2e-webhook",
                    "url": "http://internal.service.local/webhook",
                    "events": ["content.published"],
                },
            ).status_code,
            403,
        )
        self.assertEqual(self.client.post("/api/v1/webhooks/dispatch", json={"event_name": "content.published", "payload": {}}).status_code, 403)
        self.assertEqual(self.client.get("/api/v1/webhooks/deliveries").status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/webhooks/deliveries/{uuid.uuid4()}/retry").status_code, 403)

    def test_student_blocked_from_admin_legal_hold_endpoints(self):
        user_id = str(uuid.uuid4())
        self.assertEqual(self.client.get(f"/api/v1/admin/users/{user_id}/legal-hold").status_code, 403)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/users/{user_id}/legal-hold",
                json={"legal_hold": True, "reason": "e2e"},
            ).status_code,
            403,
        )

    def test_student_engagement_milestone_and_annotation_routes(self):
        other_user_id = str(uuid.uuid4())
        self.assertEqual(self.client.post("/api/v1/milestone-templates", json={"key": f"k-{uuid.uuid4().hex[:6]}", "name": "Template"}).status_code, 403)
        self.assertEqual(
            self.client.post(
                f"/api/v1/students/{self._extract_my_id()}/milestones/manual",
                json={
                    "milestone_name": "Self milestone",
                    "milestone_type": "custom",
                    "milestone_template_id": str(uuid.uuid4()),
                },
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get(f"/api/v1/students/{other_user_id}/milestones").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/contents/{uuid.uuid4()}/annotations").status_code, 200)
        self.assertEqual(
            self.client.patch(
                f"/api/v1/annotations/{uuid.uuid4()}",
                json={"annotation_text": "update", "client_updated_at": "2030-01-01T00:00:00Z"},
            ).status_code,
            404,
        )

    def test_student_telemetry_progress_endpoint(self):
        create = self.client.post(
            "/api/v1/telemetry/events",
            json={"event_type": "play", "event_data": {"position_seconds": 12}},
        )
        self.assertEqual(create.status_code, 201)
        progress = self.client.get("/api/v1/telemetry/progress")
        self.assertEqual(progress.status_code, 200)
        self.assertIsInstance(progress.json(), list)

    def _extract_my_id(self) -> str:
        me = self.client.get("/api/v1/users/me")
        self.assertEqual(me.status_code, 200)
        return me.json()["id"]


def tearDownModule():
    # Cleanup hook: direct DB access is allowed here only.
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
