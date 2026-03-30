import os
import time
import unittest
import uuid

import httpx
from sqlalchemy import text

from app.core.database import SessionLocal


API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")
TEST_RUN_TAG = uuid.uuid4().hex[:12]


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


def _new_email(prefix: str) -> str:
    return f"{prefix}.{TEST_RUN_TAG}.{uuid.uuid4().hex[:8]}@example.com"


def _register(client: httpx.Client, email: str, password: str = "Password123", display_name: str = "E2E User"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    if response.status_code not in {200, 201, 409}:
        raise AssertionError(f"Register failed for {email}: {response.status_code} {response.text}")


def _login(client: httpx.Client, email: str, password: str = "Password123"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        raise AssertionError(f"Login failed for {email}: {response.status_code} {response.text}")


def _login_seeded(client: httpx.Client, email: str, password: str = os.getenv("SEED_DEV_PASSWORD", "MeritForgeDev!2026")):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        raise AssertionError(f"Seeded login failed for {email}: {response.status_code} {response.text}")


class E2EAuthFlowsTests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)

    def tearDown(self):
        self.client.close()

    def test_register_login_and_me_profile(self):
        email = _new_email("auth-flow")
        _register(self.client, email, display_name="Auth Flow")
        _login(self.client, email)

        me = self.client.get("/api/v1/users/me")
        self.assertEqual(me.status_code, 200)
        body = me.json()
        self.assertEqual(body["email"], email)
        self.assertEqual(body["display_name"], "Auth Flow")

    def test_step_up_requires_valid_password(self):
        email = _new_email("step-up")
        _register(self.client, email)
        _login(self.client, email)

        bad = self.client.post("/api/v1/auth/step-up", json={"password": "WrongPass123"})
        self.assertEqual(bad.status_code, 403)

        good = self.client.post("/api/v1/auth/step-up", json={"password": "Password123"})
        self.assertEqual(good.status_code, 200)

    def test_refresh_and_logout_flow(self):
        email = _new_email("refresh-logout")
        _register(self.client, email)
        _login(self.client, email)

        refreshed = self.client.post("/api/v1/auth/refresh")
        self.assertEqual(refreshed.status_code, 200)

        logout = self.client.post("/api/v1/auth/logout")
        self.assertEqual(logout.status_code, 200)

        me_after = self.client.get("/api/v1/users/me")
        self.assertEqual(me_after.status_code, 401)


class E2EStudentWorkspaceFlowsTests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()
        self.client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        self.email = _new_email("student-flow")
        _register(self.client, self.email, display_name="Student Flow")
        _login(self.client, self.email)

    def tearDown(self):
        self.client.close()

    def test_topic_subscription_lifecycle(self):
        create = self.client.post("/api/v1/users/me/topic-subscriptions", json={"topic": f"portfolio-{TEST_RUN_TAG}"})
        self.assertEqual(create.status_code, 201)

        listing = self.client.get("/api/v1/users/me/topic-subscriptions")
        self.assertEqual(listing.status_code, 200)
        self.assertTrue(any(item["topic"] == f"portfolio-{TEST_RUN_TAG}" for item in listing.json()))

        delete = self.client.delete("/api/v1/users/me/topic-subscriptions", params={"topic": f"portfolio-{TEST_RUN_TAG}"})
        self.assertEqual(delete.status_code, 204)

        listing_after = self.client.get("/api/v1/users/me/topic-subscriptions")
        self.assertEqual(listing_after.status_code, 200)
        self.assertFalse(any(item["topic"] == f"portfolio-{TEST_RUN_TAG}" for item in listing_after.json()))

    def test_idempotent_profile_patch(self):
        key = f"idem-{uuid.uuid4()}"
        payload = {"display_name": f"E2E-{TEST_RUN_TAG}"}

        first = self.client.patch("/api/v1/users/me", json=payload, headers={"Idempotency-Key": key})
        self.assertEqual(first.status_code, 200)
        second = self.client.patch("/api/v1/users/me", json=payload, headers={"Idempotency-Key": key})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())

        conflict = self.client.patch(
            "/api/v1/users/me",
            json={"display_name": f"DIFF-{TEST_RUN_TAG}"},
            headers={"Idempotency-Key": key},
        )
        self.assertEqual(conflict.status_code, 409)

    def test_student_cannot_submit_author_content(self):
        submission = self.client.post(
            "/api/v1/content/submissions",
            json={
                "content_type": "article",
                "title": f"Forbidden Student Submission {TEST_RUN_TAG}",
                "body": "Students should not have author privileges.",
            },
        )
        self.assertEqual(submission.status_code, 403)


class E2ESeededRoleFlowsTests(unittest.TestCase):
    def setUp(self):
        _wait_for_backend_ready()

    def test_admin_risk_dictionary_crud_and_cohort_listing(self):
        client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            _login_seeded(client, "admin.meritforge@gmail.com")

            term = f"risk-{TEST_RUN_TAG}-{uuid.uuid4().hex[:6]}"
            created = client.post(
                "/api/v1/admin/risk-dictionary",
                json={"term": term, "category": "policy", "severity": "low", "description": "e2e risk term"},
            )
            self.assertEqual(created.status_code, 201)
            risk_id = created.json()["id"]

            listed = client.get("/api/v1/admin/risk-dictionary")
            self.assertEqual(listed.status_code, 200)
            self.assertTrue(any(item["id"] == risk_id for item in listed.json()))

            updated = client.patch(
                f"/api/v1/admin/risk-dictionary/{risk_id}",
                json={"severity": "medium", "replacement_suggestion": "safer alternative"},
            )
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.json()["severity"], "medium")

            cohorts = client.get("/api/v1/admin/cohorts")
            self.assertEqual(cohorts.status_code, 200)
            self.assertIsInstance(cohorts.json(), list)

            deleted = client.delete(f"/api/v1/admin/risk-dictionary/{risk_id}")
            self.assertEqual(deleted.status_code, 204)
        finally:
            client.close()

    def test_admin_webhook_config_and_delivery_listing(self):
        client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            _login_seeded(client, "admin.meritforge@gmail.com")

            created = client.post(
                "/api/v1/webhooks/configs",
                json={
                    "name": f"Webhook {TEST_RUN_TAG}",
                    "url": "http://internal.service.local/webhook",
                    "events": ["content.published"],
                },
            )
            self.assertEqual(created.status_code, 201)

            configs = client.get("/api/v1/webhooks/configs")
            self.assertEqual(configs.status_code, 200)
            self.assertTrue(any(item["name"] == f"Webhook {TEST_RUN_TAG}" for item in configs.json()))

            deliveries = client.get("/api/v1/webhooks/deliveries")
            self.assertEqual(deliveries.status_code, 200)
            self.assertIsInstance(deliveries.json(), list)
        finally:
            client.close()

    def test_student_profile_import_export_and_deletion_mark(self):
        client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            _login_seeded(client, "student.meritforge@gmail.com")

            exported = client.get("/api/v1/users/me/export")
            self.assertEqual(exported.status_code, 200)

            imported = client.post(
                "/api/v1/users/me/import",
                json={
                    "source": "e2e-blackbox",
                    "user": {"display_name": f"Imported {TEST_RUN_TAG}", "bio": "imported via api"},
                },
            )
            self.assertEqual(imported.status_code, 200)

            denied = client.post("/api/v1/users/me/deletion/mark", json={"reason": "e2e"})
            self.assertEqual(denied.status_code, 403)

            step_up = client.post("/api/v1/auth/step-up", json={"password": os.getenv("SEED_DEV_PASSWORD", "MeritForgeDev!2026")})
            self.assertEqual(step_up.status_code, 200)

            marked = client.post("/api/v1/users/me/deletion/mark", json={"reason": "e2e"})
            self.assertEqual(marked.status_code, 200)
        finally:
            client.close()

    def test_author_submission_mine_and_revision_flow(self):
        author_client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        reviewer_client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            _login_seeded(author_client, "author.meritforge@gmail.com")
            _login_seeded(reviewer_client, "reviewer.meritforge@gmail.com")
            title = f"Author Submission {TEST_RUN_TAG}"

            created = author_client.post(
                "/api/v1/content/submissions",
                json={
                    "content_type": "article",
                    "title": title,
                    "body": "This is a seeded author submission body for end-to-end coverage.",
                },
            )
            self.assertEqual(created.status_code, 201)
            content_id = created.json()["content_id"]

            mine = author_client.get("/api/v1/content/submissions/mine")
            self.assertEqual(mine.status_code, 200)
            self.assertTrue(any(item["content_id"] == content_id for item in mine.json()))

            queue = reviewer_client.get("/api/v1/review-workflow/queue")
            self.assertEqual(queue.status_code, 200)
            stage = next(item for item in queue.json() if item["content_id"] == content_id)

            returned = reviewer_client.post(
                f"/api/v1/review-workflow/stages/{stage['stage_id']}/decisions",
                json={
                    "decision": "return_for_revision",
                    "comments": "Please revise this draft with more detail and clearer structure.",
                },
            )
            self.assertEqual(returned.status_code, 200)

            revised = author_client.post(
                f"/api/v1/content/{content_id}/revisions",
                json={
                    "title": f"{title} Revised",
                    "body": "Updated body for revision coverage path.",
                    "change_summary": "e2e revision",
                },
            )
            self.assertEqual(revised.status_code, 201)
        finally:
            author_client.close()
            reviewer_client.close()

    def test_reviewer_short_return_for_revision_validation(self):
        author_client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        reviewer_client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            _login_seeded(author_client, "author.meritforge@gmail.com")
            _login_seeded(reviewer_client, "reviewer.meritforge@gmail.com")

            created = author_client.post(
                "/api/v1/content/submissions",
                json={
                    "content_type": "article",
                    "title": f"Reviewer Validation {TEST_RUN_TAG}",
                    "body": "This article gives enough text for a reviewer validation scenario.",
                },
            )
            self.assertEqual(created.status_code, 201)
            content_id = created.json()["content_id"]

            queue = reviewer_client.get("/api/v1/review-workflow/queue")
            self.assertEqual(queue.status_code, 200)
            stage = next(item for item in queue.json() if item["content_id"] == content_id)

            response = reviewer_client.post(
                f"/api/v1/review-workflow/stages/{stage['stage_id']}/decisions",
                json={"decision": "return_for_revision", "comments": "too short"},
            )
            self.assertEqual(response.status_code, 422)
        finally:
            author_client.close()
            reviewer_client.close()

    def test_employer_job_creation_and_cross_user_isolation(self):
        owner_client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        other_client = httpx.Client(base_url=API_BASE_URL, follow_redirects=True)
        try:
            _login_seeded(owner_client, "employer.meritforge@gmail.com")
            _login_seeded(other_client, "employer2.meritforge@gmail.com")

            created = owner_client.post(
                "/api/v1/employer/job-posts",
                json={
                    "title": f"Employer Job {TEST_RUN_TAG}",
                    "employer_name": "MeritForge Employer",
                },
            )
            self.assertEqual(created.status_code, 201)
            job_post_id = created.json()["id"]

            forbidden = other_client.patch(
                f"/api/v1/employer/job-posts/{job_post_id}",
                json={"title": "Unauthorized change"},
            )
            self.assertEqual(forbidden.status_code, 403)

            forbidden_apps = other_client.get(f"/api/v1/employer/job-posts/{job_post_id}/applications")
            self.assertEqual(forbidden_apps.status_code, 403)

            forbidden_milestones = other_client.get(f"/api/v1/employer/job-posts/{job_post_id}/milestones")
            self.assertEqual(forbidden_milestones.status_code, 403)
        finally:
            owner_client.close()
            other_client.close()


def tearDownModule():
    db = SessionLocal()
    try:
        pattern = f"%{TEST_RUN_TAG}%"
        db.execute(text("DELETE FROM refresh_tokens WHERE user_id IN (SELECT id FROM users WHERE email LIKE :pattern)"), {"pattern": pattern})
        db.execute(text("DELETE FROM user_topic_subscriptions WHERE user_id IN (SELECT id FROM users WHERE email LIKE :pattern)"), {"pattern": pattern})
        db.execute(text("DELETE FROM bookmarks WHERE user_id IN (SELECT id FROM users WHERE email LIKE :pattern)"), {"pattern": pattern})
        db.execute(text("DELETE FROM annotations WHERE author_id IN (SELECT id FROM users WHERE email LIKE :pattern)"), {"pattern": pattern})
        db.execute(text("DELETE FROM users WHERE email LIKE :pattern"), {"pattern": pattern})
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    unittest.main()
