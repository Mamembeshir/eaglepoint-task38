"""Add aggregated operations metrics tables

Revision ID: 011_operations_metrics_tables
Revises: 010_employer_job_features
Create Date: 2024-01-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "011_operations_metrics_tables"
down_revision: Union[str, None] = "010_employer_job_features"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ops_daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("active_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("returning_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interacted_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applying_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("converted_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("job_posts_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("applications_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("milestones_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("event_counts", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_date"),
    )
    op.create_index(op.f("ix_ops_daily_metrics_metric_date"), "ops_daily_metrics", ["metric_date"], unique=True)
    op.create_index("ix_ops_daily_metrics_conversion", "ops_daily_metrics", ["metric_date", "converted_users", "interacted_users"], unique=False)
    op.create_index("ix_ops_daily_metrics_funnel", "ops_daily_metrics", ["metric_date", "job_posts_created", "applications_created", "milestones_completed"], unique=False)

    op.create_table(
        "ops_event_daily_counts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_user_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ops_event_daily_counts_metric_date"), "ops_event_daily_counts", ["metric_date"], unique=False)
    op.create_index(op.f("ix_ops_event_daily_counts_event_type"), "ops_event_daily_counts", ["event_type"], unique=False)
    op.create_index("ix_ops_event_daily_unique", "ops_event_daily_counts", ["metric_date", "event_type"], unique=True)
    op.create_index("ix_ops_event_daily_trending", "ops_event_daily_counts", ["event_type", "metric_date", "event_count"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ops_event_daily_trending", table_name="ops_event_daily_counts")
    op.drop_index("ix_ops_event_daily_unique", table_name="ops_event_daily_counts")
    op.drop_index(op.f("ix_ops_event_daily_counts_event_type"), table_name="ops_event_daily_counts")
    op.drop_index(op.f("ix_ops_event_daily_counts_metric_date"), table_name="ops_event_daily_counts")
    op.drop_table("ops_event_daily_counts")

    op.drop_index("ix_ops_daily_metrics_funnel", table_name="ops_daily_metrics")
    op.drop_index("ix_ops_daily_metrics_conversion", table_name="ops_daily_metrics")
    op.drop_index(op.f("ix_ops_daily_metrics_metric_date"), table_name="ops_daily_metrics")
    op.drop_table("ops_daily_metrics")
