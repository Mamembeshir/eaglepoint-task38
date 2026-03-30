"""Initial migration with User, Role, UserCohort models

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
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
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_roles_name_active', 'roles', ['name', 'is_active'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    op.create_table(
        'user_cohorts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
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
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_cohorts_name_active', 'user_cohorts', ['name', 'is_active'], unique=False)
    op.create_index('ix_user_cohorts_slug_active', 'user_cohorts', ['slug', 'is_active'], unique=False)
    op.create_index('ix_user_cohorts_updated_at', 'user_cohorts', ['updated_at'], unique=False)
    op.create_index(op.f('ix_user_cohorts_name'), 'user_cohorts', ['name'], unique=True)
    op.create_index(op.f('ix_user_cohorts_slug'), 'user_cohorts', ['slug'], unique=True)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email_active', 'users', ['email', 'is_active'], unique=False)
    op.create_index('ix_users_role_active', 'users', ['role_id', 'is_active'], unique=False)
    op.create_index('ix_users_updated_at', 'users', ['updated_at'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role_id'), 'users', ['role_id'], unique=False)

    op.create_table(
        'user_cohort_memberships',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cohort_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'joined_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(['cohort_id'], ['user_cohorts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'cohort_id')
    )

    op.execute("""
        INSERT INTO roles (name, description, is_active) VALUES
        ('student', 'Student user with basic access', true),
        ('employer_manager', 'Employer manager for hiring operations', true),
        ('content_author', 'Content author for creating and editing content', true),
        ('reviewer', 'Reviewer for content moderation', true),
        ('system_administrator', 'System administrator with full access', true)
    """)


def downgrade() -> None:
    op.drop_table('user_cohort_memberships')
    op.drop_index(op.f('ix_users_role_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index('ix_users_updated_at', table_name='users')
    op.drop_index('ix_users_role_active', table_name='users')
    op.drop_index('ix_users_email_active', table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_user_cohorts_slug'), table_name='user_cohorts')
    op.drop_index(op.f('ix_user_cohorts_name'), table_name='user_cohorts')
    op.drop_index('ix_user_cohorts_updated_at', table_name='user_cohorts')
    op.drop_index('ix_user_cohorts_slug_active', table_name='user_cohorts')
    op.drop_index('ix_user_cohorts_name_active', table_name='user_cohorts')
    op.drop_table('user_cohorts')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_index('ix_roles_name_active', table_name='roles')
    op.drop_table('roles')
