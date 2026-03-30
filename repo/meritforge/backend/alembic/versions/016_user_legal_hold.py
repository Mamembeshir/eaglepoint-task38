"""Add legal hold fields to users

Revision ID: 016_user_legal_hold
Revises: 015_user_topic_subscriptions
Create Date: 2024-01-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016_user_legal_hold"
down_revision: Union[str, None] = "015_user_topic_subscriptions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("legal_hold_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("legal_hold_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "legal_hold_updated_at")
    op.drop_column("users", "legal_hold_reason")
    op.drop_column("users", "legal_hold")
