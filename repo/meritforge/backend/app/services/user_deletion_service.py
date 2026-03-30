from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.enums import AuditAction
from app.models.user import User


def process_due_user_hard_deletions(
    db: Session,
    *,
    actor: User | None,
    request=None,
    source: str,
) -> list[UUID]:
    now = datetime.now(timezone.utc)
    due_users = db.scalars(
        select(User).where(
            User.is_marked_for_deletion.is_(True),
            User.scheduled_deletion_at.is_not(None),
            User.scheduled_deletion_at <= now,
        )
    ).all()

    deleted_ids: list[UUID] = []
    for user in due_users:
        if user.legal_hold:
            write_audit_log(
                db,
                action=AuditAction.UPDATE,
                entity_type="account_deletion",
                entity_id=str(user.id),
                actor=actor,
                request=request,
                after_data={
                    "legal_hold": True,
                    "legal_hold_reason": user.legal_hold_reason,
                    "source": source,
                },
                description="Skipped hard deletion because legal hold is active",
            )
            continue

        deleted_ids.append(user.id)
        write_audit_log(
            db,
            action=AuditAction.DELETE,
            entity_type="user",
            entity_id=str(user.id),
            actor=actor,
            request=request,
            before_data={
                "email": user.email,
                "scheduled_deletion_at": user.scheduled_deletion_at.isoformat() if user.scheduled_deletion_at else None,
                "source": source,
            },
            description="Hard deleted user after 30-day retention period",
        )
        db.delete(user)

    return deleted_ids
