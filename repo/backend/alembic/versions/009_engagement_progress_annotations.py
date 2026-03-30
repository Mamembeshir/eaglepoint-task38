"""Add telemetry enhancements, milestone templates/revisions, annotation revisions

Revision ID: 009_engagement_annotations
Revises: 008_publishing_history
Create Date: 2024-01-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "009_engagement_annotations"
down_revision: Union[str, None] = "008_publishing_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'job_application'")

    op.execute("ALTER TABLE event_telemetry ALTER COLUMN event_data TYPE jsonb USING CASE WHEN event_data IS NULL THEN NULL ELSE to_jsonb(event_data) END")
    op.add_column("event_telemetry", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_telemetry_analytics_event_user_time", "event_telemetry", ["event_type", "user_id", "created_at"], unique=False)
    op.create_index("ix_telemetry_analytics_content_time", "event_telemetry", ["content_id", "created_at"], unique=False)

    op.create_table(
        "student_milestone_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_predefined", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("automation_event_type", sa.Enum(
            "play", "skip", "favorite", "search", "application", "view", "download", "share", "job_application", name="eventtype"
        ), nullable=True),
        sa.Column("threshold_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_student_milestone_templates_key"), "student_milestone_templates", ["key"], unique=True)
    op.create_index(op.f("ix_student_milestone_templates_automation_event_type"), "student_milestone_templates", ["automation_event_type"], unique=False)
    op.create_index(op.f("ix_student_milestone_templates_created_by_id"), "student_milestone_templates", ["created_by_id"], unique=False)
    op.create_index("ix_student_milestone_templates_active_event", "student_milestone_templates", ["is_active", "automation_event_type"], unique=False)

    op.add_column("student_progress_milestones", sa.Column("milestone_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("student_progress_milestones", sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("student_progress_milestones", sa.Column("source", sa.String(length=50), nullable=False, server_default="manual"))
    op.add_column("student_progress_milestones", sa.Column("progress_value", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("student_progress_milestones", sa.Column("target_value", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("student_progress_milestones", sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("student_progress_milestones", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.add_column("student_progress_milestones", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.execute("ALTER TABLE student_progress_milestones ALTER COLUMN metadata_json TYPE jsonb USING CASE WHEN metadata_json IS NULL THEN NULL ELSE to_jsonb(metadata_json) END")
    op.execute("ALTER TABLE student_progress_milestones ALTER COLUMN achievement_date DROP NOT NULL")
    op.create_foreign_key(
        "fk_student_progress_milestones_template",
        "student_progress_milestones",
        "student_milestone_templates",
        ["milestone_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_student_progress_milestones_milestone_template_id"), "student_progress_milestones", ["milestone_template_id"], unique=False)
    op.create_index("ix_milestones_student_template", "student_progress_milestones", ["student_id", "milestone_template_id"], unique=False)
    op.create_index("ix_milestones_updated_at", "student_progress_milestones", ["updated_at"], unique=False)

    op.create_table(
        "student_progress_milestone_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["milestone_id"], ["student_progress_milestones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_student_progress_milestone_revisions_milestone_id"), "student_progress_milestone_revisions", ["milestone_id"], unique=False)
    op.create_index(op.f("ix_student_progress_milestone_revisions_changed_by_id"), "student_progress_milestone_revisions", ["changed_by_id"], unique=False)
    op.create_index("ix_milestone_revisions_milestone_revision", "student_progress_milestone_revisions", ["milestone_id", "revision_number"], unique=False)

    op.execute("ALTER TABLE annotations ALTER COLUMN tags TYPE jsonb USING CASE WHEN tags IS NULL THEN NULL ELSE to_jsonb(tags) END")
    op.add_column("annotations", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    op.create_table(
        "annotation_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("annotation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("previous_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["annotation_id"], ["annotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_annotation_revisions_annotation_id"), "annotation_revisions", ["annotation_id"], unique=False)
    op.create_index(op.f("ix_annotation_revisions_changed_by_id"), "annotation_revisions", ["changed_by_id"], unique=False)
    op.create_index("ix_annotation_revisions_annotation_revision", "annotation_revisions", ["annotation_id", "revision_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_annotation_revisions_annotation_revision", table_name="annotation_revisions")
    op.drop_index(op.f("ix_annotation_revisions_changed_by_id"), table_name="annotation_revisions")
    op.drop_index(op.f("ix_annotation_revisions_annotation_id"), table_name="annotation_revisions")
    op.drop_table("annotation_revisions")

    op.drop_column("annotations", "version")

    op.drop_index("ix_milestone_revisions_milestone_revision", table_name="student_progress_milestone_revisions")
    op.drop_index(op.f("ix_student_progress_milestone_revisions_changed_by_id"), table_name="student_progress_milestone_revisions")
    op.drop_index(op.f("ix_student_progress_milestone_revisions_milestone_id"), table_name="student_progress_milestone_revisions")
    op.drop_table("student_progress_milestone_revisions")

    op.drop_index("ix_milestones_updated_at", table_name="student_progress_milestones")
    op.drop_index("ix_milestones_student_template", table_name="student_progress_milestones")
    op.drop_index(op.f("ix_student_progress_milestones_milestone_template_id"), table_name="student_progress_milestones")
    op.drop_constraint("fk_student_progress_milestones_template", "student_progress_milestones", type_="foreignkey")
    op.drop_column("student_progress_milestones", "version")
    op.drop_column("student_progress_milestones", "updated_at")
    op.drop_column("student_progress_milestones", "last_event_at")
    op.drop_column("student_progress_milestones", "target_value")
    op.drop_column("student_progress_milestones", "progress_value")
    op.drop_column("student_progress_milestones", "source")
    op.drop_column("student_progress_milestones", "is_custom")
    op.drop_column("student_progress_milestones", "milestone_template_id")

    op.drop_index("ix_student_milestone_templates_active_event", table_name="student_milestone_templates")
    op.drop_index(op.f("ix_student_milestone_templates_created_by_id"), table_name="student_milestone_templates")
    op.drop_index(op.f("ix_student_milestone_templates_automation_event_type"), table_name="student_milestone_templates")
    op.drop_index(op.f("ix_student_milestone_templates_key"), table_name="student_milestone_templates")
    op.drop_table("student_milestone_templates")

    op.drop_index("ix_telemetry_analytics_content_time", table_name="event_telemetry")
    op.drop_index("ix_telemetry_analytics_event_user_time", table_name="event_telemetry")
    op.drop_column("event_telemetry", "updated_at")
