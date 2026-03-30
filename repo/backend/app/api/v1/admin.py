from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.database import get_db
from app.core.enums import AuditAction, RoleType
from app.dependencies.auth import require_roles
from app.models.risk_dictionary import RiskDictionary
from app.models.user import User
from app.models.user_cohort import UserCohort
from app.schemas.admin import (
    CohortMemberOut,
    CohortWithMembersOut,
    RiskDictionaryCreateRequest,
    RiskDictionaryOut,
    RiskDictionaryUpdateRequest,
)

router = APIRouter(tags=["Admin"])


@router.get("/admin/risk-dictionary", response_model=list[RiskDictionaryOut])
def list_risk_dictionary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> list[RiskDictionaryOut]:
    rows = db.scalars(select(RiskDictionary).order_by(RiskDictionary.created_at.desc())).all()
    return [
        RiskDictionaryOut(
            id=r.id,
            term=r.term,
            category=r.category,
            severity=r.severity,
            description=r.description,
            replacement_suggestion=r.replacement_suggestion,
            is_active=r.is_active,
            is_regex=r.is_regex,
            match_count=r.match_count,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/admin/risk-dictionary", response_model=RiskDictionaryOut, status_code=status.HTTP_201_CREATED)
def create_risk_dictionary_entry(
    payload: RiskDictionaryCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> RiskDictionaryOut:
    existing = db.scalar(select(RiskDictionary).where(RiskDictionary.term == payload.term))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Risk term already exists")

    row = RiskDictionary(
        term=payload.term,
        category=payload.category,
        severity=payload.severity,
        description=payload.description,
        replacement_suggestion=payload.replacement_suggestion,
        is_regex=payload.is_regex,
        created_by_id=current_user.id,
    )
    db.add(row)
    db.flush()

    write_audit_log(
        db,
        action=AuditAction.CREATE,
        entity_type="risk_dictionary",
        entity_id=str(row.id),
        actor=current_user,
        request=request,
        after_data={"term": row.term, "severity": row.severity, "category": row.category},
        description="Created risk dictionary entry",
    )
    db.commit()

    return RiskDictionaryOut(
        id=row.id,
        term=row.term,
        category=row.category,
        severity=row.severity,
        description=row.description,
        replacement_suggestion=row.replacement_suggestion,
        is_active=row.is_active,
        is_regex=row.is_regex,
        match_count=row.match_count,
        created_at=row.created_at,
    )


@router.patch("/admin/risk-dictionary/{risk_id}", response_model=RiskDictionaryOut)
def update_risk_dictionary_entry(
    risk_id: UUID,
    payload: RiskDictionaryUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> RiskDictionaryOut:
    row = db.scalar(select(RiskDictionary).where(RiskDictionary.id == risk_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk term not found")

    before = {
        "term": row.term,
        "category": row.category,
        "severity": row.severity,
        "description": row.description,
        "replacement_suggestion": row.replacement_suggestion,
        "is_active": row.is_active,
        "is_regex": row.is_regex,
    }

    updates = payload.model_dump(exclude_unset=True)
    updated_term = updates.get("term")
    if updated_term and updated_term != row.term:
        duplicate = db.scalar(select(RiskDictionary).where(RiskDictionary.term == updated_term, RiskDictionary.id != row.id))
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Risk term already exists")
    for key, value in updates.items():
        setattr(row, key, value)

    write_audit_log(
        db,
        action=AuditAction.UPDATE,
        entity_type="risk_dictionary",
        entity_id=str(row.id),
        actor=current_user,
        request=request,
        before_data=before,
        after_data={
            "term": row.term,
            "category": row.category,
            "severity": row.severity,
            "description": row.description,
            "replacement_suggestion": row.replacement_suggestion,
            "is_active": row.is_active,
            "is_regex": row.is_regex,
        },
        description="Updated risk dictionary entry",
    )
    db.commit()

    return RiskDictionaryOut(
        id=row.id,
        term=row.term,
        category=row.category,
        severity=row.severity,
        description=row.description,
        replacement_suggestion=row.replacement_suggestion,
        is_active=row.is_active,
        is_regex=row.is_regex,
        match_count=row.match_count,
        created_at=row.created_at,
    )


@router.delete("/admin/risk-dictionary/{risk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_risk_dictionary_entry(
    risk_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> None:
    row = db.scalar(select(RiskDictionary).where(RiskDictionary.id == risk_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk term not found")

    before = {
        "term": row.term,
        "category": row.category,
        "severity": row.severity,
        "is_regex": row.is_regex,
        "is_active": row.is_active,
    }

    write_audit_log(
        db,
        action=AuditAction.DELETE,
        entity_type="risk_dictionary",
        entity_id=str(row.id),
        actor=current_user,
        request=request,
        before_data=before,
        description="Deleted risk dictionary entry",
    )
    db.delete(row)
    db.commit()


@router.get("/admin/cohorts", response_model=list[CohortWithMembersOut])
def list_cohorts_with_members(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleType.SYSTEM_ADMINISTRATOR)),
) -> list[CohortWithMembersOut]:
    rows = db.scalars(select(UserCohort).order_by(UserCohort.created_at.desc())).all()
    return [
        CohortWithMembersOut(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            is_admin_defined=c.is_admin_defined,
            is_active=c.is_active,
            created_at=c.created_at,
            members=[
                CohortMemberOut(id=m.id, email=m.email, display_name=m.display_name)
                for m in c.members
            ],
        )
        for c in rows
    ]
