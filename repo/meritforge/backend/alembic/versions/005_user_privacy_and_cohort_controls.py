"""Add user privacy consent and deletion lifecycle fields

Revision ID: 005_user_privacy_and_cohort_controls
Revises: 004_auth_refresh_tokens
Create Date: 2024-01-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_user_privacy_and_cohort_controls"
down_revision: Union[str, None] = "004_auth_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("consent_contact_info_visible", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("consent_photo_visible", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("is_marked_for_deletion", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("scheduled_deletion_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("deletion_reason", sa.Text(), nullable=True))
    op.create_index("ix_users_marked_for_deletion", "users", ["is_marked_for_deletion", "scheduled_deletion_at"], unique=False)

    op.add_column("user_cohorts", sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("user_cohorts", sa.Column("is_admin_defined", sa.Boolean(), nullable=False, server_default="false"))
    op.create_foreign_key(
        "fk_user_cohorts_created_by_id_users",
        "user_cohorts",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_user_cohorts_created_by_id"), "user_cohorts", ["created_by_id"], unique=False)
    op.create_index("ix_user_cohorts_created_by", "user_cohorts", ["created_by_id", "is_admin_defined"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_cohorts_created_by", table_name="user_cohorts")
    op.drop_index(op.f("ix_user_cohorts_created_by_id"), table_name="user_cohorts")
    op.drop_constraint("fk_user_cohorts_created_by_id_users", "user_cohorts", type_="foreignkey")
    op.drop_column("user_cohorts", "is_admin_defined")
    op.drop_column("user_cohorts", "created_by_id")

    op.drop_index("ix_users_marked_for_deletion", table_name="users")
    op.drop_column("users", "deletion_reason")
    op.drop_column("users", "scheduled_deletion_at")
    op.drop_column("users", "deletion_requested_at")
    op.drop_column("users", "is_marked_for_deletion")
    op.drop_column("users", "consent_photo_visible")
    op.drop_column("users", "consent_contact_info_visible")
    op.drop_column("users", "phone_number")
