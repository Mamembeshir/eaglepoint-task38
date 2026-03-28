"""Add user topic subscriptions table

Revision ID: 015_user_topic_subscriptions
Revises: 014_security_privacy_encryption_updates
Create Date: 2024-01-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "015_user_topic_subscriptions"
down_revision: Union[str, None] = "014_security_privacy_encryption_updates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_topic_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_topic_subscriptions_user_id"), "user_topic_subscriptions", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_topic_subscriptions_topic"), "user_topic_subscriptions", ["topic"], unique=False)
    op.create_index("uq_user_topic_subscriptions_user_topic", "user_topic_subscriptions", ["user_id", "topic"], unique=True)
    op.create_index("ix_user_topic_subscriptions_user_created", "user_topic_subscriptions", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_topic_subscriptions_user_created", table_name="user_topic_subscriptions")
    op.drop_index("uq_user_topic_subscriptions_user_topic", table_name="user_topic_subscriptions")
    op.drop_index(op.f("ix_user_topic_subscriptions_topic"), table_name="user_topic_subscriptions")
    op.drop_index(op.f("ix_user_topic_subscriptions_user_id"), table_name="user_topic_subscriptions")
    op.drop_table("user_topic_subscriptions")
