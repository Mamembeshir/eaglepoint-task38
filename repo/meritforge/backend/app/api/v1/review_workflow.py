from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, ContentStatus, ReviewDecisionType, RoleType
from app.dependencies.auth import get_current_user, require_roles
from app.models.content import Content
from app.models.content_risk_assessment import ContentRiskAssessment
from app.models.review_decision import ReviewDecision
from app.models.review_workflow_stage import ReviewWorkflowStage
from app.models.review_workflow_template_stage import ReviewWorkflowTemplateStage
from app.models.user import User
from app.schemas.review_workflow import (
    InitializeWorkflowResponse,
    ReviewDecisionOut,
    ReviewDecisionRequest,
    TemplateStageCreateRequest,
    TemplateStageOut,
)
from app.schemas.reviewer import ReviewerQueueItemOut

router = APIRouter(tags=["Review Workflow"])


def _role_name(user: User) -> str | None:
    if user.role is None:
        return None
    return user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)


def _is_reviewer(user: User) -> bool:
    role_name = _role_name(user)
    return role_name in {RoleType.REVIEWER.value, RoleType.SYSTEM_ADMINISTRATOR.value}


@router.get("/review-workflow/queue", response_model=list[ReviewerQueueItemOut])
def get_reviewer_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReviewerQueueItemOut]:
    if not _is_reviewer(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer role required")

    stages = db.scalars(
        select(ReviewWorkflowStage)
        .where(ReviewWorkflowStage.is_completed.is_(False), ReviewWorkflowStage.is_required.is_(True))
        .order_by(ReviewWorkflowStage.stage_order.asc(), ReviewWorkflowStage.updated_at.desc())
    ).all()

    items: list[ReviewerQueueItemOut] = []
    for stage in stages:
        content = db.scalar(select(Content).where(Content.id == stage.content_id))
        if not content:
            continue
        if content.status not in {ContentStatus.UNDER_REVIEW, ContentStatus.NEEDS_REVISION}:
            continue

        risk = db.scalar(select(ContentRiskAssessment).where(ContentRiskAssessment.content_id == content.id))
        required_reviewers = max(1, risk.required_distinct_reviewers if risk else 1)
        current_approvers = db.scalar(
            select(func.count(func.distinct(ReviewDecision.reviewer_id))).where(
                ReviewDecision.stage_id == stage.id,
                ReviewDecision.decision == ReviewDecisionType.APPROVE.value,
            )
        ) or 0

        latest = db.scalar(
            select(ReviewDecision)
            .where(ReviewDecision.stage_id == stage.id)
            .order_by(ReviewDecision.created_at.desc())
            .limit(1)
        )

        items.append(
            ReviewerQueueItemOut(
                stage_id=stage.id,
                content_id=content.id,
                title=content.title,
                content_type=content.content_type,
                status=content.status,
                stage_name=stage.stage_name,
                stage_order=stage.stage_order,
                is_parallel=stage.is_parallel,
                required_distinct_reviewers=required_reviewers,
                current_distinct_approvers=int(current_approvers),
                latest_comment=latest.comments if latest else None,
                updated_at=stage.updated_at,
            )
        )

    return items


@router.post("/review-workflow/templates/stages", response_model=TemplateStageOut, status_code=status.HTTP_201_CREATED)
def create_template_stage(
    payload: TemplateStageCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> TemplateStageOut:
    stage = ReviewWorkflowTemplateStage(
        stage_name=payload.stage_name,
        stage_order=payload.stage_order,
        description=payload.description,
        is_required=payload.is_required,
        is_parallel=payload.is_parallel,
        created_by_id=current_user.id,
    )
    db.add(stage)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="review_workflow_template_stage",
        entity_id=str(stage.id),
        actor=current_user,
        request=request,
        after_data={
            "stage_name": stage.stage_name,
            "stage_order": stage.stage_order,
            "is_required": stage.is_required,
            "is_parallel": stage.is_parallel,
        },
        description="Created review workflow template stage",
    )
    db.commit()

    return TemplateStageOut(
        id=stage.id,
        stage_name=stage.stage_name,
        stage_order=stage.stage_order,
        description=stage.description,
        is_required=stage.is_required,
        is_parallel=stage.is_parallel,
        is_active=stage.is_active,
        created_by_id=stage.created_by_id,
        created_at=stage.created_at,
    )


@router.get("/review-workflow/templates/stages", response_model=list[TemplateStageOut])
def list_template_stages(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> list[TemplateStageOut]:
    stages = db.scalars(
        select(ReviewWorkflowTemplateStage)
        .where(ReviewWorkflowTemplateStage.is_active.is_(True))
        .order_by(ReviewWorkflowTemplateStage.stage_order.asc(), ReviewWorkflowTemplateStage.created_at.asc())
    ).all()
    return [
        TemplateStageOut(
            id=s.id,
            stage_name=s.stage_name,
            stage_order=s.stage_order,
            description=s.description,
            is_required=s.is_required,
            is_parallel=s.is_parallel,
            is_active=s.is_active,
            created_by_id=s.created_by_id,
            created_at=s.created_at,
        )
        for s in stages
    ]


@router.post("/review-workflow/contents/{content_id}/initialize", response_model=InitializeWorkflowResponse)
def initialize_content_workflow(
    content_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> InitializeWorkflowResponse:
    content = db.scalar(select(Content).where(Content.id == content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    existing = db.scalar(select(func.count(ReviewWorkflowStage.id)).where(ReviewWorkflowStage.content_id == content.id))
    if existing and existing > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow already initialized for this content")

    template_stages = db.scalars(
        select(ReviewWorkflowTemplateStage)
        .where(ReviewWorkflowTemplateStage.is_active.is_(True))
        .order_by(ReviewWorkflowTemplateStage.stage_order.asc(), ReviewWorkflowTemplateStage.created_at.asc())
    ).all()
    if not template_stages:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active workflow template stages configured")

    for stage in template_stages:
        db.add(
            ReviewWorkflowStage(
                content_id=content.id,
                stage_name=stage.stage_name,
                stage_order=stage.stage_order,
                description=stage.description,
                is_required=stage.is_required,
                is_parallel=stage.is_parallel,
            )
        )

    content.status = ContentStatus.UNDER_REVIEW

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="review_workflow",
        entity_id=str(content.id),
        actor=current_user,
        request=request,
        after_data={
            "template_stage_count": len(template_stages),
            "content_status": ContentStatus.UNDER_REVIEW.value,
        },
        description="Initialized content review workflow from template",
    )
    db.commit()

    return InitializeWorkflowResponse(content_id=content.id, stages_created=len(template_stages), status=content.status)


@router.post("/review-workflow/stages/{stage_id}/decisions", response_model=ReviewDecisionOut)
def submit_review_decision(
    stage_id: UUID,
    payload: ReviewDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewDecisionOut:
    if not _is_reviewer(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer role required")

    stage = db.scalar(select(ReviewWorkflowStage).where(ReviewWorkflowStage.id == stage_id))
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review stage not found")

    content = db.scalar(select(Content).where(Content.id == stage.content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    if payload.decision == ReviewDecisionType.RETURN_FOR_REVISION:
        if not payload.comments or len(payload.comments.strip()) < 20:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Return for Revision requires comments with at least 20 characters",
            )

    lower_required_incomplete = db.scalar(
        select(func.count(ReviewWorkflowStage.id)).where(
            ReviewWorkflowStage.content_id == content.id,
            ReviewWorkflowStage.is_required.is_(True),
            ReviewWorkflowStage.is_completed.is_(False),
            ReviewWorkflowStage.stage_order < stage.stage_order,
        )
    )
    if lower_required_incomplete and lower_required_incomplete > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot decide this stage before completing prior required stages",
        )

    decision = ReviewDecision(
        stage_id=stage.id,
        reviewer_id=current_user.id,
        decision=payload.decision.value,
        comments=payload.comments,
        content_version_id=content.current_version_id,
    )
    db.add(decision)
    db.flush()

    required_distinct_reviewers = 1
    risk_assessment = db.scalar(select(ContentRiskAssessment).where(ContentRiskAssessment.content_id == content.id))
    if risk_assessment:
        required_distinct_reviewers = max(1, risk_assessment.required_distinct_reviewers)

    if payload.decision == ReviewDecisionType.APPROVE:
        distinct_approvers = db.scalar(
            select(func.count(func.distinct(ReviewDecision.reviewer_id))).where(
                ReviewDecision.stage_id == stage.id,
                ReviewDecision.decision == ReviewDecisionType.APPROVE.value,
            )
        )
        distinct_approvers = int(distinct_approvers or 0)

        if distinct_approvers >= required_distinct_reviewers:
            stage.is_completed = True
            stage.completed_at = datetime.now(timezone.utc)

        remaining_required = db.scalar(
            select(func.count(ReviewWorkflowStage.id)).where(
                ReviewWorkflowStage.content_id == content.id,
                ReviewWorkflowStage.is_required.is_(True),
                ReviewWorkflowStage.is_completed.is_(False),
            )
        )
        if remaining_required == 0:
            content.status = ContentStatus.APPROVED
        else:
            content.status = ContentStatus.UNDER_REVIEW

    elif payload.decision in {ReviewDecisionType.RETURN_FOR_REVISION, ReviewDecisionType.REJECT}:
        content.status = ContentStatus.NEEDS_REVISION
        stages_to_reset = db.scalars(
            select(ReviewWorkflowStage).where(ReviewWorkflowStage.content_id == content.id)
        ).all()
        for s in stages_to_reset:
            s.is_completed = False
            s.completed_at = None
        distinct_approvers = 0
    else:
        distinct_approvers = 0

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="review_decision",
        entity_id=str(decision.id),
        actor=current_user,
        request=request,
        after_data={
            "content_id": str(content.id),
            "stage_id": str(stage.id),
            "decision": payload.decision.value,
            "comments": payload.comments,
            "content_status": content.status.value,
            "required_distinct_reviewers": required_distinct_reviewers,
            "distinct_approvers": distinct_approvers,
            "stage_completed": stage.is_completed,
        },
        description="Submitted review decision",
    )
    db.commit()

    return ReviewDecisionOut(
        stage_id=stage.id,
        decision=payload.decision,
        content_status=content.status,
        stage_completed=stage.is_completed,
        required_distinct_reviewers=required_distinct_reviewers,
        distinct_approvers=distinct_approvers,
        created_at=decision.created_at,
    )
