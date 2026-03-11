"""whatsapp, leads, nurture, social media, meta integration

Revision ID: b3c9e5f72a1d
Revises: a2f8c3d41e9b
Create Date: 2026-03-11 18:00:00.000000

Changes:
- Create leads table (central lead management)
- Create whatsapp_configs table (WhatsApp Cloud API credentials)
- Create ai_employees table (AI chatbot configuration)
- Create whatsapp_conversations table
- Create whatsapp_messages table
- Create nurture_sequences table
- Create nurture_steps table
- Create nurture_enrollments table
- Create clinic_api_keys table (webhook auth)
- Create meta_configs table (Meta/Facebook integration)
- Create social_accounts table
- Create social_posts table
- Create marketing_insights table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c9e5f72a1d'
down_revision: Union[str, None] = 'a2f8c3d41e9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Leads ---
    op.create_table(
        'leads',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('name', sa.String(200)),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(200)),
        sa.Column('source', sa.String(50), server_default='manual'),
        sa.Column('campaign_name', sa.String(200)),
        sa.Column('campaign_source', sa.String(50)),
        sa.Column('campaign_medium', sa.String(50)),
        sa.Column('campaign_content', sa.String(200)),
        sa.Column('lead_score', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(50), server_default='new'),
        sa.Column('lost_reason', sa.Text()),
        sa.Column('assigned_agent_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('form_data', sa.JSON()),
        sa.Column('procedure_interest', sa.String(200)),
        sa.Column('tags', sa.JSON()),
        sa.Column('deal_id', sa.String(), sa.ForeignKey('pipeline_deals.id'), nullable=True),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_leads_clinic_id', 'leads', ['clinic_id'])
    op.create_index('ix_leads_phone', 'leads', ['phone'])
    op.create_index('ix_leads_status', 'leads', ['status'])

    # --- WhatsApp Config ---
    op.create_table(
        'whatsapp_configs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False, unique=True),
        sa.Column('phone_number_id', sa.String(50)),
        sa.Column('waba_id', sa.String(50)),
        sa.Column('access_token', sa.Text()),
        sa.Column('business_name', sa.String(200)),
        sa.Column('business_phone', sa.String(20)),
        sa.Column('webhook_verify_token', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), server_default='false'),
        sa.Column('connected_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- AI Employee ---
    op.create_table(
        'ai_employees',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False, unique=True),
        sa.Column('name', sa.String(200), server_default='Clinic Assistant'),
        sa.Column('system_prompt', sa.Text()),
        sa.Column('greeting_message', sa.Text()),
        sa.Column('after_hours_message', sa.Text()),
        sa.Column('business_hours', sa.JSON()),
        sa.Column('procedures_offered', sa.JSON()),
        sa.Column('clinic_address', sa.Text()),
        sa.Column('clinic_phone', sa.String(20)),
        sa.Column('booking_link', sa.String(500)),
        sa.Column('doctor_name', sa.String(200)),
        sa.Column('tone', sa.String(50), server_default='professional'),
        sa.Column('language', sa.String(50), server_default='english'),
        sa.Column('auto_reply_enabled', sa.Boolean(), server_default='true'),
        sa.Column('followup_enabled', sa.Boolean(), server_default='true'),
        sa.Column('max_messages_before_handoff', sa.Integer(), server_default='15'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- WhatsApp Conversations ---
    op.create_table(
        'whatsapp_conversations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('wa_phone', sa.String(20), nullable=False),
        sa.Column('contact_name', sa.String(200)),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('is_ai_handling', sa.Boolean(), server_default='true'),
        sa.Column('ai_message_count', sa.Integer(), server_default='0'),
        sa.Column('assigned_agent_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('unread_count', sa.Integer(), server_default='0'),
        sa.Column('last_message_at', sa.DateTime()),
        sa.Column('last_message_preview', sa.String(200)),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_wa_conversations_clinic', 'whatsapp_conversations', ['clinic_id'])
    op.create_index('ix_wa_conversations_phone', 'whatsapp_conversations', ['clinic_id', 'wa_phone'])

    # --- WhatsApp Messages ---
    op.create_table(
        'whatsapp_messages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('conversation_id', sa.String(), sa.ForeignKey('whatsapp_conversations.id'), nullable=False),
        sa.Column('direction', sa.String(20), nullable=False),
        sa.Column('message_type', sa.String(50), server_default='text'),
        sa.Column('content', sa.Text()),
        sa.Column('media_url', sa.Text()),
        sa.Column('wa_message_id', sa.String(100)),
        sa.Column('sender_type', sa.String(50), server_default='lead'),
        sa.Column('status', sa.String(50), server_default='sent'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_wa_messages_conversation', 'whatsapp_messages', ['conversation_id'])

    # --- Nurture Sequences ---
    op.create_table(
        'nurture_sequences',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('procedure_category', sa.String(100)),
        sa.Column('trigger_type', sa.String(50), server_default='manual'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_template', sa.Boolean(), server_default='false'),
        sa.Column('total_steps', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_nurture_sequences_clinic', 'nurture_sequences', ['clinic_id'])

    # --- Nurture Steps ---
    op.create_table(
        'nurture_steps',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('sequence_id', sa.String(), sa.ForeignKey('nurture_sequences.id'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('delay_hours', sa.Integer(), server_default='0'),
        sa.Column('delay_type', sa.String(20), server_default='hours'),
        sa.Column('message_template', sa.Text(), nullable=False),
        sa.Column('channel', sa.String(50), server_default='whatsapp'),
        sa.Column('step_type', sa.String(50), server_default='message'),
        sa.Column('is_ai_generated', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_nurture_steps_sequence', 'nurture_steps', ['sequence_id'])

    # --- Nurture Enrollments ---
    op.create_table(
        'nurture_enrollments',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=False),
        sa.Column('sequence_id', sa.String(), sa.ForeignKey('nurture_sequences.id'), nullable=False),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('current_step', sa.Integer(), server_default='0'),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('next_send_at', sa.DateTime()),
        sa.Column('metadata', sa.JSON()),
        sa.Column('enrolled_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
    )
    op.create_index('ix_nurture_enrollments_next_send', 'nurture_enrollments', ['status', 'next_send_at'])
    op.create_index('ix_nurture_enrollments_lead', 'nurture_enrollments', ['lead_id'])

    # --- Clinic API Keys ---
    op.create_table(
        'clinic_api_keys',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False, unique=True),
        sa.Column('api_key', sa.String(100), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime()),
    )

    # --- Meta Config ---
    op.create_table(
        'meta_configs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False, unique=True),
        sa.Column('access_token', sa.Text()),
        sa.Column('page_id', sa.String(50)),
        sa.Column('page_name', sa.String(200)),
        sa.Column('ad_account_id', sa.String(50)),
        sa.Column('connected_forms', sa.JSON()),
        sa.Column('is_active', sa.Boolean(), server_default='false'),
        sa.Column('connected_at', sa.DateTime()),
        sa.Column('token_expires_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- Social Accounts ---
    op.create_table(
        'social_accounts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('account_name', sa.String(200)),
        sa.Column('account_id', sa.String(100)),
        sa.Column('profile_url', sa.String(500)),
        sa.Column('profile_image_url', sa.String(500)),
        sa.Column('access_token', sa.Text()),
        sa.Column('refresh_token', sa.Text()),
        sa.Column('token_expires_at', sa.DateTime()),
        sa.Column('followers_count', sa.Integer(), server_default='0'),
        sa.Column('posts_count', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('connected_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- Social Posts ---
    op.create_table(
        'social_posts',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('created_by_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('media_urls', sa.JSON()),
        sa.Column('media_type', sa.String(50)),
        sa.Column('platforms', sa.JSON(), nullable=False),
        sa.Column('platform_specific', sa.JSON()),
        sa.Column('scheduled_at', sa.DateTime()),
        sa.Column('published_at', sa.DateTime()),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('published_urls', sa.JSON()),
        sa.Column('publish_errors', sa.JSON()),
        sa.Column('is_ai_generated', sa.Boolean(), server_default='false'),
        sa.Column('ai_prompt', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- Marketing Insights ---
    op.create_table(
        'marketing_insights',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('call_id', sa.String(), sa.ForeignKey('calls.id'), nullable=True),
        sa.Column('insight_type', sa.String(50)),
        sa.Column('category', sa.String(100)),
        sa.Column('title', sa.String(300)),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_quote', sa.Text()),
        sa.Column('is_used', sa.Boolean(), server_default='false'),
        sa.Column('used_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_marketing_insights_clinic', 'marketing_insights', ['clinic_id'])


def downgrade() -> None:
    op.drop_table('marketing_insights')
    op.drop_table('social_posts')
    op.drop_table('social_accounts')
    op.drop_table('meta_configs')
    op.drop_table('clinic_api_keys')
    op.drop_table('nurture_enrollments')
    op.drop_table('nurture_steps')
    op.drop_table('nurture_sequences')
    op.drop_table('whatsapp_messages')
    op.drop_table('whatsapp_conversations')
    op.drop_table('ai_employees')
    op.drop_table('whatsapp_configs')
    op.drop_table('leads')
