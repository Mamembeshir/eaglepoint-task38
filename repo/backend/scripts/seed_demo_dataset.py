import os

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.enums import RoleType
from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User

try:
    from scripts.seed_demo_dataset_helpers import (
        approve_all_stages,
        build_demo_items,
        ensure_content_and_version,
        ensure_demo_cohort,
        ensure_job_post_and_application,
        ensure_risk_defaults,
        ensure_template_stages,
        initialize_counters,
        publish_content,
    )
except ImportError:
    from seed_demo_dataset_helpers import (  # type: ignore[no-redef]
        approve_all_stages,
        build_demo_items,
        ensure_content_and_version,
        ensure_demo_cohort,
        ensure_job_post_and_application,
        ensure_risk_defaults,
        ensure_template_stages,
        initialize_counters,
        publish_content,
    )

DEMO_VIDEO_URL_DEFAULT = "https://filesamples.com/samples/video/mp4/sample_640x360.mp4"
SEED_ACCOUNTS = [
    ("student.meritforge@gmail.com", RoleType.STUDENT, "Student"),
    ("employer.meritforge@gmail.com", RoleType.EMPLOYER_MANAGER, "Employer Manager"),
    ("author.meritforge@gmail.com", RoleType.CONTENT_AUTHOR, "Content Author"),
    ("reviewer.meritforge@gmail.com", RoleType.REVIEWER, "Reviewer"),
    ("admin.meritforge@gmail.com", RoleType.SYSTEM_ADMINISTRATOR, "System Administrator"),
]


def _ensure_role(db, role_type: RoleType, counters: dict) -> Role:
    role = db.scalar(select(Role).where(Role.name == role_type.value))
    if role:
        if not role.is_active:
            role.is_active = True
            counters["roles_updated"] += 1
        return role
    role = Role(name=role_type.value, description=f"Seeded role: {role_type.value}", is_active=True)
    db.add(role)
    db.flush()
    counters["roles_created"] += 1
    return role


def _ensure_seed_users(db, counters: dict) -> dict[RoleType, User]:
    password = os.getenv("SEED_DEV_PASSWORD", "MeritForgeDev!2026")
    hashed_password = get_password_hash(password)

    users: dict[RoleType, User] = {}
    for email, role_type, display_name in SEED_ACCOUNTS:
        role = _ensure_role(db, role_type, counters)
        user = db.scalar(select(User).where(User.email == email))
        if user:
            changed = False
            if user.role_id != role.id:
                user.role_id = role.id
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if not user.is_verified:
                user.is_verified = True
                changed = True
            if user.is_superuser != (role_type == RoleType.SYSTEM_ADMINISTRATOR):
                user.is_superuser = role_type == RoleType.SYSTEM_ADMINISTRATOR
                changed = True
            if user.display_name != display_name:
                user.display_name = display_name
                changed = True
            if user.hashed_password != hashed_password:
                user.hashed_password = hashed_password
                changed = True
            if changed:
                counters["users_updated"] += 1
        else:
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
            db.flush()
            counters["users_created"] += 1
        users[role_type] = user

    return users


def main() -> None:
    demo_video_url = os.getenv("DEMO_VIDEO_URL", DEMO_VIDEO_URL_DEFAULT)
    counters = initialize_counters()

    db = SessionLocal()
    try:
        users = _ensure_seed_users(db, counters)
        admin = users[RoleType.SYSTEM_ADMINISTRATOR]
        author = users[RoleType.CONTENT_AUTHOR]
        reviewer = users[RoleType.REVIEWER]
        employer = users[RoleType.EMPLOYER_MANAGER]
        student = users[RoleType.STUDENT]

        ensure_risk_defaults(db, admin, counters)
        ensure_template_stages(db, admin, counters)

        seeded_contents = {}
        for spec in build_demo_items(demo_video_url, author, employer):
            content, version = ensure_content_and_version(
                db,
                slug=spec["slug"],
                title=spec["title"],
                content_type=spec["content_type"],
                author=spec["author"],
                body=spec["body"],
                media_url=spec["media_url"],
                topic=spec["topic"],
                counters=counters,
            )
            approve_all_stages(db, content, version, reviewer, counters)
            publish_content(db, content, admin, counters)
            seeded_contents[spec["slug"]] = content

        ensure_job_post_and_application(
            db,
            job_content=seeded_contents["demo-job-announcement-1"],
            employer=employer,
            student=student,
            counters=counters,
        )
        ensure_demo_cohort(db, admin, student, counters)

        db.commit()

        print("Demo dataset seed completed.")
        print("Summary:")
        for key in sorted(counters.keys()):
            print(f"  {key}={counters[key]}")
        print("Seeded slugs: demo-career-video-1, demo-career-video-2, demo-career-article-1, demo-job-announcement-1")
    finally:
        db.close()


if __name__ == "__main__":
    main()
