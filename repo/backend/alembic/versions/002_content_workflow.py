"""Add Content, ContentVersion, ReviewWorkflow, Publishing, Canary models

Revision ID: 002_content_workflow
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_content_workflow'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'content_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_published_version', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_content_versions_content_number', 'content_versions', ['content_id', 'version_number'], unique=True)
    op.create_index('ix_content_versions_published', 'content_versions', ['content_id', 'is_published_version'])
    op.create_index('ix_content_versions_created_at', 'content_versions', ['created_at'])
    op.create_index(op.f('ix_content_versions_content_id'), 'content_versions', ['content_id'])
    op.create_index(op.f('ix_content_versions_created_by_id'), 'content_versions', ['created_by_id'])

    op.create_table(
        'contents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column(
            'content_type',
            sa.Enum('article', 'video', 'job_announcement', name='contenttype'),
            nullable=False
        ),
        sa.Column(
            'status',
            sa.Enum('draft', 'under_review', 'approved', 'rejected', 'published', 'retracted', name='contentstatus'),
            nullable=False,
            server_default='draft'
        ),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retracted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['current_version_id'], ['content_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contents_type_status', 'contents', ['content_type', 'status'])
    op.create_index('ix_contents_author_status', 'contents', ['author_id', 'status'])
    op.create_index('ix_contents_published_at', 'contents', ['published_at'])
    op.create_index('ix_contents_updated_at', 'contents', ['updated_at'])
    op.create_index('ix_contents_status_featured', 'contents', ['status', 'is_featured'])
    op.create_index(op.f('ix_contents_title'), 'contents', ['title'])
    op.create_index(op.f('ix_contents_slug'), 'contents', ['slug'], unique=True)
    op.create_index(op.f('ix_contents_content_type'), 'contents', ['content_type'])
    op.create_index(op.f('ix_contents_status'), 'contents', ['status'])
    op.create_index(op.f('ix_contents_author_id'), 'contents', ['author_id'])

    op.create_table(
        'review_workflow_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_name', sa.String(length=100), nullable=False),
        sa.Column('stage_order', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_review_stages_content_order', 'review_workflow_stages', ['content_id', 'stage_order'])
    op.create_index('ix_review_stages_completed', 'review_workflow_stages', ['content_id', 'is_completed'])
    op.create_index(op.f('ix_review_workflow_stages_content_id'), 'review_workflow_stages', ['content_id'])

    op.create_table(
        'publishing_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scheduled_publish_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_unpublish_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_unpublished', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('unpublished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('publish_job_id', sa.String(length=100), nullable=True),
        sa.Column('unpublish_job_id', sa.String(length=100), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_id')
    )
    op.create_index('ix_publishing_schedules_pending', 'publishing_schedules', ['scheduled_publish_at', 'is_published'])
    op.create_index('ix_publishing_schedules_unpublish', 'publishing_schedules', ['scheduled_unpublish_at', 'is_unpublished'])
    op.create_index(op.f('ix_publishing_schedules_content_id'), 'publishing_schedules', ['content_id'], unique=True)
    op.create_index(op.f('ix_publishing_schedules_scheduled_publish_at'), 'publishing_schedules', ['scheduled_publish_at'])
    op.create_index(op.f('ix_publishing_schedules_created_by_id'), 'publishing_schedules', ['created_by_id'])

    op.create_table(
        'canary_release_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'segmentation_type',
            sa.Enum('random', 'cohort', 'role', 'user_list', name='segmentationtype'),
            nullable=False,
            server_default='random'
        ),
        sa.Column('segment_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('ramp_stages', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('current_stage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('target_user_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('target_cohort_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metrics_threshold', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.CheckConstraint('percentage >= 0 AND percentage <= 100', name='ck_canary_percentage_range'),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_id')
    )
    op.create_index('ix_canary_configs_enabled_active', 'canary_release_configs', ['is_enabled', 'is_active'])
    op.create_index('ix_canary_configs_percentage', 'canary_release_configs', ['percentage'])
    op.create_index('ix_canary_configs_segmentation', 'canary_release_configs', ['segmentation_type'])
    op.create_index('ix_canary_configs_started', 'canary_release_configs', ['started_at'])
    op.create_index(op.f('ix_canary_release_configs_content_id'), 'canary_release_configs', ['content_id'], unique=True)
    op.create_index(op.f('ix_canary_release_configs_created_by_id'), 'canary_release_configs', ['created_by_id'])

    op.create_table(
        'review_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('content_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['content_version_id'], ['content_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['stage_id'], ['review_workflow_stages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_review_decisions_stage_decision', 'review_decisions', ['stage_id', 'decision'])
    op.create_index('ix_review_decisions_reviewer_created', 'review_decisions', ['reviewer_id', 'created_at'])
    op.create_index(op.f('ix_review_decisions_stage_id'), 'review_decisions', ['stage_id'])
    op.create_index(op.f('ix_review_decisions_reviewer_id'), 'review_decisions', ['reviewer_id'])
    op.create_index(op.f('ix_review_decisions_decision'), 'review_decisions', ['decision'])


def downgrade() -> None:
    op.drop_table('review_decisions')
    
    op.drop_index(op.f('ix_canary_release_configs_created_by_id'), table_name='canary_release_configs')
    op.drop_index(op.f('ix_canary_release_configs_content_id'), table_name='canary_release_configs')
    op.drop_index('ix_canary_configs_started', table_name='canary_release_configs')
    op.drop_index('ix_canary_configs_segmentation', table_name='canary_release_configs')
    op.drop_index('ix_canary_configs_percentage', table_name='canary_release_configs')
    op.drop_index('ix_canary_configs_enabled_active', table_name='canary_release_configs')
    op.drop_table('canary_release_configs')
    op.execute("DROP TYPE IF EXISTS segmentationtype")
    
    op.drop_index(op.f('ix_publishing_schedules_created_by_id'), table_name='publishing_schedules')
    op.drop_index(op.f('ix_publishing_schedules_scheduled_publish_at'), table_name='publishing_schedules')
    op.drop_index(op.f('ix_publishing_schedules_content_id'), table_name='publishing_schedules')
    op.drop_index('ix_publishing_schedules_unpublish', table_name='publishing_schedules')
    op.drop_index('ix_publishing_schedules_pending', table_name='publishing_schedules')
    op.drop_table('publishing_schedules')
    
    op.drop_index(op.f('ix_review_workflow_stages_content_id'), table_name='review_workflow_stages')
    op.drop_index('ix_review_stages_completed', table_name='review_workflow_stages')
    op.drop_index('ix_review_stages_content_order', table_name='review_workflow_stages')
    op.drop_table('review_workflow_stages')
    
    op.drop_index(op.f('ix_contents_author_id'), table_name='contents')
    op.drop_index(op.f('ix_contents_status'), table_name='contents')
    op.drop_index(op.f('ix_contents_content_type'), table_name='contents')
    op.drop_index(op.f('ix_contents_slug'), table_name='contents')
    op.drop_index(op.f('ix_contents_title'), table_name='contents')
    op.drop_index('ix_contents_status_featured', table_name='contents')
    op.drop_index('ix_contents_updated_at', table_name='contents')
    op.drop_index('ix_contents_published_at', table_name='contents')
    op.drop_index('ix_contents_author_status', table_name='contents')
    op.drop_index('ix_contents_type_status', table_name='contents')
    op.drop_table('contents')
    op.execute("DROP TYPE IF EXISTS contentstatus")
    op.execute("DROP TYPE IF EXISTS contenttype")
    
    op.drop_index(op.f('ix_content_versions_created_by_id'), table_name='content_versions')
    op.drop_index(op.f('ix_content_versions_content_id'), table_name='content_versions')
    op.drop_index('ix_content_versions_created_at', table_name='content_versions')
    op.drop_index('ix_content_versions_published', table_name='content_versions')
    op.drop_index('ix_content_versions_content_number', table_name='content_versions')
    op.drop_table('content_versions')
