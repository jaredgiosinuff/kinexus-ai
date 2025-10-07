"""Initial schema with users, documents, reviews, and audit

Revision ID: acdfb8332457
Revises: 
Create Date: 2025-09-27 12:03:34.147165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'acdfb8332457'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum('viewer', 'reviewer', 'lead_reviewer', 'admin', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('source_system', sa.String(50), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=False),
        sa.Column('current_version', sa.Integer(), default=1, nullable=False),
        sa.Column('status', sa.Enum('active', 'archived', 'deleted', name='documentstatus'), default='active', nullable=False),
        sa.Column('doc_metadata', sa.JSON()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('idx_document_source_external', 'documents', ['source_system', 'external_id'])
    op.create_index('idx_document_type_status', 'documents', ['document_type', 'status'])
    op.create_unique_constraint('uq_document_source_external', 'documents', ['source_system', 'external_id'])

    # Create document_versions table
    op.create_table(
        'document_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_format', sa.String(20), default='markdown', nullable=False),
        sa.Column('change_summary', sa.Text()),
        sa.Column('ai_generated', sa.Boolean(), default=False, nullable=False),
        sa.Column('ai_model', sa.String(100)),
        sa.Column('ai_confidence', sa.Integer()),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_version_document_version', 'document_versions', ['document_id', 'version'])
    op.create_unique_constraint('uq_document_version', 'document_versions', ['document_id', 'version'])

    # Create approval_rules table
    op.create_table(
        'approval_rules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('conditions', sa.JSON(), nullable=False),
        sa.Column('action', sa.Enum('auto_approve', 'require_review', 'require_lead_review', 'require_admin_review', name='approvalaction'), nullable=False),
        sa.Column('priority', sa.Integer(), default=0, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('times_applied', sa.Integer(), default=0, nullable=False),
        sa.Column('last_applied', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('idx_approval_rule_active_priority', 'approval_rules', ['is_active', 'priority'])

    # Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('change_id', sa.String(255), nullable=False),
        sa.Column('proposed_version', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'in_review', 'approved', 'approved_with_changes', 'rejected', 'auto_approved', name='reviewstatus'), default='pending', nullable=False),
        sa.Column('priority', sa.Integer(), default=5, nullable=False),
        sa.Column('impact_score', sa.Integer(), nullable=False),
        sa.Column('reviewer_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('assigned_at', sa.DateTime(timezone=True)),
        sa.Column('reviewed_at', sa.DateTime(timezone=True)),
        sa.Column('decision', sa.String(50)),
        sa.Column('feedback', sa.Text()),
        sa.Column('modifications', sa.JSON()),
        sa.Column('ai_reasoning', sa.Text()),
        sa.Column('ai_confidence', sa.Integer()),
        sa.Column('ai_model', sa.String(100)),
        sa.Column('change_context', sa.JSON()),
        sa.Column('auto_approval_rule_id', UUID(as_uuid=True), sa.ForeignKey('approval_rules.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('idx_review_status_priority', 'reviews', ['status', 'priority'])
    op.create_index('idx_review_reviewer_status', 'reviews', ['reviewer_id', 'status'])
    op.create_index('idx_review_created', 'reviews', ['created_at'])
    op.create_index('idx_review_change_id', 'reviews', ['change_id'])

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', UUID(as_uuid=True), nullable=False),
        sa.Column('old_values', sa.JSON()),
        sa.Column('new_values', sa.JSON()),
        sa.Column('audit_metadata', sa.JSON()),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_audit_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])

    # Create system_metrics table
    op.create_table(
        'system_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Integer(), nullable=False),
        sa.Column('dimensions', sa.JSON()),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_metric_name_timestamp', 'system_metrics', ['metric_name', 'timestamp'])
    op.create_index('idx_metric_timestamp', 'system_metrics', ['timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('system_metrics')
    op.drop_table('audit_logs')
    op.drop_table('reviews')
    op.drop_table('approval_rules')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('users')

    # Drop custom enums
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS documentstatus')
    op.execute('DROP TYPE IF EXISTS reviewstatus')
    op.execute('DROP TYPE IF EXISTS approvalaction')
