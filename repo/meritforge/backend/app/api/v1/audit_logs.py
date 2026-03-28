from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import RoleType
from app.dependencies.auth import require_roles
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_logs import AuditLogOut, AuditSearchResponse

router = APIRouter(tags=["Audit Logs"])


@router.get("/audit-logs", response_model=AuditSearchResponse)
def search_audit_logs(
    user_id: UUID | None = Query(default=None),
    user_email: str | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    ip_address: str | None = Query(default=None),
    q: str | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> AuditSearchResponse:
    filters = []
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action == action)
    if user_email:
        filters.append(AuditLog.user_email.ilike(f"%{user_email}%"))
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if ip_address:
        filters.append(AuditLog.ip_address == ip_address)
    if start_at:
        filters.append(AuditLog.created_at >= start_at)
    if end_at:
        filters.append(AuditLog.created_at <= end_at)
    if q:
        like = f"%{q}%"
        filters.append(
            (AuditLog.description.ilike(like))
            | (AuditLog.entity_type.ilike(like))
            | (AuditLog.entity_id.ilike(like))
            | (AuditLog.user_email.ilike(like))
        )

    base_query = select(AuditLog)
    count_query = select(func.count(AuditLog.id))
    if filters:
        condition = and_(*filters)
        base_query = base_query.where(condition)
        count_query = count_query.where(condition)

    total = db.scalar(count_query) or 0
    rows = db.scalars(
        base_query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return AuditSearchResponse(
        total=int(total),
        items=[
            AuditLogOut(
                id=row.id,
                action=row.action.value if hasattr(row.action, "value") else str(row.action),
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                user_id=row.user_id,
                user_email=row.user_email,
                ip_address=row.ip_address,
                before_data=row.before_data,
                after_data=row.after_data,
                changes=row.changes,
                description=row.description,
                request_url=row.request_url,
                request_method=row.request_method,
                created_at=row.created_at,
            )
            for row in rows
        ],
    )
