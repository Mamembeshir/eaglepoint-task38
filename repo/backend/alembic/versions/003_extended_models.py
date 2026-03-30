"""Add JobPost, Application, Milestone, Bookmark, Annotation, Telemetry, Risk, Audit, Webhook

Revision ID: 003_extended_models
Revises: 002_content_workflow
Create Date: 2024-01-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003_extended_models'
down_revision: Union[str, None] = '002_content_workflow'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'job_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('employer_name', sa.String(length=255), nullable=False),
        sa.Column('employer_logo_url', sa.String(length=500), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('location_type', sa.String(length=50), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=True),
        sa.Column('salary_min', sa.Numeric(12, 2), nullable=True),
        sa.Column('salary_max', sa.Numeric(12, 2), nullable=True),
        sa.Column('salary_currency', sa.String(length=3), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('benefits', sa.Text(), nullable=True),
        sa.Column('application_deadline', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('application_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_id')
    )
    op.create_index('ix_job_posts_employer_active', 'job_posts', ['employer_name', 'is_active'])
    op.create_index('ix_job_posts_location_active', 'job_posts', ['location', 'is_active'])
    op.create_index('ix_job_posts_deadline_active', 'job_posts', ['application_deadline', 'is_active'])
    op.create_index('ix_job_posts_featured', 'job_posts', ['is_featured', 'is_active'])
    op.create_index(op.f('ix_job_posts_content_id'), 'job_posts', ['content_id'], unique=True)
    op.create_index(op.f('ix_job_posts_employer_name'), 'job_posts', ['employer_name'])

    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('applicant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('draft', 'submitted', 'under_review', 'interview_scheduled', 'accepted', 'rejected', 'withdrawn', name='applicationstatus'), nullable=False, server_default='draft'),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('resume_url', sa.String(length=500), nullable=True),
        sa.Column('portfolio_url', sa.String(length=500), nullable=True),
        sa.Column('custom_fields', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['job_post_id'], ['job_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_post_id', 'applicant_id', name='uq_applications_job_applicant')
    )
    op.create_index('ix_applications_job_status', 'applications', ['job_post_id', 'status'])
    op.create_index('ix_applications_applicant_status', 'applications', ['applicant_id', 'status'])
    op.create_index('ix_applications_submitted', 'applications', ['submitted_at'])
    op.create_index(op.f('ix_applications_job_post_id'), 'applications', ['job_post_id'])
    op.create_index(op.f('ix_applications_applicant_id'), 'applications', ['applicant_id'])
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'])

    op.create_table(
        'student_progress_milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('milestone_type', sa.String(length=100), nullable=False),
        sa.Column('milestone_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('achievement_date', sa.Date(), nullable=False),
        sa.Column('metadata_json', sa.String(), nullable=True),
        sa.Column('certificate_url', sa.String(length=500), nullable=True),
        sa.Column('badge_url', sa.String(length=500), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verified_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_milestones_student_type', 'student_progress_milestones', ['student_id', 'milestone_type'])
    op.create_index('ix_milestones_student_date', 'student_progress_milestones', ['student_id', 'achievement_date'])
    op.create_index('ix_milestones_verified', 'student_progress_milestones', ['is_verified', 'achievement_date'])
    op.create_index(op.f('ix_student_progress_milestones_student_id'), 'student_progress_milestones', ['student_id'])
    op.create_index(op.f('ix_student_progress_milestones_milestone_type'), 'student_progress_milestones', ['milestone_type'])
    op.create_index(op.f('ix_student_progress_milestones_achievement_date'), 'student_progress_milestones', ['achievement_date'])

    op.create_table(
        'bookmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('folder', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'content_id', name='uq_bookmarks_user_content')
    )
    op.create_index('ix_bookmarks_user_favorite', 'bookmarks', ['user_id', 'is_favorite'])
    op.create_index('ix_bookmarks_user_folder', 'bookmarks', ['user_id', 'folder'])
    op.create_index(op.f('ix_bookmarks_user_id'), 'bookmarks', ['user_id'])
    op.create_index(op.f('ix_bookmarks_content_id'), 'bookmarks', ['content_id'])
    op.create_index(op.f('ix_bookmarks_folder'), 'bookmarks', ['folder'])

    op.create_table(
        'annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('visibility', sa.Enum('private', 'cohort', 'public', name='annotationvisibility'), nullable=False, server_default='private'),
        sa.Column('cohort_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('start_offset', sa.Integer(), nullable=False),
        sa.Column('end_offset', sa.Integer(), nullable=False),
        sa.Column('highlighted_text', sa.Text(), nullable=True),
        sa.Column('annotation_text', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cohort_id'], ['user_cohorts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_annotations_content_visibility', 'annotations', ['content_id', 'visibility'])
    op.create_index('ix_annotations_author_visibility', 'annotations', ['author_id', 'visibility'])
    op.create_index('ix_annotations_cohort', 'annotations', ['cohort_id', 'visibility'])
    op.create_index('ix_annotations_offsets', 'annotations', ['content_id', 'start_offset', 'end_offset'])
    op.create_index(op.f('ix_annotations_content_id'), 'annotations', ['content_id'])
    op.create_index(op.f('ix_annotations_author_id'), 'annotations', ['author_id'])
    op.create_index(op.f('ix_annotations_visibility'), 'annotations', ['visibility'])

    op.create_table(
        'event_telemetry',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.Enum('play', 'skip', 'favorite', 'search', 'application', 'view', 'download', 'share', name='eventtype'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('event_data', sa.String(), nullable=True),
        sa.Column('page_url', sa.String(length=500), nullable=True),
        sa.Column('referrer_url', sa.String(length=500), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('browser', sa.String(length=50), nullable=True),
        sa.Column('os', sa.String(length=50), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('progress_percentage', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_telemetry_type_created', 'event_telemetry', ['event_type', 'created_at'])
    op.create_index('ix_telemetry_user_type', 'event_telemetry', ['user_id', 'event_type'])
    op.create_index('ix_telemetry_content_type', 'event_telemetry', ['content_id', 'event_type'])
    op.create_index('ix_telemetry_session_created', 'event_telemetry', ['session_id', 'created_at'])
    op.create_index('ix_telemetry_resource', 'event_telemetry', ['resource_type', 'resource_id'])
    op.create_index('ix_telemetry_device_created', 'event_telemetry', ['device_type', 'created_at'])
    op.create_index(op.f('ix_event_telemetry_event_type'), 'event_telemetry', ['event_type'])
    op.create_index(op.f('ix_event_telemetry_user_id'), 'event_telemetry', ['user_id'])
    op.create_index(op.f('ix_event_telemetry_session_id'), 'event_telemetry', ['session_id'])
    op.create_index(op.f('ix_event_telemetry_content_id'), 'event_telemetry', ['content_id'])
    op.create_index(op.f('ix_event_telemetry_resource_type'), 'event_telemetry', ['resource_type'])
    op.create_index(op.f('ix_event_telemetry_resource_id'), 'event_telemetry', ['resource_id'])
    op.create_index(op.f('ix_event_telemetry_ip_address'), 'event_telemetry', ['ip_address'])
    op.create_index(op.f('ix_event_telemetry_device_type'), 'event_telemetry', ['device_type'])
    op.create_index(op.f('ix_event_telemetry_created_at'), 'event_telemetry', ['created_at'])

    op.create_table(
        'risk_dictionary',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('term', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('replacement_suggestion', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_regex', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('match_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('term')
    )
    op.create_index('ix_risk_dictionary_category_severity', 'risk_dictionary', ['category', 'severity'])
    op.create_index('ix_risk_dictionary_active', 'risk_dictionary', ['is_active', 'category'])
    op.create_index(op.f('ix_risk_dictionary_term'), 'risk_dictionary', ['term'], unique=True)
    op.create_index(op.f('ix_risk_dictionary_category'), 'risk_dictionary', ['category'])
    op.create_index(op.f('ix_risk_dictionary_severity'), 'risk_dictionary', ['severity'])
    op.create_index(op.f('ix_risk_dictionary_created_by_id'), 'risk_dictionary', ['created_by_id'])

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.Enum('create', 'update', 'delete', 'login', 'logout', 'view', 'export', 'import', name='auditaction'), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('before_data', sa.String(), nullable=True),
        sa.Column('after_data', sa.String(), nullable=True),
        sa.Column('changes', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('request_url', sa.String(length=500), nullable=True),
        sa.Column('request_method', sa.String(length=10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('ix_audit_logs_action_created', 'audit_logs', ['action', 'created_at'])
    op.create_index('ix_audit_logs_user_created', 'audit_logs', ['user_id', 'created_at'])
    op.create_index('ix_audit_logs_entity_created', 'audit_logs', ['entity_type', 'entity_id', 'created_at'])
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'])
    op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'])
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'])
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'])
    op.create_index(op.f('ix_audit_logs_ip_address'), 'audit_logs', ['ip_address'])
    op.create_index(op.f('ix_audit_logs_session_id'), 'audit_logs', ['session_id'])
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'])

    op.create_table(
        'webhook_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=True),
        sa.Column('events', sa.String(), nullable=False),
        sa.Column('headers', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_delay_seconds', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_response_status', sa.Integer(), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_configs_active', 'webhook_configs', ['is_active'])
    op.create_index('ix_webhook_configs_events', 'webhook_configs', ['events'])
    op.create_index(op.f('ix_webhook_configs_created_by_id'), 'webhook_configs', ['created_by_id'])


def downgrade() -> None:
    op.drop_table('webhook_configs')
    op.execute("DROP TYPE IF EXISTS webhookevent")
    
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_session_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_ip_address'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index('ix_audit_logs_entity_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.execute("DROP TYPE IF EXISTS auditaction")
    
    op.drop_index(op.f('ix_risk_dictionary_created_by_id'), table_name='risk_dictionary')
    op.drop_index(op.f('ix_risk_dictionary_severity'), table_name='risk_dictionary')
    op.drop_index(op.f('ix_risk_dictionary_category'), table_name='risk_dictionary')
    op.drop_index(op.f('ix_risk_dictionary_term'), table_name='risk_dictionary')
    op.drop_index('ix_risk_dictionary_active', table_name='risk_dictionary')
    op.drop_index('ix_risk_dictionary_category_severity', table_name='risk_dictionary')
    op.drop_table('risk_dictionary')
    
    op.drop_index(op.f('ix_event_telemetry_created_at'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_device_type'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_ip_address'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_resource_id'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_resource_type'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_content_id'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_session_id'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_user_id'), table_name='event_telemetry')
    op.drop_index(op.f('ix_event_telemetry_event_type'), table_name='event_telemetry')
    op.drop_index('ix_telemetry_device_created', table_name='event_telemetry')
    op.drop_index('ix_telemetry_resource', table_name='event_telemetry')
    op.drop_index('ix_telemetry_session_created', table_name='event_telemetry')
    op.drop_index('ix_telemetry_content_type', table_name='event_telemetry')
    op.drop_index('ix_telemetry_user_type', table_name='event_telemetry')
    op.drop_index('ix_telemetry_type_created', table_name='event_telemetry')
    op.drop_table('event_telemetry')
    op.execute("DROP TYPE IF EXISTS eventtype")
    
    op.drop_index(op.f('ix_annotations_visibility'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_author_id'), table_name='annotations')
    op.drop_index(op.f('ix_annotations_content_id'), table_name='annotations')
    op.drop_index('ix_annotations_offsets', table_name='annotations')
    op.drop_index('ix_annotations_cohort', table_name='annotations')
    op.drop_index('ix_annotations_author_visibility', table_name='annotations')
    op.drop_index('ix_annotations_content_visibility', table_name='annotations')
    op.drop_table('annotations')
    op.execute("DROP TYPE IF EXISTS annotationvisibility")
    
    op.drop_index(op.f('ix_bookmarks_folder'), table_name='bookmarks')
    op.drop_index(op.f('ix_bookmarks_content_id'), table_name='bookmarks')
    op.drop_index(op.f('ix_bookmarks_user_id'), table_name='bookmarks')
    op.drop_index('ix_bookmarks_user_folder', table_name='bookmarks')
    op.drop_index('ix_bookmarks_user_favorite', table_name='bookmarks')
    op.drop_table('bookmarks')
    
    op.drop_index(op.f('ix_student_progress_milestones_achievement_date'), table_name='student_progress_milestones')
    op.drop_index(op.f('ix_student_progress_milestones_milestone_type'), table_name='student_progress_milestones')
    op.drop_index(op.f('ix_student_progress_milestones_student_id'), table_name='student_progress_milestones')
    op.drop_index('ix_milestones_verified', table_name='student_progress_milestones')
    op.drop_index('ix_milestones_student_date', table_name='student_progress_milestones')
    op.drop_index('ix_milestones_student_type', table_name='student_progress_milestones')
    op.drop_table('student_progress_milestones')
    
    op.drop_index(op.f('ix_applications_status'), table_name='applications')
    op.drop_index(op.f('ix_applications_applicant_id'), table_name='applications')
    op.drop_index(op.f('ix_applications_job_post_id'), table_name='applications')
    op.drop_index('ix_applications_submitted', table_name='applications')
    op.drop_index('ix_applications_applicant_status', table_name='applications')
    op.drop_index('ix_applications_job_status', table_name='applications')
    op.drop_table('applications')
    op.execute("DROP TYPE IF EXISTS applicationstatus")
    
    op.drop_index(op.f('ix_job_posts_employer_name'), table_name='job_posts')
    op.drop_index(op.f('ix_job_posts_content_id'), table_name='job_posts')
    op.drop_index('ix_job_posts_featured', table_name='job_posts')
    op.drop_index('ix_job_posts_deadline_active', table_name='job_posts')
    op.drop_index('ix_job_posts_location_active', table_name='job_posts')
    op.drop_index('ix_job_posts_employer_active', table_name='job_posts')
    op.drop_table('job_posts')
