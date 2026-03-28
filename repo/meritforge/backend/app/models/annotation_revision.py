from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnnotationRevision(Base):
    __tablename__ = "annotation_revisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    annotation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annotations.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_annotation_revisions_annotation_revision", "annotation_id", "revision_number"),
    )
