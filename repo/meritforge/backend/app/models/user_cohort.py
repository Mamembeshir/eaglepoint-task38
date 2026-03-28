from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


user_cohort_memberships = Table(
    "user_cohort_memberships",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("cohort_id", ForeignKey("user_cohorts.id", ondelete="CASCADE"), primary_key=True),
    Column("joined_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


class UserCohort(Base):
    __tablename__ = "user_cohorts"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_admin_defined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    members: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_cohort_memberships,
        back_populates="cohorts"
    )

    __table_args__ = (
        Index("ix_user_cohorts_name_active", "name", "is_active"),
        Index("ix_user_cohorts_slug_active", "slug", "is_active"),
        Index("ix_user_cohorts_updated_at", "updated_at"),
        Index("ix_user_cohorts_created_by", "created_by_id", "is_admin_defined"),
    )

    def __repr__(self) -> str:
        return f"<UserCohort(id={self.id}, name={self.name})>"
