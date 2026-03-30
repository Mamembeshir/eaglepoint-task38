"""Convert audit payload fields to JSON and prepare retention

Revision ID: 012_auditlog_json_and_retention
Revises: 011_operations_metrics_tables
Create Date: 2024-01-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012_auditlog_json_and_retention"
down_revision: Union[str, None] = "011_operations_metrics_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE audit_logs
        ALTER COLUMN before_data TYPE jsonb
        USING CASE
            WHEN before_data IS NULL THEN NULL
            WHEN left(trim(before_data), 1) IN ('{', '[') THEN before_data::jsonb
            ELSE to_jsonb(before_data)
        END
        """
    )
    op.execute(
        """
        ALTER TABLE audit_logs
        ALTER COLUMN after_data TYPE jsonb
        USING CASE
            WHEN after_data IS NULL THEN NULL
            WHEN left(trim(after_data), 1) IN ('{', '[') THEN after_data::jsonb
            ELSE to_jsonb(after_data)
        END
        """
    )
    op.execute(
        """
        ALTER TABLE audit_logs
        ALTER COLUMN changes TYPE jsonb
        USING CASE
            WHEN changes IS NULL THEN NULL
            WHEN left(trim(changes), 1) IN ('{', '[') THEN changes::jsonb
            ELSE to_jsonb(changes)
        END
        """
    )

    op.create_index("ix_audit_logs_retention", "audit_logs", ["created_at", "action"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_retention", table_name="audit_logs")
    op.execute("ALTER TABLE audit_logs ALTER COLUMN before_data TYPE varchar USING before_data::text")
    op.execute("ALTER TABLE audit_logs ALTER COLUMN after_data TYPE varchar USING after_data::text")
    op.execute("ALTER TABLE audit_logs ALTER COLUMN changes TYPE varchar USING changes::text")
