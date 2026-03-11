"""expanded crm features - unified messaging, contact management, hiring, video consultations, clinic operations

Revision ID: c4d7f8e92b3a
Revises: b3c9e5f72a1d
Create Date: 2026-03-11 18:00:00.000000

Changes:
- Create unified_conversations table (multi-channel inbox)
- Create unified_messages table (messages from all platforms)
- Create contact_activities table (activity timeline)
- Create contact_tags table (tagging system)
- Create contact_tag_assignments association table
- Create contact_reminders table (follow-up reminders)
- Create contact_tasks table (tasks for contacts)
- Create hiring_positions table (job openings)
- Create hiring_candidates table (applicant tracking)
- Create hiring_interviews table (interview records)
- Create video_consultations table (video consultation tracking)
- Create invoices table (billing)
- Create inventory_items table (clinic inventory)
- Create patient_records table (patient information)
- Create ad_performance table (ad metrics)
- Create weekly_ad_reports table (ad analytics)
- Create ai_content_generation table (generated content)
- Create clinic_documents table (legal documents)
- Create finance_records table (financial records)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d7f8e92b3a'
down_revision: Union[str, None] = 'b3c9e5f72a1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Unified Conversations ---
    op.create_table(
        'unified_conversations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('contact_name', sa.String(200)),
        sa.Column('contact_phone', sa.String(20)),
        sa.Column('contact_email', sa.String(200)),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('platform_account_id', sa.String(200)),
        sa.Column('external_thread_id', sa.String(200)),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('unread_count', sa.Integer(), server_default='0'),
        sa.Column('last_message_at', sa.DateTime()),
        sa.Column('last_message_preview', sa.String(300)),
        sa.Column('assigned_agent_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('tags', sa.JSON()),
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_unified_conversations_clinic', 'unified_conversations', ['clinic_id'])
    op.create_index('ix_unified_conversations_platform', 'unified_conversations', ['platform'])

    # --- Unified Messages ---
    op.create_table(
        'unified_messages',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('conversation_id', sa.String(), sa.ForeignKey('unified_conversations.id'), nullable=False),
        sa.Column('direction', sa.String(20), nullable=False),
        sa.Column('content', sa.Text()),
        sa.Column('media_url', sa.Text()),
        sa.Column('media_type', sa.String(50)),
        sa.Column('sender_type', sa.String(50), server_default='contact'),
        sa.Column('sender_id', sa.String(200)),
        sa.Column('platform_message_id', sa.String(200)),
        sa.Column('status', sa.String(50), server_default='sent'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_unified_messages_conversation', 'unified_messages', ['conversation_id'])

    # --- Contact Activities ---
    op.create_table(
        'contact_activities',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=False),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('source_platform', sa.String(100)),
        sa.Column('source_url', sa.String(500)),
        sa.Column('extra_data', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_contact_activities_lead', 'contact_activities', ['lead_id'])
    op.create_index('ix_contact_activities_clinic', 'contact_activities', ['clinic_id'])

    # --- Contact Tags ---
    op.create_table(
        'contact_tags',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(7), server_default='#3B82F6'),
        sa.Column('category', sa.String(50), server_default='custom'),
        sa.Column('created_at', sa.DateTime()),
    )

    # --- Contact Tag Assignments (Association Table) ---
    op.create_table(
        'contact_tag_assignments',
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id')),
        sa.Column('tag_id', sa.String(), sa.ForeignKey('contact_tags.id')),
    )

    # --- Contact Reminders ---
    op.create_table(
        'contact_reminders',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('is_completed', sa.Boolean(), server_default='false'),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('priority', sa.String(20), server_default='medium'),
        sa.Column('reminder_type', sa.String(50), server_default='follow_up'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_contact_reminders_user', 'contact_reminders', ['user_id'])

    # --- Contact Tasks ---
    op.create_table(
        'contact_tasks',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('assigned_to_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('due_date', sa.DateTime()),
        sa.Column('status', sa.String(50), server_default='pending'),
        sa.Column('priority', sa.String(20), server_default='medium'),
        sa.Column('category', sa.String(50), server_default='sales'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
    )
    op.create_index('ix_contact_tasks_assigned', 'contact_tasks', ['assigned_to_id'])

    # --- Hiring Positions ---
    op.create_table(
        'hiring_positions',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('department', sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('requirements', sa.JSON()),
        sa.Column('salary_range', sa.String(100)),
        sa.Column('status', sa.String(50), server_default='open'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_hiring_positions_clinic', 'hiring_positions', ['clinic_id'])

    # --- Hiring Candidates ---
    op.create_table(
        'hiring_candidates',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('position_id', sa.String(), sa.ForeignKey('hiring_positions.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200)),
        sa.Column('phone', sa.String(20)),
        sa.Column('resume_url', sa.Text()),
        sa.Column('cover_letter', sa.Text()),
        sa.Column('status', sa.String(50), server_default='applied'),
        sa.Column('score', sa.Float(), server_default='0'),
        sa.Column('interview_notes', sa.JSON()),
        sa.Column('source', sa.String(50)),
        sa.Column('applied_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_hiring_candidates_position', 'hiring_candidates', ['position_id'])

    # --- Hiring Interviews ---
    op.create_table(
        'hiring_interviews',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('candidate_id', sa.String(), sa.ForeignKey('hiring_candidates.id'), nullable=False),
        sa.Column('interviewer_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('status', sa.String(50), server_default='scheduled'),
        sa.Column('score_card', sa.JSON()),
        sa.Column('notes', sa.Text()),
        sa.Column('recommendation', sa.String(50)),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_hiring_interviews_candidate', 'hiring_interviews', ['candidate_id'])

    # --- Video Consultations ---
    op.create_table(
        'video_consultations',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('doctor_name', sa.String(200)),
        sa.Column('patient_name', sa.String(200)),
        sa.Column('patient_phone', sa.String(20)),
        sa.Column('patient_email', sa.String(200)),
        sa.Column('meet_link', sa.String(500)),
        sa.Column('scheduled_at', sa.DateTime()),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('ended_at', sa.DateTime()),
        sa.Column('duration_minutes', sa.Integer()),
        sa.Column('status', sa.String(50), server_default='scheduled'),
        sa.Column('recording_url', sa.Text()),
        sa.Column('transcription', sa.Text()),
        sa.Column('ai_summary', sa.Text()),
        sa.Column('ai_suggestions', sa.JSON()),
        sa.Column('ai_key_points', sa.JSON()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_video_consultations_clinic', 'video_consultations', ['clinic_id'])

    # --- Invoices ---
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('invoice_number', sa.String(50), nullable=False),
        sa.Column('patient_name', sa.String(200)),
        sa.Column('patient_phone', sa.String(20)),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('subtotal', sa.Float(), server_default='0'),
        sa.Column('tax_percent', sa.Float(), server_default='0'),
        sa.Column('tax_amount', sa.Float(), server_default='0'),
        sa.Column('discount_percent', sa.Float(), server_default='0'),
        sa.Column('discount_amount', sa.Float(), server_default='0'),
        sa.Column('total', sa.Float(), server_default='0'),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('due_date', sa.DateTime()),
        sa.Column('paid_at', sa.DateTime()),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('notes', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_invoices_clinic', 'invoices', ['clinic_id'])

    # --- Inventory Items ---
    op.create_table(
        'inventory_items',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('sku', sa.String(100)),
        sa.Column('current_stock', sa.Integer(), server_default='0'),
        sa.Column('min_stock_level', sa.Integer(), server_default='0'),
        sa.Column('unit_price', sa.Float(), server_default='0'),
        sa.Column('supplier', sa.String(200)),
        sa.Column('last_restocked_at', sa.DateTime()),
        sa.Column('status', sa.String(50), server_default='in_stock'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- Patient Records ---
    op.create_table(
        'patient_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('lead_id', sa.String(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('email', sa.String(200)),
        sa.Column('date_of_birth', sa.DateTime()),
        sa.Column('gender', sa.String(20)),
        sa.Column('blood_group', sa.String(10)),
        sa.Column('allergies', sa.JSON()),
        sa.Column('medical_history', sa.JSON()),
        sa.Column('procedures_done', sa.JSON()),
        sa.Column('consent_forms', sa.JSON()),
        sa.Column('total_spent', sa.Float(), server_default='0'),
        sa.Column('visits_count', sa.Integer(), server_default='0'),
        sa.Column('last_visit_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_patient_records_clinic', 'patient_records', ['clinic_id'])

    # --- Ad Performance ---
    op.create_table(
        'ad_performance',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('campaign_id', sa.String(100)),
        sa.Column('campaign_name', sa.String(200)),
        sa.Column('ad_set_name', sa.String(200)),
        sa.Column('ad_name', sa.String(200)),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('ctr', sa.Float(), server_default='0'),
        sa.Column('cpc', sa.Float(), server_default='0'),
        sa.Column('spend', sa.Float(), server_default='0'),
        sa.Column('conversions', sa.Integer(), server_default='0'),
        sa.Column('cost_per_conversion', sa.Float(), server_default='0'),
        sa.Column('roas', sa.Float(), server_default='0'),
        sa.Column('ai_optimization_notes', sa.Text()),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_ad_performance_clinic', 'ad_performance', ['clinic_id'])

    # --- Weekly Ad Reports ---
    op.create_table(
        'weekly_ad_reports',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('week_start', sa.DateTime(), nullable=False),
        sa.Column('week_end', sa.DateTime(), nullable=False),
        sa.Column('total_spend', sa.Float(), server_default='0'),
        sa.Column('total_conversions', sa.Integer(), server_default='0'),
        sa.Column('avg_cpc', sa.Float(), server_default='0'),
        sa.Column('avg_ctr', sa.Float(), server_default='0'),
        sa.Column('avg_cost_per_conversion', sa.Float(), server_default='0'),
        sa.Column('top_campaigns', sa.JSON()),
        sa.Column('underperforming_campaigns', sa.JSON()),
        sa.Column('ai_recommendations', sa.JSON()),
        sa.Column('auto_generated', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime()),
    )

    # --- AI Content Generation ---
    op.create_table(
        'ai_content_generation',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('procedure_category', sa.String(100)),
        sa.Column('prompt_used', sa.Text()),
        sa.Column('generated_content', sa.Text()),
        sa.Column('status', sa.String(50), server_default='generated'),
        sa.Column('score', sa.Float(), server_default='0'),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- Clinic Documents ---
    op.create_table(
        'clinic_documents',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('file_url', sa.Text()),
        sa.Column('status', sa.String(50), server_default='draft'),
        sa.Column('valid_until', sa.DateTime()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )

    # --- Finance Records ---
    op.create_table(
        'finance_records',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('clinic_id', sa.String(), sa.ForeignKey('clinics.id'), nullable=False),
        sa.Column('record_type', sa.String(50), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('reference_number', sa.String(100)),
        sa.Column('created_at', sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table('finance_records')
    op.drop_table('clinic_documents')
    op.drop_table('ai_content_generation')
    op.drop_table('weekly_ad_reports')
    op.drop_table('ad_performance')
    op.drop_table('patient_records')
    op.drop_table('inventory_items')
    op.drop_table('invoices')
    op.drop_table('video_consultations')
    op.drop_table('hiring_interviews')
    op.drop_table('hiring_candidates')
    op.drop_table('hiring_positions')
    op.drop_table('contact_tasks')
    op.drop_table('contact_reminders')
    op.drop_table('contact_tag_assignments')
    op.drop_table('contact_tags')
    op.drop_table('contact_activities')
    op.drop_table('unified_messages')
    op.drop_table('unified_conversations')
