"""admin portal, leaderboard enhancements, remove GHL

Revision ID: a2f8c3d41e9b
Revises: 1ee7bdd0971d
Create Date: 2026-03-11 12:00:00.000000

Changes:
- Drop ghl_integrations table
- Remove ghl_contact_id and ghl_opportunity_id from pipeline_deals
- Add is_super_admin to users (default False)
- Make users.clinic_id nullable (for super admins)
- Add leaderboard_visible to clinics (default True)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2f8c3d41e9b'
down_revision: Union[str, Sequence[str], None] = '1ee7bdd0971d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop GHL integrations table if it exists
    op.execute("""
        DROP TABLE IF EXISTS ghl_integrations
    """)

    # Remove GHL columns from pipeline_deals (if they exist)
    # Using raw SQL for SQLite compatibility
    try:
        op.drop_column('pipeline_deals', 'ghl_contact_id')
    except Exception:
        pass

    try:
        op.drop_column('pipeline_deals', 'ghl_opportunity_id')
    except Exception:
        pass

    # Add is_super_admin to users
    op.add_column('users', sa.Column('is_super_admin', sa.Boolean(), nullable=True, server_default=sa.text('false')))

    # Add leaderboard_visible to clinics
    op.add_column('clinics', sa.Column('leaderboard_visible', sa.Boolean(), nullable=True, server_default=sa.text('true')))

    # Make clinic_id nullable on users (for super admins)
    # Note: SQLite doesn't support ALTER COLUMN, so we use batch mode
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('clinic_id', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Remove leaderboard_visible from clinics
    op.drop_column('clinics', 'leaderboard_visible')

    # Remove is_super_admin from users
    op.drop_column('users', 'is_super_admin')

    # Make clinic_id non-nullable again
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('clinic_id', existing_type=sa.String(), nullable=False)

    # Re-add GHL columns to pipeline_deals
    op.add_column('pipeline_deals', sa.Column('ghl_contact_id', sa.String(), nullable=True))
    op.add_column('pipeline_deals', sa.Column('ghl_opportunity_id', sa.String(), nullable=True))

    # Re-create ghl_integrations table
    op.create_table(
        'ghl_integrations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=False),
        sa.Column('location_id', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_connected', sa.Boolean(), default=False),
        sa.Column('sync_pipeline_id', sa.String(), nullable=True),
        sa.Column('auto_sync_enabled', sa.Boolean(), default=True),
        sa.Column('total_leads_synced', sa.Integer(), default=0),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_status', sa.String(), nullable=True),
        sa.Column('last_sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
