from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, ForeignKey, func, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base
from app.core.enums import AnnotationVisibility

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.content import Content
    from app.models.user_cohort import UserCohort


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    visibility: Mapped[AnnotationVisibility] = mapped_column(
        SQLEnum(
            AnnotationVisibility,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=True,
        ),
        default=AnnotationVisibility.PRIVATE,
        nullable=False,
        index=True
    )
    
    cohort_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("user_cohorts.id", ondelete="SET NULL"),
        nullable=True
    )
    
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    
    highlighted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    annotation_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    
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
    
    content: Mapped["Content"] = relationship("Content", back_populates="annotations")
    author: Mapped["User"] = relationship("User", back_populates="annotations")
    cohort: Mapped[Optional["UserCohort"]] = relationship("UserCohort")

    __table_args__ = (
        Index("ix_annotations_content_visibility", "content_id", "visibility"),
        Index("ix_annotations_author_visibility", "author_id", "visibility"),
        Index("ix_annotations_cohort", "cohort_id", "visibility"),
        Index("ix_annotations_offsets", "content_id", "start_offset", "end_offset"),
    )

    def __repr__(self) -> str:
        return f"<Annotation(id={self.id}, visibility={self.visibility})>"
