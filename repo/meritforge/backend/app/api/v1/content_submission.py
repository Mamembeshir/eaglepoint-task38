import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, ContentStatus, ContentType, RoleType
from app.dependencies.auth import get_current_user
from app.models.content import Content
from app.models.content_version import ContentVersion
from app.models.content_risk_assessment import ContentRiskAssessment
from app.models.content_version import ContentVersion
from app.models.risk_dictionary import RiskDictionary
from app.models.risk_grade_rule import RiskGradeRule
from app.models.risk_severity_weight import RiskSeverityWeight
from app.models.review_decision import ReviewDecision
from app.models.review_workflow_stage import ReviewWorkflowStage
from app.models.user import User
from app.schemas.content_submission import (
    ContentCatalogItemOut,
    ContentSubmissionListItemOut,
    ContentSubmissionOut,
    ContentSubmissionRequest,
    ReviewCommentOut,
    ReviewStageSummaryOut,
    TriggeredWordOut,
)
from app.services.review_workflow_service import ensure_content_review_workflow
from app.services.publishing_service import is_user_in_canary

router = APIRouter(tags=["Content Submission"])


@router.get("/content", response_model=list[ContentCatalogItemOut])
def list_content_catalog(
    content_type: ContentType | None = Query(default=None, alias="type"),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ContentCatalogItemOut]:
    query = select(Content).outerjoin(ContentVersion, ContentVersion.id == Content.current_version_id).where(
        Content.status.in_([ContentStatus.PUBLISHED, ContentStatus.RETRACTED]),
        Content.published_at.is_not(None),
    )
    if content_type is not None:
        query = query.where(Content.content_type == content_type)
    normalized_q = q.strip().lower() if q else None
    if normalized_q:
        search_term = f"%{normalized_q}%"
        query = query.where(
            or_(
                Content.title.ilike(search_term),
                ContentVersion.body.ilike(search_term),
                cast(ContentVersion.metadata_json, String).ilike(search_term),
            )
        )

    rows = db.scalars(
        query.order_by(Content.published_at.desc(), Content.created_at.desc()).offset(offset).limit(limit)
    ).all()

    items: list[ContentCatalogItemOut] = []
    for row in rows:
        if row.status not in {ContentStatus.PUBLISHED, ContentStatus.RETRACTED} or row.published_at is None:
            continue
        canary = getattr(row, "canary_config", None)
        if canary and canary.is_enabled and canary.is_active:
            visible, _ = is_user_in_canary(db, row.id, current_user.id)
            if not visible:
                continue

        current_version = row.current_version
        metadata_json = current_version.metadata_json if current_version and current_version.metadata_json else {}
        if normalized_q:
            haystack = " ".join(
                [
                    row.title or "",
                    current_version.body if current_version and current_version.body else "",
                    str(metadata_json) if metadata_json else "",
                ]
            ).lower()
            if normalized_q not in haystack:
                continue
        media_url = metadata_json.get("media_url") if isinstance(metadata_json, dict) else None
        submission_metadata = metadata_json.get("submission_metadata") if isinstance(metadata_json, dict) else None
        summary_source = current_version.body if current_version else None
        summary = summary_source[:240].strip() if summary_source else None

        items.append(
            ContentCatalogItemOut(
                id=row.id,
                title=row.title,
                content_type=row.content_type,
                status=row.status,
                media_url=media_url,
                metadata=submission_metadata if isinstance(submission_metadata, dict) else (metadata_json if isinstance(metadata_json, dict) else None),
                summary=summary,
                retracted_at=row.retracted_at,
                retraction_notice="This content has been retracted." if row.retracted_at else None,
            )
        )

    return items


def _normalize_role_name(user: User) -> str | None:
    if user.role is None:
        return None
    return user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)


def _assert_submit_permission(content_type: ContentType, user: User) -> None:
    role_name = _normalize_role_name(user)
    if role_name is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role is required")

    if content_type in {ContentType.ARTICLE, ContentType.VIDEO}:
        allowed = {RoleType.CONTENT_AUTHOR.value, RoleType.SYSTEM_ADMINISTRATOR.value}
    else:
        allowed = {RoleType.EMPLOYER_MANAGER.value, RoleType.SYSTEM_ADMINISTRATOR.value}

    if role_name not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions for submission")


def _build_submission_text(payload: ContentSubmissionRequest) -> str:
    parts = [payload.title]
    if payload.body:
        parts.append(payload.body)
    if payload.media_url:
        parts.append(payload.media_url)
    if payload.metadata:
        parts.append(str(payload.metadata))
    return "\n".join(parts)


def _match_term(text: str, term: RiskDictionary) -> int:
    if term.is_regex:
        pattern = re.compile(term.term, re.IGNORECASE)
    else:
        pattern = re.compile(rf"\b{re.escape(term.term)}\b", re.IGNORECASE)
    return len(pattern.findall(text))


def _resolve_grade(score: int, rules: list[RiskGradeRule]) -> RiskGradeRule | None:
    for rule in rules:
        upper_ok = rule.max_score is None or score <= rule.max_score
        if score >= rule.min_score and upper_ok:
            return rule
    return None


def _compute_risk_policy(grade_rule: RiskGradeRule) -> tuple[bool, int]:
    blocked_until_final_approval = grade_rule.blocked_until_final_approval
    required_distinct_reviewers = max(1, grade_rule.required_distinct_reviewers)
    normalized_grade = grade_rule.grade.lower()
    if normalized_grade == "high":
        blocked_until_final_approval = True
    if normalized_grade == "medium":
        required_distinct_reviewers = max(2, required_distinct_reviewers)
    return blocked_until_final_approval, required_distinct_reviewers


def _generate_slug(title: str, db: Session) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "content"
    slug = base
    counter = 2
    while db.scalar(select(Content).where(Content.slug == slug)):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@router.post("/content/submissions", response_model=ContentSubmissionOut, status_code=status.HTTP_201_CREATED)
def submit_content(
    payload: ContentSubmissionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentSubmissionOut:
    _assert_submit_permission(payload.content_type, current_user)

    if payload.content_type in {ContentType.ARTICLE, ContentType.JOB_ANNOUNCEMENT} and not payload.body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Body is required for article/job announcement")
    if payload.content_type == ContentType.VIDEO and not payload.media_url:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="media_url is required for video")

    dictionary_entries = db.scalars(
        select(RiskDictionary).where(RiskDictionary.is_active.is_(True))
    ).all()
    if not dictionary_entries:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk dictionary is empty")

    severity_weights = db.scalars(select(RiskSeverityWeight)).all()
    if not severity_weights:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk severity weights are not configured")

    weight_by_severity = {row.severity.lower(): row.weight for row in severity_weights}

    grade_rules = db.scalars(select(RiskGradeRule).order_by(RiskGradeRule.min_score.asc())).all()
    if not grade_rules:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk grade rules are not configured")

    submission_text = _build_submission_text(payload)

    risk_score = 0
    triggering_words: list[dict] = []
    for term in dictionary_entries:
        severity_key = term.severity.lower()
        if severity_key not in weight_by_severity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing severity weight for '{term.severity}'",
            )

        match_count = _match_term(submission_text, term)
        if match_count <= 0:
            continue

        weight = weight_by_severity[severity_key]
        risk_score += match_count * weight
        triggering_words.append(
            {
                "term": term.term,
                "severity": term.severity,
                "weight": weight,
                "match_count": match_count,
            }
        )

        term.match_count = term.match_count + match_count
        term.last_matched_at = datetime.now(timezone.utc)

    grade_rule = _resolve_grade(risk_score, grade_rules)
    if grade_rule is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No risk grade rule matched computed score")

    blocked_until_final_approval, required_distinct_reviewers = _compute_risk_policy(grade_rule)

    slug = _generate_slug(payload.title, db)
    content = Content(
        title=payload.title,
        slug=slug,
        content_type=payload.content_type,
        status=ContentStatus.UNDER_REVIEW,
        author_id=current_user.id,
        is_locked=blocked_until_final_approval,
    )
    db.add(content)
    db.flush()

    version = ContentVersion(
        content_id=content.id,
        version_number=1,
        title=payload.title,
        body=payload.body,
        metadata_json={"media_url": payload.media_url, "submission_metadata": payload.metadata} if (payload.media_url or payload.metadata) else None,
        change_summary="Initial submission",
        created_by_id=current_user.id,
        is_published_version=False,
    )
    db.add(version)
    db.flush()

    content.current_version_id = version.id

    risk_assessment = ContentRiskAssessment(
        content_id=content.id,
        risk_score=risk_score,
        risk_grade=grade_rule.grade,
        triggering_words=triggering_words,
        blocked_until_final_approval=blocked_until_final_approval,
        required_distinct_reviewers=required_distinct_reviewers,
    )
    db.add(risk_assessment)
    ensure_content_review_workflow(db, content, created_by_id=current_user.id)

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="content_submission",
        entity_id=str(content.id),
        actor=current_user,
        request=request,
        after_data={
            "content_type": payload.content_type.value,
            "risk_score": risk_score,
            "risk_grade": grade_rule.grade,
            "blocked_until_final_approval": blocked_until_final_approval,
            "required_distinct_reviewers": required_distinct_reviewers,
            "triggering_words": triggering_words,
        },
        description="Submitted content with risk assessment",
    )

    db.commit()
    db.refresh(content)
    db.refresh(version)

    return ContentSubmissionOut(
        content_id=content.id,
        version_id=version.id,
        content_type=content.content_type,
        status=content.status,
        risk_score=risk_assessment.risk_score,
        risk_grade=risk_assessment.risk_grade,
        blocked_until_final_approval=risk_assessment.blocked_until_final_approval,
        required_distinct_reviewers=risk_assessment.required_distinct_reviewers,
        triggering_words=[TriggeredWordOut(**item) for item in risk_assessment.triggering_words],
        created_at=content.created_at,
    )


@router.get("/content/submissions/mine", response_model=list[ContentSubmissionListItemOut])
def list_my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ContentSubmissionListItemOut]:
    rows = db.scalars(
        select(Content)
        .where(Content.author_id == current_user.id)
        .order_by(Content.created_at.desc())
    ).all()

    results: list[ContentSubmissionListItemOut] = []
    for row in rows:
        assessment = db.scalar(select(ContentRiskAssessment).where(ContentRiskAssessment.content_id == row.id))

        stage_rows = db.scalars(
            select(ReviewWorkflowStage).where(ReviewWorkflowStage.content_id == row.id)
        ).all()
        comments: list[ReviewCommentOut] = []
        for stage in stage_rows:
            decisions = db.scalars(
                select(ReviewDecision)
                .where(ReviewDecision.stage_id == stage.id)
                .order_by(ReviewDecision.created_at.desc())
            ).all()
            for decision in decisions:
                comments.append(
                    ReviewCommentOut(
                        stage_name=stage.stage_name,
                        decision=decision.decision,
                        reviewer_id=decision.reviewer_id,
                        comments=decision.comments,
                        created_at=decision.created_at,
                    )
                )

        results.append(
            ContentSubmissionListItemOut(
                content_id=row.id,
                title=row.title,
                content_type=row.content_type,
                status=row.status,
                risk_score=assessment.risk_score if assessment else None,
                risk_grade=assessment.risk_grade if assessment else None,
                workflow_stage_count=len(stage_rows),
                stages=[
                    ReviewStageSummaryOut(
                        stage_name=stage.stage_name,
                        stage_order=stage.stage_order,
                        is_required=stage.is_required,
                        is_parallel=stage.is_parallel,
                        is_completed=stage.is_completed,
                    )
                    for stage in stage_rows
                ],
                review_comments=comments,
                created_at=row.created_at,
            )
        )

    return results
