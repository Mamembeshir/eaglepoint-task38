from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
import uuid

from app.core.database import Base
from app.core.enums import RoleType

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[RoleType] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    users: Mapped[list["User"]] = relationship("User", back_populates="role")

    __table_args__ = (
        Index("ix_roles_name_active", "name", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"
