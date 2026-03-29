import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.v1 import api_router
from app.core.database import SessionLocal
from app.core.enums import RoleType
from app.core.security import get_password_hash
from app.dependencies.auth import get_current_user
from app.models.risk_dictionary import RiskDictionary
from app.models.risk_grade_rule import RiskGradeRule
from app.models.risk_severity_weight import RiskSeverityWeight
from app.models.review_workflow_template_stage import ReviewWorkflowTemplateStage
from app.models.role import Role
from app.models.user import User


class DbBackedWorkflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current_user = None
        app = FastAPI()
        app.include_router(api_router)
        app.dependency_overrides[get_current_user] = lambda: cls.current_user
        cls.client = TestClient(app)
        cls.seed_tag = uuid.uuid4().hex[:8]
        cls._ensure_risk_config()
        cls.author = cls._ensure_user(RoleType.CONTENT_AUTHOR, f"author.{cls.seed_tag}@example.com")
        cls.reviewer = cls._ensure_user(RoleType.REVIEWER, f"reviewer.{cls.seed_tag}@example.com")
        cls.student = cls._ensure_user(RoleType.STUDENT, f"student.{cls.seed_tag}@example.com")
        cls.author_ctx = cls._as_current_user(cls.author, RoleType.CONTENT_AUTHOR)
        cls.reviewer_ctx = cls._as_current_user(cls.reviewer, RoleType.REVIEWER)
        cls.student_ctx = cls._as_current_user(cls.student, RoleType.STUDENT)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        db = SessionLocal()
        try:
            users = db.scalars(select(User).where(User.email.like(f"%.{cls.seed_tag}@example.com"))).all()
            for user in users:
                db.delete(user)
            db.commit()
        finally:
            db.close()

    @classmethod
    def _ensure_role(cls, role_type: RoleType) -> Role:
        db = SessionLocal()
        try:
            role = db.scalar(select(Role).where(Role.name == role_type.value))
            if role:
                return role
            role = Role(name=role_type.value, description=f"test role {role_type.value}", is_active=True)
            db.add(role)
            db.commit()
            db.refresh(role)
            return role
        finally:
            db.close()

    @classmethod
    def _ensure_user(cls, role_type: RoleType, email: str) -> User:
        db = SessionLocal()
        try:
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                return existing
            role = cls._ensure_role(role_type)
            user = User(
                email=email,
                hashed_password=get_password_hash("Password123"),
                display_name=email.split("@")[0],
                role_id=role.id,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()

    @staticmethod
    def _as_current_user(user: User, role_type: RoleType) -> SimpleNamespace:
        return SimpleNamespace(
            id=user.id,
            email=user.email,
            role_id=user.role_id,
            is_active=True,
            is_verified=True,
            role=SimpleNamespace(name=role_type.value),
        )

    @classmethod
    def _ensure_risk_config(cls):
        db = SessionLocal()
        try:
            if not db.scalar(select(RiskDictionary).limit(1)):
                db.add(RiskDictionary(term="forbidden", category="policy", severity="high", is_active=True, is_regex=False, match_count=0))
            if not db.scalar(select(RiskSeverityWeight).limit(1)):
                db.add_all([
                    RiskSeverityWeight(severity="low", weight=1, rank=1),
                    RiskSeverityWeight(severity="medium", weight=3, rank=2),
                    RiskSeverityWeight(severity="high", weight=5, rank=3),
                ])
            if not db.scalar(select(RiskGradeRule).limit(1)):
                db.add_all([
                    RiskGradeRule(grade="low", min_score=0, max_score=4, blocked_until_final_approval=False, required_distinct_reviewers=1),
                    RiskGradeRule(grade="medium", min_score=5, max_score=14, blocked_until_final_approval=False, required_distinct_reviewers=2),
                    RiskGradeRule(grade="high", min_score=15, max_score=None, blocked_until_final_approval=True, required_distinct_reviewers=2),
                ])
            db.commit()
        finally:
            db.close()

    def test_submit_review_publish_and_telemetry_flow(self):
        db = SessionLocal()
        try:
            for stage in db.scalars(select(ReviewWorkflowTemplateStage)).all():
                db.delete(stage)
            db.commit()
        finally:
            db.close()

        self.__class__.current_user = self.author_ctx
        submission = self.client.post(
            "/api/v1/content/submissions",
            json={
                "content_type": "video",
                "title": f"Workflow Test {self.seed_tag}",
                "media_url": "https://cdn.example/video.mp4",
                "metadata": {"topic": "career", "summary": "workflow summary"},
            },
        )
        self.assertEqual(submission.status_code, 201)
        content_id = submission.json()["content_id"]

        reviewer_queue = self.client.get("/api/v1/review-workflow/queue")
        self.assertEqual(reviewer_queue.status_code, 403)

        self.__class__.current_user = self.reviewer_ctx
        reviewer_queue = self.client.get("/api/v1/review-workflow/queue")
        self.assertEqual(reviewer_queue.status_code, 200)
        queue_items = reviewer_queue.json()
        self.assertTrue(queue_items)
        self.assertEqual(queue_items[0]["content_id"], content_id)
        self.assertEqual(queue_items[0]["stage_name"], "Initial Review")
        stage_id = queue_items[0]["stage_id"]

        decision = self.client.post(
            f"/api/v1/review-workflow/stages/{stage_id}/decisions",
            json={"decision": "approve", "comments": "Looks good for publishing."},
        )
        self.assertEqual(decision.status_code, 200)

        self.__class__.current_user = self.author_ctx
        schedule = self.client.post(
            f"/api/v1/publishing/content/{content_id}/schedule",
            json={"scheduled_publish_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()},
        )
        self.assertEqual(schedule.status_code, 200)

        self.__class__.current_user = self.student_ctx
        telemetry = self.client.post(
            "/api/v1/telemetry/events",
            json={"event_type": "play", "content_id": content_id, "event_data": {"position_seconds": 12}},
        )
        self.assertEqual(telemetry.status_code, 201)


if __name__ == "__main__":
    unittest.main()
