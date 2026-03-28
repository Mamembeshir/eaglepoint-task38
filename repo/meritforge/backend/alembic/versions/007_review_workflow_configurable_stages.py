"""Add configurable review workflow stages and needs_revision status

Revision ID: 007_review_workflow_configurable_stages
Revises: 006_content_risk_scoring
Create Date: 2024-01-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "007_review_workflow_configurable_stages"
down_revision: Union[str, None] = "006_content_risk_scoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE contentstatus ADD VALUE IF NOT EXISTS 'needs_revision'")

    op.add_column(
        "review_workflow_stages",
        sa.Column("is_parallel", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_table(
        "review_workflow_template_stages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_name", sa.String(length=100), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_parallel", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_workflow_template_stages_created_by_id"),
        "review_workflow_template_stages",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_review_workflow_template_order_active",
        "review_workflow_template_stages",
        ["stage_order", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_review_workflow_template_parallel",
        "review_workflow_template_stages",
        ["is_parallel", "stage_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_review_workflow_template_parallel", table_name="review_workflow_template_stages")
    op.drop_index("ix_review_workflow_template_order_active", table_name="review_workflow_template_stages")
    op.drop_index(op.f("ix_review_workflow_template_stages_created_by_id"), table_name="review_workflow_template_stages")
    op.drop_table("review_workflow_template_stages")

    op.drop_column("review_workflow_stages", "is_parallel")
