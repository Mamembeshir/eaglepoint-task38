from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Content
from app.models.review_workflow_stage import ReviewWorkflowStage
from app.models.review_workflow_template_stage import ReviewWorkflowTemplateStage


DEFAULT_TEMPLATE_STAGES = [
    {
        "stage_name": "Initial Review",
        "stage_order": 1,
        "description": "First-pass review for content quality and policy fit.",
        "is_required": True,
        "is_parallel": False,
    },
    {
        "stage_name": "Secondary Review",
        "stage_order": 2,
        "description": "Secondary review for quality, policy, and consistency.",
        "is_required": True,
        "is_parallel": False,
    },
    {
        "stage_name": "Final Review",
        "stage_order": 3,
        "description": "Final approval before publishing decisions can proceed.",
        "is_required": True,
        "is_parallel": False,
    },
]


def ensure_active_template_stages(db: Session, created_by_id=None) -> list[ReviewWorkflowTemplateStage]:
    template_stages = db.scalars(
        select(ReviewWorkflowTemplateStage)
        .where(ReviewWorkflowTemplateStage.is_active.is_(True))
        .order_by(ReviewWorkflowTemplateStage.stage_order.asc(), ReviewWorkflowTemplateStage.created_at.asc())
    ).all()
    if template_stages:
        return template_stages

    seeded: list[ReviewWorkflowTemplateStage] = []
    for item in DEFAULT_TEMPLATE_STAGES:
        stage = ReviewWorkflowTemplateStage(created_by_id=created_by_id, **item)
        db.add(stage)
        seeded.append(stage)
    db.flush()
    return seeded


def ensure_content_review_workflow(db: Session, content: Content, created_by_id=None) -> tuple[list[ReviewWorkflowStage], bool]:
    existing = db.scalars(
        select(ReviewWorkflowStage)
        .where(ReviewWorkflowStage.content_id == content.id)
        .order_by(ReviewWorkflowStage.stage_order.asc(), ReviewWorkflowStage.created_at.asc())
    ).all()
    if existing:
        return existing, False

    template_stages = ensure_active_template_stages(db, created_by_id=created_by_id)
    created: list[ReviewWorkflowStage] = []
    for template_stage in template_stages:
        stage = ReviewWorkflowStage(
            content_id=content.id,
            stage_name=template_stage.stage_name,
            stage_order=template_stage.stage_order,
            description=template_stage.description,
            is_required=template_stage.is_required,
            is_parallel=template_stage.is_parallel,
        )
        db.add(stage)
        created.append(stage)
    db.flush()
    return created, True
