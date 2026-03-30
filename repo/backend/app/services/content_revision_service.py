import copy
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ContentStatus, ContentType
from app.models.content import Content
from app.models.content_risk_assessment import ContentRiskAssessment
from app.models.content_version import ContentVersion
from app.models.review_decision import ReviewDecision
from app.models.review_workflow_stage import ReviewWorkflowStage
from app.services.review_workflow_service import ensure_content_review_workflow


class ContentRevisionService:
    @staticmethod
    def create_revision(
        db: Session,
        *,
        content: Content,
        actor_id,
        title: str | None,
        body: str | None,
        media_url: str | None,
        metadata: dict | None,
        change_summary: str,
    ) -> tuple[ContentVersion, int]:
        if content.status != ContentStatus.NEEDS_REVISION:
            raise ValueError("Content must be in needs_revision status before creating a revision")

        current_version = db.scalar(select(ContentVersion).where(ContentVersion.id == content.current_version_id))
        if not current_version:
            raise ValueError("Current content version not found")

        revised_title = (title or content.title).strip()
        revised_body = body if body is not None else current_version.body

        metadata_json = copy.deepcopy(current_version.metadata_json) if current_version.metadata_json else {}
        if media_url is not None:
            metadata_json["media_url"] = media_url
        if metadata is not None:
            metadata_json["submission_metadata"] = metadata
        if not metadata_json:
            metadata_json = None

        if content.content_type in {ContentType.ARTICLE, ContentType.JOB_ANNOUNCEMENT} and not (revised_body and revised_body.strip()):
            raise ValueError("Body is required for article/job announcement revisions")
        if content.content_type == ContentType.VIDEO:
            resolved_media_url = None
            if isinstance(metadata_json, dict):
                resolved_media_url = metadata_json.get("media_url")
            if not resolved_media_url:
                raise ValueError("media_url is required for video revisions")

        latest_version_number = db.scalar(
            select(func.max(ContentVersion.version_number)).where(ContentVersion.content_id == content.id)
        )
        next_version_number = int(latest_version_number or 0) + 1

        version = ContentVersion(
            content_id=content.id,
            version_number=next_version_number,
            title=revised_title,
            body=revised_body,
            metadata_json=metadata_json,
            change_summary=change_summary,
            created_by_id=actor_id,
            is_published_version=False,
        )
        db.add(version)
        db.flush()

        old_stages = db.scalars(select(ReviewWorkflowStage).where(ReviewWorkflowStage.content_id == content.id)).all()
        old_stage_ids = [stage.id for stage in old_stages]
        if old_stage_ids:
            old_decisions = db.scalars(select(ReviewDecision).where(ReviewDecision.stage_id.in_(old_stage_ids))).all()
            for decision in old_decisions:
                db.delete(decision)
            db.flush()

        for stage in old_stages:
            db.delete(stage)
        db.flush()

        new_stages, _ = ensure_content_review_workflow(db, content, created_by_id=actor_id)

        content.title = revised_title
        content.current_version_id = version.id
        content.status = ContentStatus.UNDER_REVIEW
        content.updated_at = datetime.now(timezone.utc)

        risk_assessment = db.scalar(select(ContentRiskAssessment).where(ContentRiskAssessment.content_id == content.id))
        if risk_assessment:
            content.is_locked = risk_assessment.blocked_until_final_approval

        return version, len(new_stages)
