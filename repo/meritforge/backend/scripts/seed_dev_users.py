import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.enums import RoleType
from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User


SEED_ACCOUNTS = [
    ("student.meritforge@gmail.com", RoleType.STUDENT, "Student"),
    ("employer.meritforge@gmail.com", RoleType.EMPLOYER_MANAGER, "Employer Manager"),
    ("author.meritforge@gmail.com", RoleType.CONTENT_AUTHOR, "Content Author"),
    ("reviewer.meritforge@gmail.com", RoleType.REVIEWER, "Reviewer"),
    ("admin.meritforge@gmail.com", RoleType.SYSTEM_ADMINISTRATOR, "System Administrator"),
]

LEGACY_SEED_EMAILS = {
    "student@meritforge.local",
    "employer@meritforge.local",
    "author@meritforge.local",
    "reviewer@meritforge.local",
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

        db.commit()
        print(f"Seed completed. removed_legacy={removed_legacy}, created={created}, skipped={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
