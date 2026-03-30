"""Add consent toggles and token hash key metadata

Revision ID: 014_security_privacy_updates
Revises: 013_webhooks_delivery_queue
Create Date: 2024-01-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_security_privacy_updates"
down_revision: Union[str, None] = "013_webhooks_delivery_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("token_hash_key_id", sa.String(length=64), nullable=False, server_default="legacy-sha256"))

    op.add_column("users", sa.Column("consent_analytics", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("consent_data_portability", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("users", "consent_data_portability")
    op.drop_column("users", "consent_analytics")
    op.drop_column("refresh_tokens", "token_hash_key_id")
