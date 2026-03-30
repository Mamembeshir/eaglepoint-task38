"""Add employer job management and notifications data structures

Revision ID: 010_employer_job_features
Revises: 009_engagement_annotations
Create Date: 2024-01-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "010_employer_job_features"
down_revision: Union[str, None] = "009_engagement_annotations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("job_posts", sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_job_posts_created_by", "job_posts", "users", ["created_by_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_job_posts_created_by_id"), "job_posts", ["created_by_id"], unique=False)
    op.create_index("ix_job_posts_created_by", "job_posts", ["created_by_id", "is_active"], unique=False)

    op.execute("ALTER TABLE applications ALTER COLUMN custom_fields TYPE jsonb USING CASE WHEN custom_fields IS NULL THEN NULL ELSE to_jsonb(custom_fields) END")
    op.add_column("applications", sa.Column("status_changed_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_applications_status_changed_by", "applications", "users", ["status_changed_by_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_applications_status_changed_by_id"), "applications", ["status_changed_by_id"], unique=False)
    op.create_index("ix_applications_status_changed_by", "applications", ["status_changed_by_id", "updated_at"], unique=False)

    op.add_column("student_milestone_templates", sa.Column("job_post_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_student_milestone_templates_job_post", "student_milestone_templates", "job_posts", ["job_post_id"], ["id"], ondelete="CASCADE")
    op.create_index(op.f("ix_student_milestone_templates_job_post_id"), "student_milestone_templates", ["job_post_id"], unique=False)
    op.create_index("ix_student_milestone_templates_job_post", "student_milestone_templates", ["job_post_id", "is_active"], unique=False)

    op.add_column("student_progress_milestones", sa.Column("job_post_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("student_progress_milestones", sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_student_progress_job_post", "student_progress_milestones", "job_posts", ["job_post_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_student_progress_application", "student_progress_milestones", "applications", ["application_id"], ["id"], ondelete="CASCADE")
    op.create_index(op.f("ix_student_progress_milestones_job_post_id"), "student_progress_milestones", ["job_post_id"], unique=False)
    op.create_index(op.f("ix_student_progress_milestones_application_id"), "student_progress_milestones", ["application_id"], unique=False)
    op.create_index("ix_milestones_job_post_student", "student_progress_milestones", ["job_post_id", "student_id"], unique=False)
    op.create_index("ix_milestones_application", "student_progress_milestones", ["application_id", "updated_at"], unique=False)

    op.create_table(
        "in_app_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("related_entity_type", sa.String(length=100), nullable=True),
        sa.Column("related_entity_id", sa.String(length=100), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_in_app_notifications_user_id"), "in_app_notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_in_app_notifications_category"), "in_app_notifications", ["category"], unique=False)
    op.create_index("ix_in_app_notifications_user_read", "in_app_notifications", ["user_id", "is_read"], unique=False)
    op.create_index("ix_in_app_notifications_user_created", "in_app_notifications", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_in_app_notifications_user_created", table_name="in_app_notifications")
    op.drop_index("ix_in_app_notifications_user_read", table_name="in_app_notifications")
    op.drop_index(op.f("ix_in_app_notifications_category"), table_name="in_app_notifications")
    op.drop_index(op.f("ix_in_app_notifications_user_id"), table_name="in_app_notifications")
    op.drop_table("in_app_notifications")

    op.drop_index("ix_milestones_application", table_name="student_progress_milestones")
    op.drop_index("ix_milestones_job_post_student", table_name="student_progress_milestones")
    op.drop_index(op.f("ix_student_progress_milestones_application_id"), table_name="student_progress_milestones")
    op.drop_index(op.f("ix_student_progress_milestones_job_post_id"), table_name="student_progress_milestones")
    op.drop_constraint("fk_student_progress_application", "student_progress_milestones", type_="foreignkey")
    op.drop_constraint("fk_student_progress_job_post", "student_progress_milestones", type_="foreignkey")
    op.drop_column("student_progress_milestones", "application_id")
    op.drop_column("student_progress_milestones", "job_post_id")

    op.drop_index("ix_student_milestone_templates_job_post", table_name="student_milestone_templates")
    op.drop_index(op.f("ix_student_milestone_templates_job_post_id"), table_name="student_milestone_templates")
    op.drop_constraint("fk_student_milestone_templates_job_post", "student_milestone_templates", type_="foreignkey")
    op.drop_column("student_milestone_templates", "job_post_id")

    op.drop_index("ix_applications_status_changed_by", table_name="applications")
    op.drop_index(op.f("ix_applications_status_changed_by_id"), table_name="applications")
    op.drop_constraint("fk_applications_status_changed_by", "applications", type_="foreignkey")
    op.drop_column("applications", "status_changed_by_id")

    op.drop_index("ix_job_posts_created_by", table_name="job_posts")
    op.drop_index(op.f("ix_job_posts_created_by_id"), table_name="job_posts")
    op.drop_constraint("fk_job_posts_created_by", "job_posts", type_="foreignkey")
    op.drop_column("job_posts", "created_by_id")
