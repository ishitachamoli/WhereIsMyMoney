"""Add confidence_score and classification_source columns to transactions.

Revision ID: a3f7c2d91e01
Revises:
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'a3f7c2d91e01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='1.0')
    )
    op.add_column(
        'transactions',
        sa.Column('classification_source', sa.String(30), nullable=False, server_default='rule')
    )


def downgrade() -> None:
    op.drop_column('transactions', 'classification_source')
    op.drop_column('transactions', 'confidence_score')
