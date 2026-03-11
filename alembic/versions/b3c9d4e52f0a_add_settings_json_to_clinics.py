"""add settings JSON column to clinics

Revision ID: b3c9d4e52f0a
Revises: a2f8c3d41e9b
Create Date: 2026-03-12 10:00:00.000000

Changes:
- Add settings (JSON) column to clinics table for storing activity_logs,
  GMB config, backlinks, google_ads config, and other per-clinic settings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c9d4e52f0a'
down_revision: Union[str, None] = 'a2f8c3d41e9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clinics', sa.Column('settings', sa.JSON(), nullable=True, server_default='{}'))


def downgrade() -> None:
    op.drop_column('clinics', 'settings')
