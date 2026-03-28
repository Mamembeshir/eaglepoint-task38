"""Add webhook delivery queue, dead-letter queue, and JSON config fields

Revision ID: 013_webhooks_delivery_queue
Revises: 012_auditlog_json_and_retention
Create Date: 2024-01-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "013_webhooks_delivery_queue"
down_revision: Union[str, None] = "012_auditlog_json_and_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE webhook_configs ALTER COLUMN events TYPE jsonb USING CASE WHEN events IS NULL THEN '[]'::jsonb ELSE to_jsonb(events) END")
    op.execute("ALTER TABLE webhook_configs ALTER COLUMN headers TYPE jsonb USING CASE WHEN headers IS NULL THEN NULL ELSE to_jsonb(headers) END")

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("webhook_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["webhook_config_id"], ["webhook_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(op.f("ix_webhook_deliveries_webhook_config_id"), "webhook_deliveries", ["webhook_config_id"], unique=False)
    op.create_index(op.f("ix_webhook_deliveries_event_name"), "webhook_deliveries", ["event_name"], unique=False)
    op.create_index(op.f("ix_webhook_deliveries_idempotency_key"), "webhook_deliveries", ["idempotency_key"], unique=True)
    op.create_index(op.f("ix_webhook_deliveries_status"), "webhook_deliveries", ["status"], unique=False)
    op.create_index("ix_webhook_deliveries_config_event", "webhook_deliveries", ["webhook_config_id", "event_name"], unique=False)
    op.create_index("ix_webhook_deliveries_status_attempts", "webhook_deliveries", ["status", "attempts"], unique=False)
    op.create_index("ix_webhook_deliveries_created", "webhook_deliveries", ["created_at"], unique=False)

    op.create_table(
        "webhook_dead_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("webhook_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["delivery_id"], ["webhook_deliveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["webhook_config_id"], ["webhook_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delivery_id"),
    )
    op.create_index(op.f("ix_webhook_dead_letters_delivery_id"), "webhook_dead_letters", ["delivery_id"], unique=True)
    op.create_index(op.f("ix_webhook_dead_letters_webhook_config_id"), "webhook_dead_letters", ["webhook_config_id"], unique=False)
    op.create_index(op.f("ix_webhook_dead_letters_event_name"), "webhook_dead_letters", ["event_name"], unique=False)
    op.create_index("ix_webhook_dead_letters_event", "webhook_dead_letters", ["event_name", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_webhook_dead_letters_event", table_name="webhook_dead_letters")
    op.drop_index(op.f("ix_webhook_dead_letters_event_name"), table_name="webhook_dead_letters")
    op.drop_index(op.f("ix_webhook_dead_letters_webhook_config_id"), table_name="webhook_dead_letters")
    op.drop_index(op.f("ix_webhook_dead_letters_delivery_id"), table_name="webhook_dead_letters")
    op.drop_table("webhook_dead_letters")

    op.drop_index("ix_webhook_deliveries_created", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_status_attempts", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_config_event", table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_status"), table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_idempotency_key"), table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_event_name"), table_name="webhook_deliveries")
    op.drop_index(op.f("ix_webhook_deliveries_webhook_config_id"), table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.execute("ALTER TABLE webhook_configs ALTER COLUMN events TYPE varchar USING events::text")
    op.execute("ALTER TABLE webhook_configs ALTER COLUMN headers TYPE varchar USING headers::text")
