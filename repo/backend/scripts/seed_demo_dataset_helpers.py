from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.enums import ApplicationStatus, ContentStatus, ContentType, SegmentationType
from app.models.application import Application
from app.models.canary_release_config import CanaryReleaseConfig
from app.models.content import Content
from app.models.content_risk_assessment import ContentRiskAssessment
from app.models.content_version import ContentVersion
from app.models.job_post import JobPost
from app.models.publishing_schedule import PublishingSchedule
from app.models.review_decision import ReviewDecision
from app.models.review_workflow_template_stage import ReviewWorkflowTemplateStage
from app.models.risk_dictionary import RiskDictionary
from app.models.risk_grade_rule import RiskGradeRule
from app.models.risk_severity_weight import RiskSeverityWeight
from app.models.user import User
from app.models.user_cohort import UserCohort
from app.services.review_workflow_service import ensure_content_review_workflow

DEFAULT_TEMPLATE_STAGES = [
    ("Initial Review", 1),
    ("Secondary Review", 2),
    ("Final Review", 3),
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def initialize_counters() -> dict[str, int]:
    return {
        "roles_created": 0,
        "roles_updated": 0,
        "users_created": 0,
        "users_updated": 0,
        "risk_weights_created": 0,
        "risk_weights_updated": 0,
        "risk_rules_created": 0,
        "risk_rules_updated": 0,
        "risk_terms_created": 0,
        "template_stages_created": 0,
        "template_stages_updated": 0,
        "content_created": 0,
        "content_updated": 0,
        "content_versions_created": 0,
        "content_versions_updated": 0,
        "risk_assessments_created": 0,
        "risk_assessments_updated": 0,
        "workflow_instances_created": 0,
        "workflow_stages_completed": 0,
        "review_decisions_created": 0,
        "publishing_schedules_created": 0,
        "publishing_schedules_updated": 0,
        "canary_configs_created": 0,
        "canary_configs_updated": 0,
        "job_posts_created": 0,
        "job_posts_updated": 0,
        "applications_created": 0,
        "applications_updated": 0,
        "cohorts_created": 0,
        "cohorts_updated": 0,
        "cohort_memberships_created": 0,
    }


def build_demo_items(demo_video_url: str, author: User, employer: User) -> list[dict]:
    return [
        {
            "slug": "demo-career-video-1",
            "title": "Demo Career Video: Interview Foundations",
            "content_type": ContentType.VIDEO,
            "body": "Learn interview fundamentals, confidence framing, and preparation tactics.",
            "media_url": demo_video_url,
            "topic": "interview-skills",
            "author": author,
        },
        {
            "slug": "demo-career-video-2",
            "title": "Demo Career Video: Resume Storytelling",
            "content_type": ContentType.VIDEO,
            "body": "Build a stronger resume narrative with measurable outcomes.",
            "media_url": demo_video_url,
            "topic": "resume-strategy",
            "author": author,
        },
        {
            "slug": "demo-career-article-1",
            "title": "Demo Article: First Week Success Plan",
            "content_type": ContentType.ARTICLE,
            "body": "This guide walks students through a practical first-week success plan for new roles.",
            "media_url": None,
            "topic": "career-readiness",
            "author": author,
        },
        {
            "slug": "demo-job-announcement-1",
            "title": "Demo Job Announcement: Junior Analyst",
            "content_type": ContentType.JOB_ANNOUNCEMENT,
            "body": "MeritForge Demo Employer seeks a junior analyst with strong communication skills.",
            "media_url": None,
            "topic": "hiring",
            "author": employer,
        },
    ]


def ensure_risk_defaults(db, admin_user: User, counters: dict) -> None:
    severity_defaults = [("low", 1, 1), ("medium", 3, 2), ("high", 5, 3)]
    for severity, weight, rank in severity_defaults:
        row = db.scalar(select(RiskSeverityWeight).where(RiskSeverityWeight.severity == severity))
        if row:
            changed = False
            if row.weight != weight:
                row.weight = weight
                changed = True
            if row.rank != rank:
                row.rank = rank
                changed = True
            if changed:
                counters["risk_weights_updated"] += 1
            continue
        db.add(RiskSeverityWeight(severity=severity, weight=weight, rank=rank))
        counters["risk_weights_created"] += 1

    rule_defaults = [
        ("low", 0, 4, False, 1),
        ("medium", 5, 14, False, 2),
        ("high", 15, None, True, 2),
    ]
    for grade, min_score, max_score, blocked, reviewers in rule_defaults:
        row = db.scalar(select(RiskGradeRule).where(RiskGradeRule.grade == grade))
        if row:
            changed = False
            if row.min_score != min_score:
                row.min_score = min_score
                changed = True
            if row.max_score != max_score:
                row.max_score = max_score
                changed = True
            if row.blocked_until_final_approval != blocked:
                row.blocked_until_final_approval = blocked
                changed = True
            if row.required_distinct_reviewers != reviewers:
                row.required_distinct_reviewers = reviewers
                changed = True
            if changed:
                counters["risk_rules_updated"] += 1
            continue
        db.add(
            RiskGradeRule(
                grade=grade,
                min_score=min_score,
                max_score=max_score,
                blocked_until_final_approval=blocked,
                required_distinct_reviewers=reviewers,
            )
        )
        counters["risk_rules_created"] += 1

    term = db.scalar(select(RiskDictionary).where(RiskDictionary.term == "demo-safe-term"))
    if not term:
        db.add(
            RiskDictionary(
                term="demo-safe-term",
                category="demo",
                severity="low",
                description="Ensures dictionary is initialized for demo flows",
                is_active=True,
                is_regex=False,
                match_count=0,
                created_by_id=admin_user.id,
            )
        )
        counters["risk_terms_created"] += 1


def ensure_template_stages(db, admin_user: User, counters: dict) -> None:
    for stage_name, stage_order in DEFAULT_TEMPLATE_STAGES:
        existing = db.scalar(
            select(ReviewWorkflowTemplateStage).where(
                ReviewWorkflowTemplateStage.stage_name == stage_name,
                ReviewWorkflowTemplateStage.stage_order == stage_order,
            )
        )
        if existing:
            changed = False
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if not existing.is_required:
                existing.is_required = True
                changed = True
            if existing.is_parallel:
                existing.is_parallel = False
                changed = True
            if changed:
                counters["template_stages_updated"] += 1
            continue

        db.add(
            ReviewWorkflowTemplateStage(
                stage_name=stage_name,
                stage_order=stage_order,
                description=f"{stage_name} for demo workflow",
                is_required=True,
                is_parallel=False,
                is_active=True,
                created_by_id=admin_user.id,
            )
        )
        counters["template_stages_created"] += 1


def ensure_content_and_version(
    db,
    *,
    slug: str,
    title: str,
    content_type: ContentType,
    author: User,
    body: str | None,
    media_url: str | None,
    topic: str,
    counters: dict,
) -> tuple[Content, ContentVersion]:
    content = db.scalar(select(Content).where(Content.slug == slug))
    if content:
        content.title = title
        content.content_type = content_type
        content.author_id = author.id
        counters["content_updated"] += 1
    else:
        content = Content(
            title=title,
            slug=slug,
            content_type=content_type,
            status=ContentStatus.DRAFT,
            author_id=author.id,
            is_locked=False,
        )
        db.add(content)
        db.flush()
        counters["content_created"] += 1

    metadata_json: dict = {
        "submission_metadata": {
            "topic": topic,
            "summary": (body or "")[:180],
            "seed_source": "seed_demo_dataset",
        }
    }
    if media_url:
        metadata_json["media_url"] = media_url
        metadata_json["submission_metadata"]["duration_seconds"] = 125

    version = db.scalar(
        select(ContentVersion).where(
            ContentVersion.content_id == content.id,
            ContentVersion.version_number == 1,
        )
    )
    if version:
        version.title = title
        version.body = body
        version.metadata_json = metadata_json
        version.created_by_id = author.id
        counters["content_versions_updated"] += 1
    else:
        version = ContentVersion(
            content_id=content.id,
            version_number=1,
            title=title,
            body=body,
            metadata_json=metadata_json,
            change_summary="Demo dataset seed",
            created_by_id=author.id,
            is_published_version=False,
        )
        db.add(version)
        db.flush()
        counters["content_versions_created"] += 1

    content.current_version_id = version.id

    risk = db.scalar(select(ContentRiskAssessment).where(ContentRiskAssessment.content_id == content.id))
    if risk:
        risk.risk_score = 0
        risk.risk_grade = "low"
        risk.triggering_words = []
        risk.blocked_until_final_approval = False
        risk.required_distinct_reviewers = 1
        counters["risk_assessments_updated"] += 1
    else:
        db.add(
            ContentRiskAssessment(
                content_id=content.id,
                risk_score=0,
                risk_grade="low",
                triggering_words=[],
                blocked_until_final_approval=False,
                required_distinct_reviewers=1,
            )
        )
        counters["risk_assessments_created"] += 1

    return content, version


def approve_all_stages(db, content: Content, version: ContentVersion, reviewer: User, counters: dict) -> None:
    stages, created = ensure_content_review_workflow(db, content, created_by_id=reviewer.id)
    if created:
        counters["workflow_instances_created"] += 1

    ordered_stages = sorted(stages, key=lambda stage: stage.stage_order)
    for stage in ordered_stages:
        existing_approve = db.scalar(
            select(ReviewDecision).where(
                ReviewDecision.stage_id == stage.id,
                ReviewDecision.decision == "approve",
            )
        )
        if not existing_approve:
            db.add(
                ReviewDecision(
                    stage_id=stage.id,
                    reviewer_id=reviewer.id,
                    decision="approve",
                    comments=f"Demo seed approval for {stage.stage_name}",
                    content_version_id=version.id,
                )
            )
            counters["review_decisions_created"] += 1
        if not stage.is_completed:
            stage.is_completed = True
            stage.completed_at = now_utc()
            counters["workflow_stages_completed"] += 1

    content.status = ContentStatus.APPROVED
    content.is_locked = False
    content.retracted_at = None


def publish_content(db, content: Content, publisher: User, counters: dict) -> None:
    now = now_utc()
    content.status = ContentStatus.PUBLISHED
    content.published_at = now
    content.retracted_at = None
    content.is_locked = False
    if content.current_version:
        content.current_version.is_published_version = True

    schedule = db.scalar(select(PublishingSchedule).where(PublishingSchedule.content_id == content.id))
    if schedule:
        schedule.scheduled_publish_at = now - timedelta(minutes=2)
        schedule.scheduled_unpublish_at = None
        schedule.is_published = True
        schedule.is_unpublished = False
        schedule.published_at = now
        schedule.unpublished_at = None
        schedule.created_by_id = publisher.id
        counters["publishing_schedules_updated"] += 1
    else:
        db.add(
            PublishingSchedule(
                content_id=content.id,
                scheduled_publish_at=now - timedelta(minutes=2),
                scheduled_unpublish_at=None,
                is_published=True,
                is_unpublished=False,
                published_at=now,
                unpublished_at=None,
                created_by_id=publisher.id,
            )
        )
        counters["publishing_schedules_created"] += 1

    canary = db.scalar(select(CanaryReleaseConfig).where(CanaryReleaseConfig.content_id == content.id))
    if canary:
        canary.is_enabled = False
        canary.is_active = False
        canary.percentage = 0
        canary.duration_minutes = 120
        canary.segmentation_type = SegmentationType.RANDOM
        canary.target_cohort_ids = None
        canary.started_at = None
        canary.completed_at = now
        canary.created_by_id = publisher.id
        counters["canary_configs_updated"] += 1
    else:
        db.add(
            CanaryReleaseConfig(
                content_id=content.id,
                is_enabled=False,
                is_active=False,
                percentage=0,
                duration_minutes=120,
                segmentation_type=SegmentationType.RANDOM,
                target_cohort_ids=None,
                created_by_id=publisher.id,
                completed_at=now,
            )
        )
        counters["canary_configs_created"] += 1


def ensure_job_post_and_application(
    db,
    *,
    job_content: Content,
    employer: User,
    student: User,
    counters: dict,
) -> None:
    job_post = db.scalar(select(JobPost).where(JobPost.content_id == job_content.id))
    if job_post:
        job_post.created_by_id = employer.id
        job_post.is_active = True
        job_post.employer_name = "MeritForge Demo Employer"
        counters["job_posts_updated"] += 1
    else:
        job_post = JobPost(
            content_id=job_content.id,
            created_by_id=employer.id,
            employer_name="MeritForge Demo Employer",
            location="Remote",
            employment_type="full_time",
            requirements="Portfolio and collaborative communication",
            benefits="Mentorship and growth plan",
            is_active=True,
        )
        db.add(job_post)
        db.flush()
        counters["job_posts_created"] += 1

    application = db.scalar(
        select(Application).where(
            Application.job_post_id == job_post.id,
            Application.applicant_id == student.id,
        )
    )
    if application:
        application.status = ApplicationStatus.SUBMITTED
        application.submitted_at = application.submitted_at or now_utc()
        counters["applications_updated"] += 1
    else:
        db.add(
            Application(
                job_post_id=job_post.id,
                applicant_id=student.id,
                status=ApplicationStatus.SUBMITTED,
                cover_letter="Seeded demo application for workspace walkthrough.",
                submitted_at=now_utc(),
            )
        )
        counters["applications_created"] += 1


def ensure_demo_cohort(db, admin_user: User, student: User, counters: dict) -> None:
    cohort = db.scalar(select(UserCohort).where(UserCohort.slug == "demo-career-cohort"))
    if cohort:
        cohort.name = "Demo Career Cohort"
        cohort.is_active = True
        cohort.is_admin_defined = True
        cohort.created_by_id = admin_user.id
        counters["cohorts_updated"] += 1
    else:
        cohort = UserCohort(
            name="Demo Career Cohort",
            slug="demo-career-cohort",
            description="Seeded cohort for annotation visibility demo",
            created_by_id=admin_user.id,
            is_admin_defined=True,
            is_active=True,
        )
        db.add(cohort)
        db.flush()
        counters["cohorts_created"] += 1

    if student not in cohort.members:
        cohort.members.append(student)
        counters["cohort_memberships_created"] += 1
