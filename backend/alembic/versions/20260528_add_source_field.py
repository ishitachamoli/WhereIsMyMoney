"""Add source field to transactions for manual vs uploaded distinction.

Revision ID: b4e8d3f12a02
Revises: a3f7c2d91e01
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'b4e8d3f12a02'
down_revision = 'a3f7c2d91e01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('source', sa.String(20), nullable=False, server_default='upload')
    )


def downgrade() -> None:
    op.drop_column('transactions', 'source')
