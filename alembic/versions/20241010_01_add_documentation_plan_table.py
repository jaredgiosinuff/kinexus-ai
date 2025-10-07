"""add documentation plan table

Revision ID: add_documentation_plan
Revises: acdfb8332457
Create Date: 2024-10-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_documentation_plan'
down_revision = 'acdfb8332457'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'documentation_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repository', sa.String(length=255), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('branch', sa.String(length=255), nullable=True),
        sa.Column('execution_mode', sa.String(length=50), nullable=False, server_default='plan_only'),
        sa.Column('plan', sa.JSON(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'in_review', 'completed', 'failed', name='documentationplanstatus'), nullable=False, server_default='pending'),
        sa.Column('review_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reviews.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('idx_doc_plan_repo_pr', 'documentation_plans', ['repository', 'pr_number'])
    op.create_index('idx_doc_plan_status', 'documentation_plans', ['status'])


def downgrade() -> None:
    op.drop_index('idx_doc_plan_status', table_name='documentation_plans')
    op.drop_index('idx_doc_plan_repo_pr', table_name='documentation_plans')
    op.drop_table('documentation_plans')
    op.execute("DROP TYPE IF EXISTS documentationplanstatus")
