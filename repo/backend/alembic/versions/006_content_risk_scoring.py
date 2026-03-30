"""Add content risk scoring configuration and assessments

Revision ID: 006_content_risk_scoring
Revises: 005_user_privacy_cohort
Create Date: 2024-01-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006_content_risk_scoring"
down_revision: Union[str, None] = "005_user_privacy_cohort"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "risk_severity_weights",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("severity"),
    )
    op.create_index(op.f("ix_risk_severity_weights_severity"), "risk_severity_weights", ["severity"], unique=True)
    op.create_index("ix_risk_severity_weights_rank", "risk_severity_weights", ["rank"], unique=False)

    op.create_table(
        "risk_grade_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade", sa.String(length=20), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=True),
        sa.Column("blocked_until_final_approval", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("required_distinct_reviewers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grade"),
    )
    op.create_index(op.f("ix_risk_grade_rules_grade"), "risk_grade_rules", ["grade"], unique=True)
    op.create_index("ix_risk_grade_rules_bounds", "risk_grade_rules", ["min_score", "max_score"], unique=False)

    op.create_table(
        "content_risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_grade", sa.String(length=20), nullable=False),
        sa.Column("triggering_words", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("blocked_until_final_approval", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("required_distinct_reviewers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["contents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id"),
    )
    op.create_index(op.f("ix_content_risk_assessments_content_id"), "content_risk_assessments", ["content_id"], unique=True)
    op.create_index(op.f("ix_content_risk_assessments_risk_grade"), "content_risk_assessments", ["risk_grade"], unique=False)
    op.create_index("ix_content_risk_assessments_grade_score", "content_risk_assessments", ["risk_grade", "risk_score"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_content_risk_assessments_grade_score", table_name="content_risk_assessments")
    op.drop_index(op.f("ix_content_risk_assessments_risk_grade"), table_name="content_risk_assessments")
    op.drop_index(op.f("ix_content_risk_assessments_content_id"), table_name="content_risk_assessments")
    op.drop_table("content_risk_assessments")

    op.drop_index("ix_risk_grade_rules_bounds", table_name="risk_grade_rules")
    op.drop_index(op.f("ix_risk_grade_rules_grade"), table_name="risk_grade_rules")
    op.drop_table("risk_grade_rules")

    op.drop_index("ix_risk_severity_weights_rank", table_name="risk_severity_weights")
    op.drop_index(op.f("ix_risk_severity_weights_severity"), table_name="risk_severity_weights")
    op.drop_table("risk_severity_weights")
