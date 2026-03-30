import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1 import api_router
from app.core.config import settings
from app.core.enums import AnnotationVisibility, ApplicationStatus, ContentStatus, ContentType
from app.core.database import get_db
from app.dependencies.auth import get_current_user


class _FakeScalarsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, scalar_values=None, scalars_values=None, execute_values=None):
        self.scalar_values = list(scalar_values or [])
        self.scalars_values = list(scalars_values or [])
        self.execute_values = list(execute_values or [])

    def scalar(self, *_args, **_kwargs):
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None

    def scalars(self, *_args, **_kwargs):
        if self.scalars_values:
            return _FakeScalarsResult(self.scalars_values.pop(0))
        return _FakeScalarsResult([])

    def execute(self, *_args, **_kwargs):
        if self.execute_values:
            return _FakeExecuteResult(self.execute_values.pop(0))
        return _FakeExecuteResult([])

    def add(self, obj):
        now = datetime.now(timezone.utc)
        if hasattr(obj, "id") and getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
            obj.updated_at = now

    def flush(self):
        return None

    def refresh(self, obj):
        now = datetime.now(timezone.utc)
        if hasattr(obj, "id") and getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at", None) is None:
            obj.updated_at = now

    def commit(self):
        return None

    def delete(self, _obj):
        return None


def _role(role_name: str):
    return SimpleNamespace(name=role_name)


def _user(role_name: str):
    return SimpleNamespace(
        id=uuid.uuid4(),
        email=f"{role_name}@example.local",
        role=_role(role_name),
        cohorts=[],
        is_active=True,
        hashed_password="not-used",
        created_at=datetime.now(timezone.utc),
    )


def _build_client(fake_db: _FakeDB, current_user=None):
    app = FastAPI()
    app.include_router(api_router)

    def _db_override():
        yield fake_db

    app.dependency_overrides[get_db] = _db_override
    if current_user is not None:
        app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


class AuthApiTests(unittest.TestCase):
    def test_register_conflict(self):
        fake_db = _FakeDB(scalar_values=[SimpleNamespace(id=uuid.uuid4())])
        client = _build_client(fake_db)

        response = client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "Password123"},
        )

        self.assertEqual(response.status_code, 409)

    def test_login_invalid_credentials(self):
        fake_db = _FakeDB(scalar_values=[None])
        client = _build_client(fake_db)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "Password123"},
        )

        self.assertEqual(response.status_code, 401)

    def test_register_returns_403_when_registration_disabled(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db)
        original_allow_registration = settings.allow_registration
        settings.allow_registration = False
        try:
            response = client.post(
                "/api/v1/auth/register",
                json={"email": "newuser@example.com", "password": "Password123"},
            )
        finally:
            settings.allow_registration = original_allow_registration

        self.assertEqual(response.status_code, 403)

    def test_login_wrong_password_returns_401(self):
        fake_db = _FakeDB(scalar_values=[SimpleNamespace(email="user@example.com", hashed_password="hash", is_active=True)])
        client = _build_client(fake_db)
        with patch("app.api.v1.auth.verify_password", return_value=False):
            response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "WrongPass123"})
        self.assertEqual(response.status_code, 401)

    def test_login_inactive_user_returns_forbidden(self):
        inactive_user = SimpleNamespace(
            id=uuid.uuid4(),
            email="inactive@example.com",
            is_active=False,
            role=_role("student"),
            hashed_password="hashed",
            first_name=None,
            last_name=None,
            display_name=None,
            role_id=1,
            created_at=datetime.now(timezone.utc),
            last_login_at=None,
        )
        fake_db = _FakeDB(scalar_values=[inactive_user])
        client = _build_client(fake_db)

        with patch("app.api.v1.auth.verify_password", return_value=True):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "inactive@example.com", "password": "Password123"},
            )

        self.assertEqual(response.status_code, 403)

    def test_protected_route_without_cookie_returns_unauthorized(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db)

        response = client.get("/api/v1/users/me")

        self.assertEqual(response.status_code, 401)

    def test_step_up_rejects_invalid_password(self):
        user = _user("student")
        client = _build_client(_FakeDB(), user)

        with patch("app.api.v1.auth.verify_password", return_value=False):
            response = client.post("/api/v1/auth/step-up", json={"password": "WrongPass123"})

        self.assertEqual(response.status_code, 403)

    def test_step_up_sets_cookie_for_valid_password(self):
        user = _user("student")
        client = _build_client(_FakeDB(), user)

        with patch("app.api.v1.auth.verify_password", return_value=True):
            response = client.post("/api/v1/auth/step-up", json={"password": "Password123"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("step_up_token=", response.headers.get("set-cookie", ""))


class ContentSubmissionApiTests(unittest.TestCase):
    def test_submission_rejects_role_without_permission(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db, _user("student"))

        response = client.post(
            "/api/v1/content/submissions",
            json={"content_type": "article", "title": "Blocked Article", "body": "Body text"},
        )

        self.assertEqual(response.status_code, 403)

    def test_submission_rejects_missing_body_for_article(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db, _user("content_author"))

        response = client.post(
            "/api/v1/content/submissions",
            json={"content_type": "article", "title": "No body"},
        )

        self.assertEqual(response.status_code, 422)


class ContentCatalogApiTests(unittest.TestCase):
    def test_content_catalog_requires_authentication(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db)

        response = client.get("/api/v1/content?type=video")

        self.assertEqual(response.status_code, 401)

    def test_content_catalog_for_student_returns_only_published(self):
        content_id_published = uuid.uuid4()
        content_id_draft = uuid.uuid4()
        version = SimpleNamespace(body="Published summary body", metadata_json={"media_url": "https://cdn/video.mp4", "submission_metadata": {"topic": "career"}})
        published_row = SimpleNamespace(
            id=content_id_published,
            title="Published Video",
            content_type=ContentType.VIDEO,
            status=ContentStatus.PUBLISHED,
            published_at=datetime.now(timezone.utc),
            retracted_at=None,
            current_version=version,
            canary_config=None,
            created_at=datetime.now(timezone.utc),
        )
        draft_row = SimpleNamespace(
            id=content_id_draft,
            title="Draft Video",
            content_type=ContentType.VIDEO,
            status=ContentStatus.DRAFT,
            published_at=None,
            retracted_at=None,
            current_version=version,
            canary_config=None,
            created_at=datetime.now(timezone.utc),
        )
        fake_db = _FakeDB(scalars_values=[[published_row, draft_row]])
        client = _build_client(fake_db, _user("student"))

        response = client.get("/api/v1/content?type=video")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], str(content_id_published))
        self.assertEqual(body[0]["content_type"], "video")

    def test_content_catalog_search_and_pagination(self):
        now = datetime.now(timezone.utc)
        version_one = SimpleNamespace(body="Interview preparation basics", metadata_json={"topic": "career"})
        version_two = SimpleNamespace(body="Portfolio depth", metadata_json={"topic": "portfolio"})
        row_one = SimpleNamespace(
            id=uuid.uuid4(),
            title="Interview Prep",
            content_type=ContentType.VIDEO,
            status=ContentStatus.PUBLISHED,
            published_at=now,
            retracted_at=None,
            current_version=version_one,
            canary_config=None,
            created_at=now,
        )
        row_two = SimpleNamespace(
            id=uuid.uuid4(),
            title="Portfolio Guide",
            content_type=ContentType.VIDEO,
            status=ContentStatus.PUBLISHED,
            published_at=now,
            retracted_at=None,
            current_version=version_two,
            canary_config=None,
            created_at=now,
        )
        fake_db = _FakeDB(scalars_values=[[row_one, row_two]])
        client = _build_client(fake_db, _user("student"))

        response = client.get("/api/v1/content?type=video&q=interview&limit=1&offset=0")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["title"], "Interview Prep")


class ReviewWorkflowApiTests(unittest.TestCase):
    def test_reviewer_queue_rejects_non_reviewer_role(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db, _user("student"))

        response = client.get("/api/v1/review-workflow/queue")

        self.assertEqual(response.status_code, 403)

    def test_return_for_revision_requires_meaningful_comment(self):
        stage_id = uuid.uuid4()
        content_id = uuid.uuid4()
        stage = SimpleNamespace(id=stage_id, content_id=content_id, stage_order=1)
        content = SimpleNamespace(id=content_id, current_version_id=uuid.uuid4())
        fake_db = _FakeDB(scalar_values=[stage, content])
        client = _build_client(fake_db, _user("reviewer"))

        response = client.post(
            f"/api/v1/review-workflow/stages/{stage_id}/decisions",
            json={"decision": "return_for_revision", "comments": "too short"},
        )

        self.assertEqual(response.status_code, 422)


class PublishingApiTests(unittest.TestCase):
    def test_schedule_rejects_insufficient_role(self):
        content_id = uuid.uuid4()
        fake_db = _FakeDB()
        client = _build_client(fake_db, _user("student"))

        publish_at = datetime.now(timezone.utc) + timedelta(days=1)
        response = client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={
                "scheduled_publish_at": publish_at.isoformat(),
                "canary": {"enabled": True, "percentage": 10, "duration_minutes": 60},
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_schedule_rejects_invalid_unpublish_window(self):
        content_id = uuid.uuid4()
        author = _user("content_author")
        content = SimpleNamespace(id=content_id, author_id=author.id, content_type=ContentType.ARTICLE)
        fake_db = _FakeDB(scalar_values=[content])
        client = _build_client(fake_db, author)

        publish_at = datetime.now(timezone.utc) + timedelta(days=1)
        unpublish_at = publish_at - timedelta(hours=1)
        response = client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={
                "scheduled_publish_at": publish_at.isoformat(),
                "scheduled_unpublish_at": unpublish_at.isoformat(),
                "canary": {"enabled": True, "percentage": 10, "duration_minutes": 60},
            },
        )

        self.assertEqual(response.status_code, 422)


class StepUpProtectionApiTests(unittest.TestCase):
    def test_takedown_requires_step_up_confirmation(self):
        content_id = uuid.uuid4()
        client = _build_client(_FakeDB(), _user("content_author"))
        response = client.post(f"/api/v1/publishing/content/{content_id}/takedown", json={"reason": "policy breach"})
        self.assertEqual(response.status_code, 403)

    def test_permission_change_requires_step_up_confirmation(self):
        client = _build_client(_FakeDB(), _user("system_administrator"))
        response = client.post(f"/api/v1/cohorts/{uuid.uuid4()}/users/{uuid.uuid4()}")
        self.assertEqual(response.status_code, 403)

    def test_account_deletion_mark_requires_step_up_confirmation(self):
        client = _build_client(_FakeDB(), _user("student"))
        response = client.post("/api/v1/users/me/deletion/mark", json={"reason": "cleanup"})
        self.assertEqual(response.status_code, 403)

    def test_account_deletion_mark_succeeds_after_step_up_confirmation(self):
        user = _user("student")
        client = _build_client(_FakeDB(), user)

        with patch("app.api.v1.auth.verify_password", return_value=True):
            step_up = client.post("/api/v1/auth/step-up", json={"password": "Password123"})
        self.assertEqual(step_up.status_code, 200)

        step_up_cookie = step_up.cookies.get(settings.step_up_cookie_name)
        if step_up_cookie:
            client.cookies.set(settings.step_up_cookie_name, step_up_cookie)

        response = client.post("/api/v1/users/me/deletion/mark", json={"reason": "cleanup"})
        self.assertEqual(response.status_code, 200)


class PublishingGovernanceApiTests(unittest.TestCase):
    def test_schedule_rejects_locked_content(self):
        content_id = uuid.uuid4()
        author = _user("content_author")
        content = SimpleNamespace(id=content_id, author_id=author.id, content_type=ContentType.ARTICLE, is_locked=True, status=ContentStatus.UNDER_REVIEW)
        fake_db = _FakeDB(scalar_values=[content])
        client = _build_client(fake_db, author)

        response = client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={"scheduled_publish_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        )

        self.assertEqual(response.status_code, 403)

    def test_schedule_rejects_blocked_risk_without_final_approval(self):
        content_id = uuid.uuid4()
        author = _user("content_author")
        content = SimpleNamespace(id=content_id, author_id=author.id, content_type=ContentType.ARTICLE, is_locked=False, status=ContentStatus.UNDER_REVIEW)
        risk = SimpleNamespace(blocked_until_final_approval=True)
        fake_db = _FakeDB(scalar_values=[content, risk])
        client = _build_client(fake_db, author)

        response = client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={"scheduled_publish_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        )

        self.assertEqual(response.status_code, 422)


class PublishingOwnershipApiTests(unittest.TestCase):
    def _confirm_step_up(self, client: TestClient):
        with patch("app.api.v1.auth.verify_password", return_value=True):
            step_up = client.post("/api/v1/auth/step-up", json={"password": "Password123"})
        self.assertEqual(step_up.status_code, 200)
        step_up_cookie = step_up.cookies.get(settings.step_up_cookie_name)
        if step_up_cookie:
            client.cookies.set(settings.step_up_cookie_name, step_up_cookie)

    def test_author_cannot_schedule_or_takedown_another_authors_content(self):
        content_id = uuid.uuid4()
        author_a = _user("content_author")
        author_b = _user("content_author")

        foreign_content_for_schedule = SimpleNamespace(
            id=content_id,
            author_id=author_b.id,
            content_type=ContentType.ARTICLE,
            is_locked=False,
            status=ContentStatus.DRAFT,
        )
        schedule_client = _build_client(_FakeDB(scalar_values=[foreign_content_for_schedule]), author_a)
        schedule_response = schedule_client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={"scheduled_publish_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        )
        self.assertEqual(schedule_response.status_code, 403)

        foreign_content_for_takedown = SimpleNamespace(
            id=content_id,
            author_id=author_b.id,
            content_type=ContentType.ARTICLE,
            status=ContentStatus.PUBLISHED,
            retracted_at=None,
            is_locked=False,
        )
        takedown_client = _build_client(_FakeDB(scalar_values=[foreign_content_for_takedown]), author_a)
        self._confirm_step_up(takedown_client)
        takedown_response = takedown_client.post(
            f"/api/v1/publishing/content/{content_id}/takedown",
            json={"reason": "policy breach"},
        )
        self.assertEqual(takedown_response.status_code, 403)

    def test_employer_cannot_schedule_or_takedown_other_employers_job_content(self):
        content_id = uuid.uuid4()
        employer_a = _user("employer_manager")
        employer_b = _user("employer_manager")

        job_content_for_schedule = SimpleNamespace(
            id=content_id,
            author_id=employer_b.id,
            content_type=ContentType.JOB_ANNOUNCEMENT,
            is_locked=False,
            status=ContentStatus.DRAFT,
        )
        foreign_job_post = SimpleNamespace(content_id=content_id, created_by_id=employer_b.id)
        schedule_client = _build_client(_FakeDB(scalar_values=[job_content_for_schedule, foreign_job_post]), employer_a)
        schedule_response = schedule_client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={"scheduled_publish_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        )
        self.assertEqual(schedule_response.status_code, 403)

        job_content_for_takedown = SimpleNamespace(
            id=content_id,
            author_id=employer_b.id,
            content_type=ContentType.JOB_ANNOUNCEMENT,
            status=ContentStatus.PUBLISHED,
            retracted_at=None,
            is_locked=False,
        )
        takedown_client = _build_client(_FakeDB(scalar_values=[job_content_for_takedown, foreign_job_post]), employer_a)
        self._confirm_step_up(takedown_client)
        takedown_response = takedown_client.post(
            f"/api/v1/publishing/content/{content_id}/takedown",
            json={"reason": "policy breach"},
        )
        self.assertEqual(takedown_response.status_code, 403)

    def test_rightful_owner_and_admin_can_schedule_and_takedown(self):
        content_id = uuid.uuid4()
        author = _user("content_author")
        admin = _user("system_administrator")

        own_content_schedule = SimpleNamespace(
            id=content_id,
            author_id=author.id,
            content_type=ContentType.ARTICLE,
            is_locked=False,
            status=ContentStatus.DRAFT,
        )
        owner_schedule_client = _build_client(_FakeDB(scalar_values=[own_content_schedule, None, None, None]), author)
        owner_schedule_response = owner_schedule_client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={"scheduled_publish_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        )
        self.assertEqual(owner_schedule_response.status_code, 200)

        admin_content_schedule = SimpleNamespace(
            id=content_id,
            author_id=author.id,
            content_type=ContentType.ARTICLE,
            is_locked=False,
            status=ContentStatus.DRAFT,
        )
        admin_schedule_client = _build_client(_FakeDB(scalar_values=[admin_content_schedule, None, None, None]), admin)
        admin_schedule_response = admin_schedule_client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={"scheduled_publish_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        )
        self.assertEqual(admin_schedule_response.status_code, 200)

        own_content_takedown = SimpleNamespace(
            id=content_id,
            author_id=author.id,
            content_type=ContentType.ARTICLE,
            status=ContentStatus.PUBLISHED,
            retracted_at=None,
            is_locked=False,
        )
        owner_takedown_client = _build_client(_FakeDB(scalar_values=[own_content_takedown, None, None]), author)
        self._confirm_step_up(owner_takedown_client)
        owner_takedown_response = owner_takedown_client.post(
            f"/api/v1/publishing/content/{content_id}/takedown",
            json={"reason": "policy breach"},
        )
        self.assertEqual(owner_takedown_response.status_code, 200)

        admin_content_takedown = SimpleNamespace(
            id=content_id,
            author_id=author.id,
            content_type=ContentType.ARTICLE,
            status=ContentStatus.PUBLISHED,
            retracted_at=None,
            is_locked=False,
        )
        admin_takedown_client = _build_client(_FakeDB(scalar_values=[admin_content_takedown, None, None]), admin)
        self._confirm_step_up(admin_takedown_client)
        admin_takedown_response = admin_takedown_client.post(
            f"/api/v1/publishing/content/{content_id}/takedown",
            json={"reason": "policy breach"},
        )
        self.assertEqual(admin_takedown_response.status_code, 200)


class PublishingHistoryAccessApiTests(unittest.TestCase):
    def test_non_admin_cannot_read_publishing_history(self):
        content_id = uuid.uuid4()
        client = _build_client(_FakeDB(), _user("student"))

        response = client.get(f"/api/v1/publishing/content/{content_id}/history")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_read_publishing_history(self):
        content_id = uuid.uuid4()
        row = SimpleNamespace(
            id=uuid.uuid4(),
            action="schedule_set",
            actor_id=uuid.uuid4(),
            reason="scheduled_publishing_configured",
            before_state={"status": "draft"},
            after_state={"status": "approved"},
            created_at=datetime.now(timezone.utc),
        )
        fake_db = _FakeDB(scalars_values=[[row]])
        client = _build_client(fake_db, _user("system_administrator"))

        response = client.get(f"/api/v1/publishing/content/{content_id}/history")

        self.assertEqual(response.status_code, 200)


class PublishingVisibilityAccessApiTests(unittest.TestCase):
    def test_student_cannot_query_another_users_visibility(self):
        fake_db = _FakeDB()
        student_a = _user("student")
        student_b = _user("student")
        content_id = uuid.uuid4()
        client = _build_client(fake_db, student_a)

        response = client.get(f"/api/v1/publishing/content/{content_id}/visibility/{student_b.id}")

        self.assertEqual(response.status_code, 403)

    def test_student_can_query_own_visibility(self):
        fake_db = _FakeDB()
        student = _user("student")
        content_id = uuid.uuid4()
        client = _build_client(fake_db, student)

        response = client.get(f"/api/v1/publishing/content/{content_id}/visibility/{student.id}")

        self.assertEqual(response.status_code, 200)

    def test_admin_can_query_other_users_visibility(self):
        fake_db = _FakeDB()
        admin = _user("system_administrator")
        student = _user("student")
        content_id = uuid.uuid4()
        client = _build_client(fake_db, admin)

        response = client.get(f"/api/v1/publishing/content/{content_id}/visibility/{student.id}")

        self.assertEqual(response.status_code, 200)


class TelemetryApiTests(unittest.TestCase):
    def test_telemetry_rejects_invalid_progress_percentage(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db, _user("student"))

        response = client.post(
            "/api/v1/telemetry/events",
            json={"event_type": "play", "progress_percentage": 101},
        )

        self.assertEqual(response.status_code, 422)


class AnnotationAuthorizationApiTests(unittest.TestCase):
    def test_update_annotation_rejects_non_owner(self):
        annotation_id = uuid.uuid4()
        annotation = SimpleNamespace(
            id=annotation_id,
            author_id=uuid.uuid4(),
            updated_at=datetime.now(timezone.utc),
        )
        fake_db = _FakeDB(scalar_values=[annotation])
        client = _build_client(fake_db, _user("student"))

        response = client.patch(
            f"/api/v1/annotations/{annotation_id}",
            json={
                "client_updated_at": datetime.now(timezone.utc).isoformat(),
                "annotation_text": "try to edit someone else note",
            },
        )

        self.assertEqual(response.status_code, 403)


class AnnotationVisibilityApiTests(unittest.TestCase):
    def test_user_in_cohort_sees_cohort_visible_annotation(self):
        content_id = uuid.uuid4()
        cohort_id = uuid.uuid4()
        annotation = SimpleNamespace(
            id=uuid.uuid4(),
            content_id=content_id,
            author_id=uuid.uuid4(),
            visibility=AnnotationVisibility.COHORT,
            cohort_id=cohort_id,
            start_offset=0,
            end_offset=10,
            highlighted_text="highlight",
            annotation_text="cohort note",
            color="yellow",
            tags=["tag1"],
            updated_at=datetime.now(timezone.utc),
            version=1,
        )
        fake_db = _FakeDB(scalars_values=[[annotation]])

        current_user = _user("student")
        current_user.cohorts = [SimpleNamespace(id=cohort_id)]
        client = _build_client(fake_db, current_user)

        response = client.get(f"/api/v1/contents/{content_id}/annotations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_user_not_in_cohort_does_not_see_cohort_visible_annotation(self):
        content_id = uuid.uuid4()
        cohort_id = uuid.uuid4()
        annotation = SimpleNamespace(
            id=uuid.uuid4(),
            content_id=content_id,
            author_id=uuid.uuid4(),
            visibility=AnnotationVisibility.COHORT,
            cohort_id=cohort_id,
            start_offset=0,
            end_offset=10,
            highlighted_text="highlight",
            annotation_text="cohort note",
            color="yellow",
            tags=["tag1"],
            updated_at=datetime.now(timezone.utc),
            version=1,
        )
        fake_db = _FakeDB(scalars_values=[[annotation]])

        current_user = _user("student")
        current_user.cohorts = []
        client = _build_client(fake_db, current_user)

        response = client.get(f"/api/v1/contents/{content_id}/annotations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_annotation_rejects_offsets_outside_source_text(self):
        content_id = uuid.uuid4()
        content = SimpleNamespace(
            id=content_id,
            current_version=SimpleNamespace(body="short text", metadata_json={}),
        )
        fake_db = _FakeDB(scalar_values=[content])
        client = _build_client(fake_db, _user("student"))

        response = client.post(
            "/api/v1/annotations",
            json={
                "content_id": str(content_id),
                "visibility": "private",
                "start_offset": 0,
                "end_offset": 100,
                "highlighted_text": "x",
                "annotation_text": "note",
                "tags": [],
            },
        )

        self.assertEqual(response.status_code, 422)


class EngagementMilestoneAuthorizationApiTests(unittest.TestCase):
    def test_employer_without_hiring_link_cannot_access_student_milestones(self):
        student_id = uuid.uuid4()
        employer = _user("employer_manager")

        read_client = _build_client(_FakeDB(scalar_values=[None]), employer)
        read_response = read_client.get(f"/api/v1/students/{student_id}/milestones")
        self.assertEqual(read_response.status_code, 403)

        write_client = _build_client(_FakeDB(scalar_values=[None]), employer)
        write_response = write_client.post(
            f"/api/v1/students/{student_id}/milestones/manual",
            json={
                "milestone_name": "Interview Prep",
                "milestone_type": "custom",
                "progress_value": 1,
                "target_value": 3,
            },
        )
        self.assertEqual(write_response.status_code, 403)

    def test_employer_with_hiring_link_can_read_and_update_student_milestones(self):
        now = datetime.now(timezone.utc)
        student_id = uuid.uuid4()
        employer = _user("employer_manager")
        milestone_id = uuid.uuid4()

        milestone = SimpleNamespace(
            id=milestone_id,
            student_id=student_id,
            milestone_template_id=None,
            milestone_type="custom",
            milestone_name="Interview Prep",
            description="Draft prep",
            is_custom=True,
            source="manual",
            progress_value=1,
            target_value=3,
            achievement_date=None,
            metadata_json={"level": "intro"},
            updated_at=now,
            version=1,
        )

        read_client = _build_client(
            _FakeDB(
                scalar_values=[uuid.uuid4()],
                scalars_values=[[milestone]],
            ),
            employer,
        )
        read_response = read_client.get(f"/api/v1/students/{student_id}/milestones")
        self.assertEqual(read_response.status_code, 200)

        update_client = _build_client(
            _FakeDB(scalar_values=[uuid.uuid4(), milestone]),
            employer,
        )
        update_response = update_client.patch(
            f"/api/v1/students/{student_id}/milestones/{milestone_id}",
            json={
                "client_updated_at": now.isoformat(),
                "milestone_name": "Interview Prep Updated",
                "progress_value": 2,
                "target_value": 3,
            },
        )
        self.assertEqual(update_response.status_code, 200)

    def test_student_self_access_still_allowed(self):
        student = _user("student")
        client = _build_client(_FakeDB(scalars_values=[[]]), student)

        response = client.get(f"/api/v1/students/{student.id}/milestones")
        self.assertEqual(response.status_code, 200)


class EmployerAuthorizationApiTests(unittest.TestCase):
    def test_other_employer_cannot_view_job_applications(self):
        owner_id = uuid.uuid4()
        job_post_id = uuid.uuid4()
        job_post = SimpleNamespace(id=job_post_id, created_by_id=owner_id)
        fake_db = _FakeDB(scalar_values=[job_post])

        user_b = _user("employer_manager")
        client = _build_client(fake_db, user_b)

        response = client.get(f"/api/v1/employer/job-posts/{job_post_id}/applications")

        self.assertEqual(response.status_code, 403)


class StudentJobApplicationApiTests(unittest.TestCase):
    def test_student_can_submit_application_for_active_published_job(self):
        job_post_id = uuid.uuid4()
        student = _user("student")
        fake_db = _FakeDB(
            scalar_values=[
                SimpleNamespace(id=job_post_id, content_id=uuid.uuid4(), is_active=True, created_by_id=uuid.uuid4()),
                SimpleNamespace(id=uuid.uuid4(), status=ContentStatus.PUBLISHED),
                None,
                None,
            ]
        )
        client = _build_client(fake_db, student)

        response = client.post(
            f"/api/v1/student/job-posts/{job_post_id}/applications",
            json={"cover_letter": "I am excited to apply."},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["job_post_id"], str(job_post_id))
        self.assertEqual(payload["applicant_id"], str(student.id))
        self.assertEqual(payload["status"], ApplicationStatus.SUBMITTED.value)

    def test_duplicate_active_application_returns_409(self):
        job_post_id = uuid.uuid4()
        student = _user("student")
        fake_db = _FakeDB(
            scalar_values=[
                SimpleNamespace(id=job_post_id, content_id=uuid.uuid4(), is_active=True, created_by_id=uuid.uuid4()),
                SimpleNamespace(id=uuid.uuid4(), status=ContentStatus.PUBLISHED),
                SimpleNamespace(id=uuid.uuid4(), status=ApplicationStatus.SUBMITTED),
            ]
        )
        client = _build_client(fake_db, student)

        response = client.post(
            f"/api/v1/student/job-posts/{job_post_id}/applications",
            json={},
        )

        self.assertEqual(response.status_code, 409)

    def test_non_student_cannot_submit_student_application(self):
        job_post_id = uuid.uuid4()
        fake_db = _FakeDB()
        client = _build_client(fake_db, _user("employer_manager"))

        response = client.post(
            f"/api/v1/student/job-posts/{job_post_id}/applications",
            json={},
        )

        self.assertEqual(response.status_code, 403)

    def test_other_employer_cannot_update_application_status(self):
        app_id = uuid.uuid4()
        app_row = SimpleNamespace(id=app_id, job_post_id=uuid.uuid4())
        job_post = SimpleNamespace(id=app_row.job_post_id, created_by_id=uuid.uuid4())
        fake_db = _FakeDB(scalar_values=[app_row, job_post])
        client = _build_client(fake_db, _user("employer_manager"))

        response = client.patch(f"/api/v1/employer/applications/{app_id}/status", json={"status": "under_review", "notes": "x"})

        self.assertEqual(response.status_code, 403)

    def test_other_employer_cannot_view_job_milestones(self):
        job_post_id = uuid.uuid4()
        job_post = SimpleNamespace(id=job_post_id, created_by_id=uuid.uuid4())
        fake_db = _FakeDB(scalar_values=[job_post])
        client = _build_client(fake_db, _user("employer_manager"))

        response = client.get(f"/api/v1/employer/job-posts/{job_post_id}/milestones")

        self.assertEqual(response.status_code, 403)


class OperationsAccessApiTests(unittest.TestCase):
    def test_non_admin_cannot_access_operations_metrics_or_export(self):
        client = _build_client(_FakeDB(), _user("student"))
        params = {"start_date": "2026-01-01", "end_date": "2026-01-02"}
        self.assertEqual(client.get("/api/v1/operations/metrics", params=params).status_code, 403)
        self.assertEqual(client.get("/api/v1/operations/metrics/export.csv", params=params).status_code, 403)

    def test_admin_can_access_operations_metrics_and_export(self):
        row = SimpleNamespace(
            metric_date=date(2026, 1, 1),
            active_users=10,
            returning_users=4,
            interacted_users=8,
            applying_users=3,
            converted_users=2,
            job_posts_created=5,
            applications_created=4,
            milestones_completed=1,
        )
        fake_db = _FakeDB(
            scalars_values=[[row], [row]],
            execute_values=[[("play", 3)], [("play", 2)]],
        )
        client = _build_client(fake_db, _user("system_administrator"))
        params = {"start_date": "2026-01-01", "end_date": "2026-01-02"}
        metrics = client.get("/api/v1/operations/metrics", params=params)
        export_csv = client.get("/api/v1/operations/metrics/export.csv", params=params)
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(export_csv.status_code, 200)
        self.assertIn("text/csv", export_csv.headers.get("content-type", ""))


class BookmarkApiTests(unittest.TestCase):
    def test_list_bookmarks_empty(self):
        fake_db = _FakeDB(scalars_values=[[]])
        client = _build_client(fake_db, _user("student"))

        response = client.get("/api/v1/bookmarks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_bookmark(self):
        content_id = uuid.uuid4()
        fake_db = _FakeDB(scalar_values=[SimpleNamespace(id=content_id), None])
        client = _build_client(fake_db, _user("student"))

        response = client.post("/api/v1/bookmarks", json={"content_id": str(content_id), "is_favorite": False})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["content_id"], str(content_id))

    def test_toggle_favorite_updates_existing_bookmark(self):
        content_id = uuid.uuid4()
        bookmark = SimpleNamespace(
            id=uuid.uuid4(),
            content_id=content_id,
            is_favorite=False,
            folder=None,
            notes=None,
            updated_at=datetime.now(timezone.utc),
        )
        fake_db = _FakeDB(scalar_values=[SimpleNamespace(id=content_id), bookmark])
        client = _build_client(fake_db, _user("student"))

        response = client.post("/api/v1/bookmarks", json={"content_id": str(content_id), "is_favorite": True})

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["is_favorite"])

    def test_delete_bookmark(self):
        content_id = uuid.uuid4()
        bookmark = SimpleNamespace(id=uuid.uuid4(), content_id=content_id, is_favorite=False, folder=None)
        fake_db = _FakeDB(scalar_values=[SimpleNamespace(id=content_id), bookmark])
        client = _build_client(fake_db, _user("student"))

        response = client.delete(f"/api/v1/bookmarks/{content_id}")

        self.assertEqual(response.status_code, 204)

    def test_cross_user_delete_isolation(self):
        content_id = uuid.uuid4()
        fake_db = _FakeDB(scalar_values=[SimpleNamespace(id=content_id), None])
        client = _build_client(fake_db, _user("student"))

        response = client.delete(f"/api/v1/bookmarks/{content_id}")

        self.assertEqual(response.status_code, 404)


class TopicSubscriptionApiTests(unittest.TestCase):
    def test_list_topic_subscriptions_empty(self):
        fake_db = _FakeDB(scalars_values=[[]])
        client = _build_client(fake_db, _user("student"))

        response = client.get("/api/v1/users/me/topic-subscriptions")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_topic_subscription(self):
        fake_db = _FakeDB(scalar_values=[None])
        client = _build_client(fake_db, _user("student"))

        response = client.post("/api/v1/users/me/topic-subscriptions", json={"topic": "Portfolio"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["topic"], "portfolio")

    def test_delete_topic_subscription_is_scoped_to_user(self):
        fake_db = _FakeDB(scalar_values=[None])
        client = _build_client(fake_db, _user("student"))

        response = client.delete("/api/v1/users/me/topic-subscriptions", params={"topic": "portfolio"})

        self.assertEqual(response.status_code, 404)


class UserMeApiTests(unittest.TestCase):
    def test_get_users_me_without_cookie_returns_401(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db)

        response = client.get("/api/v1/users/me")

        self.assertEqual(response.status_code, 401)


class UserProfileAccessApiTests(unittest.TestCase):
    def test_non_admin_cannot_fetch_another_user_profile_while_self_and_admin_can(self):
        now = datetime.now(timezone.utc)
        student_a = _user("student")
        student_b = _user("student")
        admin = _user("system_administrator")

        student_a_target = SimpleNamespace(
            id=student_a.id,
            email=student_a.email,
            first_name="Alice",
            last_name="Anderson",
            display_name="alice",
            bio="student-a-bio",
            avatar_url="https://cdn.example/a.png",
            phone_number="+10000000001",
            consent_contact_info_visible=False,
            consent_photo_visible=False,
            consent_analytics=True,
            consent_data_portability=True,
            created_at=now,
            updated_at=now,
            is_active=True,
        )
        student_b_target = SimpleNamespace(
            id=student_b.id,
            email=student_b.email,
            first_name="Bob",
            last_name="Brown",
            display_name="bob",
            bio="student-b-bio",
            avatar_url="https://cdn.example/b.png",
            phone_number="+10000000002",
            consent_contact_info_visible=False,
            consent_photo_visible=False,
            consent_analytics=True,
            consent_data_portability=True,
            created_at=now,
            updated_at=now,
            is_active=True,
        )

        fake_db = _FakeDB(scalar_values=[student_a_target, student_b_target])

        student_client = _build_client(fake_db, student_a)
        forbidden = student_client.get(f"/api/v1/users/{student_b.id}")
        self.assertEqual(forbidden.status_code, 403)

        self_response = student_client.get(f"/api/v1/users/{student_a.id}")
        self.assertEqual(self_response.status_code, 200)
        self_payload = self_response.json()
        self.assertEqual(self_payload["id"], str(student_a.id))
        self.assertEqual(self_payload["email"], student_a.email)
        self.assertEqual(self_payload["phone_number"], "+10000000001")
        self.assertEqual(self_payload["avatar_url"], "https://cdn.example/a.png")

        admin_client = _build_client(fake_db, admin)
        admin_response = admin_client.get(f"/api/v1/users/{student_b.id}")
        self.assertEqual(admin_response.status_code, 200)
        admin_payload = admin_response.json()
        self.assertEqual(admin_payload["id"], str(student_b.id))
        self.assertEqual(admin_payload["display_name"], "bob")
        self.assertEqual(admin_payload["email"], None)
        self.assertEqual(admin_payload["phone_number"], None)
        self.assertEqual(admin_payload["avatar_url"], None)


class AdminAccessApiTests(unittest.TestCase):
    def test_student_cannot_access_audit_logs_endpoint(self):
        fake_db = _FakeDB()
        client = _build_client(fake_db, _user("student"))

        response = client.get("/api/v1/audit-logs")

        self.assertEqual(response.status_code, 403)

if __name__ == "__main__":
    unittest.main()
