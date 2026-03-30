import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.enums import RoleType
from app.models.review_workflow_template_stage import ReviewWorkflowTemplateStage
from app.models.risk_dictionary import RiskDictionary
from app.models.risk_grade_rule import RiskGradeRule
from app.models.risk_severity_weight import RiskSeverityWeight
from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User


SEED_ACCOUNTS = [
    ("student.meritforge@gmail.com", RoleType.STUDENT, "Student"),
    ("employer.meritforge@gmail.com", RoleType.EMPLOYER_MANAGER, "Employer Manager"),
    ("employer2.meritforge@gmail.com", RoleType.EMPLOYER_MANAGER, "Employer Manager Two"),
    ("author.meritforge@gmail.com", RoleType.CONTENT_AUTHOR, "Content Author"),
    ("author2.meritforge@gmail.com", RoleType.CONTENT_AUTHOR, "Content Author Two"),
    ("reviewer.meritforge@gmail.com", RoleType.REVIEWER, "Reviewer"),
    ("reviewer2.meritforge@gmail.com", RoleType.REVIEWER, "Reviewer Two"),
    ("admin.meritforge@gmail.com", RoleType.SYSTEM_ADMINISTRATOR, "System Administrator"),
]

LEGACY_SEED_EMAILS = {
    "student@meritforge.local",
    "employer@meritforge.local",
    "employer2@meritforge.local",
    "author@meritforge.local",
    "author2@meritforge.local",
    "reviewer@meritforge.local",
    "reviewer2@meritforge.local",
    "admin@meritforge.local",
}


def _ensure_role(db, role_type: RoleType) -> Role:
    role = db.scalar(select(Role).where(Role.name == role_type.value))
    if role:
        return role
    role = Role(name=role_type.value, description=f"Seeded role: {role_type.value}", is_active=True)
    db.add(role)
    db.flush()
    return role


def main() -> None:
    password = os.getenv("SEED_DEV_PASSWORD", "MeritForgeDev!2026")
    hashed_password = get_password_hash(password)

    db = SessionLocal()
    try:
        created = 0
        skipped = 0
        removed_legacy = 0

        for legacy_email in LEGACY_SEED_EMAILS:
            old_user = db.scalar(select(User).where(User.email == legacy_email))
            if old_user:
                db.delete(old_user)
                removed_legacy += 1

        for email, role_type, display_name in SEED_ACCOUNTS:
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                skipped += 1
                continue

            role = _ensure_role(db, role_type)
            user = User(
                email=email,
                hashed_password=hashed_password,
                display_name=display_name,
                role_id=role.id,
                is_active=True,
                is_verified=True,
                is_superuser=(role_type == RoleType.SYSTEM_ADMINISTRATOR),
            )
            db.add(user)
            created += 1

        if not db.scalar(select(RiskSeverityWeight).limit(1)):
            db.add_all(
                [
                    RiskSeverityWeight(severity="low", weight=1, rank=1),
                    RiskSeverityWeight(severity="medium", weight=3, rank=2),
                    RiskSeverityWeight(severity="high", weight=5, rank=3),
                ]
            )

        if not db.scalar(select(RiskGradeRule).limit(1)):
            db.add_all(
                [
                    RiskGradeRule(grade="low", min_score=0, max_score=4, blocked_until_final_approval=False, required_distinct_reviewers=1),
                    RiskGradeRule(grade="medium", min_score=5, max_score=14, blocked_until_final_approval=False, required_distinct_reviewers=2),
                    RiskGradeRule(grade="high", min_score=15, max_score=None, blocked_until_final_approval=True, required_distinct_reviewers=2),
                ]
            )

        if not db.scalar(select(RiskDictionary).where(RiskDictionary.term == "forbidden")):
            db.add(
                RiskDictionary(
                    term="forbidden",
                    category="policy",
                    severity="high",
                    description="Seeded keyword for risk scoring tests",
                    is_active=True,
                    is_regex=False,
                )
            )

        if not db.scalar(select(ReviewWorkflowTemplateStage).limit(1)):
            db.add_all(
                [
                    ReviewWorkflowTemplateStage(stage_name="Initial Review", stage_order=1, description="Seeded initial review", is_required=True, is_parallel=False, is_active=True),
                    ReviewWorkflowTemplateStage(stage_name="Final Review", stage_order=2, description="Seeded final review", is_required=True, is_parallel=False, is_active=True),
                ]
            )

        db.commit()
        print(f"Seed completed. removed_legacy={removed_legacy}, created={created}, skipped={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
