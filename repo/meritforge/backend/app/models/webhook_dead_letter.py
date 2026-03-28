from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WebhookDeadLetter(Base):
    __tablename__ = "webhook_dead_letters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    delivery_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("webhook_deliveries.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    webhook_config_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("webhook_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_webhook_dead_letters_event", "event_name", "created_at"),
    )
