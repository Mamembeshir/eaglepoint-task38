from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AnnotationVisibility, AuditAction
from app.dependencies.auth import get_current_user
from app.models.annotation import Annotation
from app.models.annotation_revision import AnnotationRevision
from app.models.content import Content
from app.models.user import User
from app.schemas.engagement import AnnotationCreateRequest, AnnotationOut, AnnotationUpdateRequest

router = APIRouter(tags=["Engagement"])


def _annotation_visible_to_user(annotation: Annotation, user: User) -> bool:
    if annotation.author_id == user.id:
        return True
    if annotation.visibility == AnnotationVisibility.PUBLIC:
        return True
    if annotation.visibility == AnnotationVisibility.PRIVATE:
        return False
    if annotation.visibility == AnnotationVisibility.COHORT:
        if not annotation.cohort_id:
            return False
        user_cohort_ids = {c.id for c in user.cohorts}
        return annotation.cohort_id in user_cohort_ids
    return False


def _annotation_source_text(content: Content) -> str:
    version = content.current_version
    if version and version.body:
        return version.body

    metadata_json = version.metadata_json if version and isinstance(version.metadata_json, dict) else {}
    transcript = metadata_json.get("transcript") or metadata_json.get("transcript_text")
    if isinstance(transcript, str) and transcript.strip():
        return transcript

    submission_metadata = metadata_json.get("submission_metadata")
    if isinstance(submission_metadata, dict):
        nested_transcript = submission_metadata.get("transcript") or submission_metadata.get("summary")
        if isinstance(nested_transcript, str) and nested_transcript.strip():
            return nested_transcript

    summary = metadata_json.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary

    return ""


@router.post("/annotations", response_model=AnnotationOut, status_code=status.HTTP_201_CREATED)
def create_annotation(
    payload: AnnotationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnotationOut:
    if payload.end_offset <= payload.start_offset:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="end_offset must be > start_offset")

    if payload.visibility == AnnotationVisibility.COHORT and not payload.cohort_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cohort visibility requires cohort_id")

    content = db.scalar(select(Content).where(Content.id == payload.content_id))
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    source_text = _annotation_source_text(content)
    if not source_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No annotation source text available for this content")
    if payload.end_offset > len(source_text):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Annotation range is outside content text length")
    if payload.highlighted_text is not None:
        expected = source_text[payload.start_offset:payload.end_offset]
        if payload.highlighted_text != expected:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="highlighted_text does not match provided offsets")

    annotation = Annotation(
        content_id=payload.content_id,
        author_id=current_user.id,
        visibility=payload.visibility,
        cohort_id=payload.cohort_id,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        highlighted_text=payload.highlighted_text,
        annotation_text=payload.annotation_text,
        color=payload.color,
        tags=payload.tags,
        version=1,
    )
    db.add(annotation)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="annotation",
        entity_id=str(annotation.id),
        actor=current_user,
        request=request,
        after_data={
            "content_id": str(annotation.content_id),
            "visibility": annotation.visibility.value if hasattr(annotation.visibility, "value") else str(annotation.visibility),
            "cohort_id": str(annotation.cohort_id) if annotation.cohort_id else None,
        },
        description="Created annotation",
    )
    db.commit()

    return AnnotationOut(
        id=annotation.id,
        content_id=annotation.content_id,
        author_id=annotation.author_id,
        visibility=annotation.visibility,
        cohort_id=annotation.cohort_id,
        start_offset=annotation.start_offset,
        end_offset=annotation.end_offset,
        highlighted_text=annotation.highlighted_text,
        annotation_text=annotation.annotation_text,
        color=annotation.color,
        tags=annotation.tags,
        updated_at=annotation.updated_at,
        version=annotation.version,
    )


@router.get("/contents/{content_id}/annotations", response_model=list[AnnotationOut])
def list_visible_annotations(
    content_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnnotationOut]:
    annotations = db.scalars(select(Annotation).where(Annotation.content_id == content_id)).all()
    visible = [a for a in annotations if _annotation_visible_to_user(a, current_user)]
    return [
        AnnotationOut(
            id=a.id,
            content_id=a.content_id,
            author_id=a.author_id,
            visibility=a.visibility,
            cohort_id=a.cohort_id,
            start_offset=a.start_offset,
            end_offset=a.end_offset,
            highlighted_text=a.highlighted_text,
            annotation_text=a.annotation_text,
            color=a.color,
            tags=a.tags,
            updated_at=a.updated_at,
            version=a.version,
        )
        for a in visible
    ]


@router.patch("/annotations/{annotation_id}", response_model=AnnotationOut)
def update_annotation_latest_wins(
    annotation_id: UUID,
    payload: AnnotationUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnnotationOut:
    annotation = db.scalar(select(Annotation).where(Annotation.id == annotation_id))
    if not annotation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    if annotation.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only author can update annotation")

    previous_data = {
        "visibility": annotation.visibility.value if hasattr(annotation.visibility, "value") else str(annotation.visibility),
        "cohort_id": str(annotation.cohort_id) if annotation.cohort_id else None,
        "annotation_text": annotation.annotation_text,
        "color": annotation.color,
        "tags": annotation.tags,
        "updated_at": annotation.updated_at.isoformat(),
        "version": annotation.version,
    }
    db.add(
        AnnotationRevision(
            annotation_id=annotation.id,
            revision_number=annotation.version,
            previous_data=previous_data,
            changed_by_id=current_user.id,
        )
    )

    updates = payload.model_dump(exclude_unset=True)
    updates.pop("client_updated_at", None)
    if "visibility" in updates and updates["visibility"] == AnnotationVisibility.COHORT and not updates.get("cohort_id") and not annotation.cohort_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="cohort visibility requires cohort_id")

    for key, value in updates.items():
        setattr(annotation, key, value)
    annotation.version += 1

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="annotation",
        entity_id=str(annotation.id),
        actor=current_user,
        request=request,
        before_data=previous_data,
        after_data={
            "visibility": annotation.visibility.value if hasattr(annotation.visibility, "value") else str(annotation.visibility),
            "cohort_id": str(annotation.cohort_id) if annotation.cohort_id else None,
            "annotation_text": annotation.annotation_text,
            "color": annotation.color,
            "tags": annotation.tags,
            "version": annotation.version,
        },
        changes=updates,
        description="Updated annotation using latest-update-wins policy",
    )
    db.commit()

    return AnnotationOut(
        id=annotation.id,
        content_id=annotation.content_id,
        author_id=annotation.author_id,
        visibility=annotation.visibility,
        cohort_id=annotation.cohort_id,
        start_offset=annotation.start_offset,
        end_offset=annotation.end_offset,
        highlighted_text=annotation.highlighted_text,
        annotation_text=annotation.annotation_text,
        color=annotation.color,
        tags=annotation.tags,
        updated_at=annotation.updated_at,
        version=annotation.version,
    )
