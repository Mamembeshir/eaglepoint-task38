from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, RoleType
from app.dependencies.auth import (
    get_current_user,
    require_roles,
    require_step_up_for_account_deletion,
    require_step_up_for_permission_changes,
)
from app.models.user import User
from app.models.user_cohort import UserCohort
from app.services.user_deletion_service import process_due_user_hard_deletions
from app.schemas.user_management import (
    CohortCreateRequest,
    CohortOut,
    DeletionStatusOut,
    ExportUserDataOut,
    ImportUserDataRequest,
    MarkDeletionRequest,
    ProcessDeletionResult,
    UserProfileOut,
    UserProfileUpdateRequest,
)

router = APIRouter(tags=["User Management"])


def _is_admin(user: User) -> bool:
    if user.role is None:
        return False
    role_name = user.role.name.value if hasattr(user.role.name, "value") else str(user.role.name)
    return role_name == RoleType.SYSTEM_ADMINISTRATOR.value


def _profile_payload(target: User, viewer: User) -> UserProfileOut:
    is_self = target.id == viewer.id
    show_contact = is_self or target.consent_contact_info_visible
    show_photo = is_self or target.consent_photo_visible

    return UserProfileOut(
        id=target.id,
        email=target.email if show_contact else None,
        first_name=target.first_name,
        last_name=target.last_name,
        display_name=target.display_name,
        bio=target.bio,
        avatar_url=target.avatar_url if show_photo else None,
        phone_number=target.phone_number if show_contact else None,
        consent_contact_info_visible=target.consent_contact_info_visible,
        consent_photo_visible=target.consent_photo_visible,
        consent_analytics=target.consent_analytics,
        consent_data_portability=target.consent_data_portability,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )


@router.get("/users/me", response_model=UserProfileOut)
def get_my_profile(current_user: User = Depends(get_current_user)) -> UserProfileOut:
    return _profile_payload(current_user, current_user)


@router.get("/users/{user_id}", response_model=UserProfileOut)
def get_user_profile(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> UserProfileOut:
    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _profile_payload(user, current_user)


@router.patch("/users/me", response_model=UserProfileOut)
def update_my_profile(
    payload: UserProfileUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileOut:
    before = {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "phone_number": current_user.phone_number,
        "consent_contact_info_visible": current_user.consent_contact_info_visible,
        "consent_photo_visible": current_user.consent_photo_visible,
        "consent_analytics": current_user.consent_analytics,
        "consent_data_portability": current_user.consent_data_portability,
    }

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    after = {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "phone_number": current_user.phone_number,
        "consent_contact_info_visible": current_user.consent_contact_info_visible,
        "consent_photo_visible": current_user.consent_photo_visible,
        "consent_analytics": current_user.consent_analytics,
        "consent_data_portability": current_user.consent_data_portability,
    }

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="user_profile",
        entity_id=str(current_user.id),
        actor=current_user,
        request=request,
        before_data=before,
        after_data=after,
        changes=update_data,
        description="Updated user profile and consent visibility settings",
    )
    db.commit()
    db.refresh(current_user)

    return _profile_payload(current_user, current_user)


@router.post("/users/me/import", response_model=UserProfileOut)
def import_my_data(
    payload: ImportUserDataRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileOut:
    before = {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "phone_number": current_user.phone_number,
        "consent_contact_info_visible": current_user.consent_contact_info_visible,
        "consent_photo_visible": current_user.consent_photo_visible,
        "consent_analytics": current_user.consent_analytics,
        "consent_data_portability": current_user.consent_data_portability,
    }

    update_data = payload.user.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    after = {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "phone_number": current_user.phone_number,
        "consent_contact_info_visible": current_user.consent_contact_info_visible,
        "consent_photo_visible": current_user.consent_photo_visible,
        "consent_analytics": current_user.consent_analytics,
        "consent_data_portability": current_user.consent_data_portability,
    }

    write_audit_log(
        db,
        action=AuditAction.IMPORT,
        entity_type="user_data_import",
        entity_id=str(current_user.id),
        actor=current_user,
        request=request,
        before_data=before,
        after_data={"source": payload.source, **after},
        changes=update_data,
        description="Imported user profile and privacy consent data",
    )
    db.commit()
    db.refresh(current_user)

    return _profile_payload(current_user, current_user)


@router.post("/cohorts", response_model=CohortOut, status_code=status.HTTP_201_CREATED)
def create_cohort(
    payload: CohortCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CohortOut:
    if payload.is_admin_defined and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create admin-defined cohorts")

    existing = db.scalar(select(UserCohort).where(UserCohort.slug == payload.slug))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cohort slug already exists")

    cohort = UserCohort(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        is_admin_defined=payload.is_admin_defined,
        created_by_id=current_user.id,
    )
    db.add(cohort)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="cohort",
        entity_id=str(cohort.id),
        actor=current_user,
        request=request,
        after_data={
            "name": payload.name,
            "slug": payload.slug,
            "is_admin_defined": payload.is_admin_defined,
        },
        description="Created cohort",
    )

    db.commit()
    db.refresh(cohort)

    return CohortOut(
        id=cohort.id,
        name=cohort.name,
        slug=cohort.slug,
        description=cohort.description,
        is_active=cohort.is_active,
        is_admin_defined=cohort.is_admin_defined,
        created_by_id=cohort.created_by_id,
        created_at=cohort.created_at,
    )


@router.post("/cohorts/{cohort_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_user_to_cohort(
    cohort_id: UUID,
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_step_up_for_permission_changes),
) -> None:
    cohort = db.scalar(select(UserCohort).where(UserCohort.id == cohort_id, UserCohort.is_active.is_(True)))
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    if not _is_admin(current_user) and cohort.created_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to modify this cohort")

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user not in cohort.members:
        cohort.members.append(user)
        write_audit_log(
            db,
            action=AuditAction.UPDATE,
            entity_type="cohort_membership",
            entity_id=f"{cohort_id}:{user_id}",
            actor=current_user,
            request=request,
            after_data={"cohort_id": str(cohort_id), "user_id": str(user_id), "operation": "assign"},
            description="Assigned user to cohort",
        )
        db.commit()


@router.delete("/cohorts/{cohort_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_cohort(
    cohort_id: UUID,
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_step_up_for_permission_changes),
) -> None:
    cohort = db.scalar(select(UserCohort).where(UserCohort.id == cohort_id, UserCohort.is_active.is_(True)))
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")

    if not _is_admin(current_user) and cohort.created_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to modify this cohort")

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user in cohort.members:
        cohort.members.remove(user)
        write_audit_log(
            db,
            action=AuditAction.UPDATE,
            entity_type="cohort_membership",
            entity_id=f"{cohort_id}:{user_id}",
            actor=current_user,
            request=request,
            before_data={"cohort_id": str(cohort_id), "user_id": str(user_id), "operation": "assigned"},
            after_data={"cohort_id": str(cohort_id), "user_id": str(user_id), "operation": "removed"},
            description="Removed user from cohort",
        )
        db.commit()


@router.get("/users/me/export", response_model=ExportUserDataOut)
def export_my_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExportUserDataOut:
    cohort_payload = [{"id": str(c.id), "name": c.name, "slug": c.slug} for c in current_user.cohorts]
    export_payload = {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "display_name": current_user.display_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "phone_number": current_user.phone_number,
        "consent_contact_info_visible": current_user.consent_contact_info_visible,
        "consent_photo_visible": current_user.consent_photo_visible,
        "consent_analytics": current_user.consent_analytics,
        "consent_data_portability": current_user.consent_data_portability,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat(),
    }

    write_audit_log(
        db,
        action=AuditAction.EXPORT,
        entity_type="user_data_export",
        entity_id=str(current_user.id),
        actor=current_user,
        request=request,
        after_data={"exported_fields": list(export_payload.keys())},
        description="Exported user data as JSON",
    )
    db.commit()

    return ExportUserDataOut(exported_at=datetime.now(timezone.utc), user=export_payload, cohorts=cohort_payload)


@router.post("/users/me/deletion/mark", response_model=DeletionStatusOut)
def mark_my_account_for_deletion(
    payload: MarkDeletionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_step_up_for_account_deletion),
) -> DeletionStatusOut:
    now = datetime.now(timezone.utc)
    current_user.is_marked_for_deletion = True
    current_user.deletion_requested_at = now
    current_user.scheduled_deletion_at = now + timedelta(days=30)
    current_user.deletion_reason = payload.reason

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="account_deletion",
        entity_id=str(current_user.id),
        actor=current_user,
        request=request,
        after_data={
            "is_marked_for_deletion": True,
            "deletion_requested_at": current_user.deletion_requested_at.isoformat(),
            "scheduled_deletion_at": current_user.scheduled_deletion_at.isoformat(),
            "reason": payload.reason,
        },
        description="Marked account for hard deletion",
    )
    db.commit()

    return DeletionStatusOut(
        user_id=current_user.id,
        is_marked_for_deletion=current_user.is_marked_for_deletion,
        deletion_requested_at=current_user.deletion_requested_at,
        scheduled_deletion_at=current_user.scheduled_deletion_at,
        reason=current_user.deletion_reason,
    )


@router.post("/users/deletion/process-due", response_model=ProcessDeletionResult)
def process_due_hard_deletions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> ProcessDeletionResult:
    deleted_ids = process_due_user_hard_deletions(
        db,
        actor=current_user,
        request=request,
        source="admin_endpoint",
    )

    db.commit()
    return ProcessDeletionResult(deleted_count=len(deleted_ids), deleted_user_ids=deleted_ids)
