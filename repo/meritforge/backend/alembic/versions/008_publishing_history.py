"""Add publishing history table

Revision ID: 008_publishing_history
Revises: 007_review_workflow_configurable_stages
Create Date: 2024-01-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008_publishing_history"
down_revision: Union[str, None] = "007_review_workflow_configurable_stages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "publishing_histories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("before_state", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_publishing_histories_content_id"), "publishing_histories", ["content_id"], unique=False)
    op.create_index(op.f("ix_publishing_histories_action"), "publishing_histories", ["action"], unique=False)
    op.create_index(op.f("ix_publishing_histories_actor_id"), "publishing_histories", ["actor_id"], unique=False)
    op.create_index("ix_publishing_histories_content_action", "publishing_histories", ["content_id", "action"], unique=False)
    op.create_index("ix_publishing_histories_created", "publishing_histories", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_publishing_histories_created", table_name="publishing_histories")
    op.drop_index("ix_publishing_histories_content_action", table_name="publishing_histories")
    op.drop_index(op.f("ix_publishing_histories_actor_id"), table_name="publishing_histories")
    op.drop_index(op.f("ix_publishing_histories_action"), table_name="publishing_histories")
    op.drop_index(op.f("ix_publishing_histories_content_id"), table_name="publishing_histories")
    op.drop_table("publishing_histories")
