"""
add provider column to recommendation_snapshots

Revision ID: 0002_add_provider
Revises: 0001_init
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_provider"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recommendation_snapshots", sa.Column("provider", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("recommendation_snapshots", "provider")

