"""
CallCoach CRM - Expanded Models
Unified Inbox, Conversations, Contact Management, Hiring, Video Consultation,
Clinic Operations (Billing, Inventory, Patient Records), Marketing Automation, Legal & Finance
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Table, Enum
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# ============================================================================
# ASSOCIATION TABLES
# ============================================================================

# Association table for contact tag assignments
contact_tag_assignments = Table(
    "contact_tag_assignments", Base.metadata,
    Column("lead_id", String, ForeignKey("leads.id")),
    Column("tag_id", String, ForeignKey("contact_tags.id"))
)


# ============================================================================
# 1. UNIFIED INBOX / CONVERSATIONS
# ============================================================================

class UnifiedConversation(Base):
    __tablename__ = "unified_conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    # Contact info
    contact_name = Column(String(200))
    contact_phone = Column(String(20))
    contact_email = Column(String(200))

    # Platform info
    platform = Column(String(50), nullable=False)  # whatsapp, instagram, facebook, linkedin, x, snapchat, email
    platform_account_id = Column(String(200))  # clinic's account ID on that platform
    external_thread_id = Column(String(200))  # conversation/thread ID from the platform

    # Conversation status
    status = Column(String(50), default="active")  # active, archived, closed, spam
    unread_count = Column(Integer, default=0)
    last_message_at = Column(DateTime)
    last_message_preview = Column(String(300))

    # Assignment
    assigned_agent_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Metadata
    tags = Column(JSON, default=list)  # custom tags for organization
    is_archived = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="unified_conversations")
    messages = relationship("UnifiedMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="UnifiedMessage.created_at")


class UnifiedMessage(Base):
    __tablename__ = "unified_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("unified_conversations.id"), nullable=False)

    # Message content
    direction = Column(String(20), nullable=False)  # inbound, outbound
    content = Column(Text)
    media_url = Column(Text)
    media_type = Column(String(50))  # image, video, document, audio, etc.

    # Sender info
    sender_type = Column(String(50), default="contact")  # contact, agent, ai
    sender_id = Column(String(200))  # agent_id or AI ID or contact identifier

    # Platform-specific
    platform_message_id = Column(String(200))  # message ID from the platform
    status = Column(String(50), default="sent")  # sent, delivered, read, failed

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("UnifiedConversation", back_populates="messages")


# ============================================================================
# 2. CONTACT ACTIVITY, TAGS, REMINDERS & TASKS
# ============================================================================

class ContactActivity(Base):
    __tablename__ = "contact_activities"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)

    # Activity details
    activity_type = Column(String(50), nullable=False)  # call, message, form_submit, page_visit, email_open, ad_click, stage_change, note
    description = Column(Text)
    source_platform = Column(String(100))  # whatsapp, instagram, website, email, etc.
    source_url = Column(String(500))

    # Additional data
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="activities")


class ContactTag(Base):
    __tablename__ = "contact_tags"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#3B82F6")  # hex color
    category = Column(String(50), default="custom")  # lead_status, procedure, source, custom

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    leads = relationship("Lead", secondary=contact_tag_assignments, backref="contact_tags")


class ContactReminder(Base):
    __tablename__ = "contact_reminders"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Reminder details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime, nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)

    # Priority & type
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    reminder_type = Column(String(50), default="follow_up")  # follow_up, callback, consultation, task, custom

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="reminders")
    user = relationship("User", backref="reminders")


class ContactTask(Base):
    __tablename__ = "contact_tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)
    assigned_to_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Task details
    title = Column(String(300), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)

    # Status & priority
    status = Column(String(50), default="pending")  # pending, in_progress, completed, cancelled
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    category = Column(String(50), default="sales")  # sales, marketing, operations, admin

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    lead = relationship("Lead", backref="tasks")
    assigned_to = relationship("User", backref="assigned_tasks")


# ============================================================================
# 3. HIRING SECTION
# ============================================================================

class HiringPosition(Base):
    __tablename__ = "hiring_positions"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Position details
    title = Column(String(200), nullable=False)
    department = Column(String(50), nullable=False)  # marketing, sales, operations, content, editing, intern
    description = Column(Text)
    requirements = Column(JSON, default=list)  # list of required qualifications

    # Compensation & status
    salary_range = Column(String(100))  # e.g., "50000-70000"
    status = Column(String(50), default="open")  # open, interviewing, filled, closed

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidates = relationship("HiringCandidate", back_populates="position", cascade="all, delete-orphan")


class HiringCandidate(Base):
    __tablename__ = "hiring_candidates"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    position_id = Column(String, ForeignKey("hiring_positions.id"), nullable=False)

    # Candidate info
    name = Column(String(200), nullable=False)
    email = Column(String(200))
    phone = Column(String(20))
    resume_url = Column(Text)
    cover_letter = Column(Text)

    # Status & scoring
    status = Column(String(50), default="applied")  # applied, screening, interview_scheduled, interview_done, offer_sent, hired, rejected
    score = Column(Float, default=0)  # 0-100
    interview_notes = Column(JSON, default=dict)

    # Recruitment info
    source = Column(String(50))  # referral, linkedin, job_board, direct
    applied_at = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    position = relationship("HiringPosition", back_populates="candidates")
    interviews = relationship("HiringInterview", back_populates="candidate", cascade="all, delete-orphan")


class HiringInterview(Base):
    __tablename__ = "hiring_interviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    candidate_id = Column(String, ForeignKey("hiring_candidates.id"), nullable=False)
    interviewer_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Interview details
    scheduled_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled

    # Scoring & feedback
    score_card = Column(JSON, default=dict)  # {dimension: score, ...}
    notes = Column(Text)
    recommendation = Column(String(50))  # strong_yes, yes, maybe, no, strong_no

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("HiringCandidate", back_populates="interviews")
    interviewer = relationship("User", backref="interviews_conducted")


# ============================================================================
# 4. VIDEO CONSULTATION
# ============================================================================

class VideoConsultation(Base):
    __tablename__ = "video_consultations"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    # Consultation details
    doctor_name = Column(String(200))
    patient_name = Column(String(200))
    patient_phone = Column(String(20))
    patient_email = Column(String(200))

    # Meeting info
    meet_link = Column(String(500))
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_minutes = Column(Integer)

    # Status
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled, no_show

    # Recording & analysis
    recording_url = Column(Text)
    transcription = Column(Text)
    ai_summary = Column(Text)
    ai_suggestions = Column(JSON, default=dict)  # {suggestion: description, ...}
    ai_key_points = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="video_consultations")


# ============================================================================
# 5. CLINIC OPERATIONS - BILLING
# ============================================================================

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    # Invoice details
    invoice_number = Column(String(50), nullable=False)
    patient_name = Column(String(200))
    patient_phone = Column(String(20))

    # Items
    items = Column(JSON, nullable=False, default=list)  # [{description, quantity, unit_price, total}, ...]

    # Calculations
    subtotal = Column(Float, default=0)
    tax_percent = Column(Float, default=0)
    tax_amount = Column(Float, default=0)
    discount_percent = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    total = Column(Float, default=0)

    # Payment & status
    status = Column(String(50), default="draft")  # draft, sent, paid, overdue, cancelled
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    payment_method = Column(String(50))  # cash, card, bank_transfer, upi, etc.

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="invoices")


# ============================================================================
# 6. CLINIC OPERATIONS - INVENTORY
# ============================================================================

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Item details
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)  # consumable, equipment, medicine, skincare
    sku = Column(String(100))

    # Stock management
    current_stock = Column(Integer, default=0)
    min_stock_level = Column(Integer, default=0)
    unit_price = Column(Float, default=0)

    # Supplier & status
    supplier = Column(String(200))
    last_restocked_at = Column(DateTime)
    status = Column(String(50), default="in_stock")  # in_stock, low_stock, out_of_stock

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# 7. CLINIC OPERATIONS - PATIENT RECORDS
# ============================================================================

class PatientRecord(Base):
    __tablename__ = "patient_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    # Personal info
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    email = Column(String(200))
    date_of_birth = Column(DateTime)
    gender = Column(String(20))

    # Medical info
    blood_group = Column(String(10))
    allergies = Column(JSON, default=list)
    medical_history = Column(JSON, default=dict)

    # Treatment records
    procedures_done = Column(JSON, default=list)  # [{procedure, date, doctor, notes, before_photos, after_photos}, ...]
    consent_forms = Column(JSON, default=list)  # list of consent form URLs or data

    # Statistics
    total_spent = Column(Float, default=0)
    visits_count = Column(Integer, default=0)
    last_visit_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", backref="patient_records")


# ============================================================================
# 8. MARKETING AUTOMATION - AD PERFORMANCE
# ============================================================================

class AdPerformance(Base):
    __tablename__ = "ad_performance"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Ad details
    platform = Column(String(50), nullable=False)  # meta, google
    campaign_id = Column(String(100))
    campaign_name = Column(String(200))
    ad_set_name = Column(String(200))
    ad_name = Column(String(200))

    # Date
    date = Column(DateTime, nullable=False)

    # Performance metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0)  # click-through rate
    cpc = Column(Float, default=0)  # cost per click
    spend = Column(Float, default=0)
    conversions = Column(Integer, default=0)
    cost_per_conversion = Column(Float, default=0)
    roas = Column(Float, default=0)  # return on ad spend

    # AI analysis
    ai_optimization_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", backref="ad_performance")


class WeeklyAdReport(Base):
    __tablename__ = "weekly_ad_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Period & platform
    platform = Column(String(50), nullable=False)  # meta, google
    week_start = Column(DateTime, nullable=False)
    week_end = Column(DateTime, nullable=False)

    # Aggregated metrics
    total_spend = Column(Float, default=0)
    total_conversions = Column(Integer, default=0)
    avg_cpc = Column(Float, default=0)
    avg_ctr = Column(Float, default=0)
    avg_cost_per_conversion = Column(Float, default=0)

    # Campaign analysis
    top_campaigns = Column(JSON, default=list)  # [{name, spend, conversions, roas}, ...]
    underperforming_campaigns = Column(JSON, default=list)

    # AI recommendations
    ai_recommendations = Column(JSON, default=list)

    auto_generated = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", backref="weekly_ad_reports")


# ============================================================================
# 9. MARKETING AUTOMATION - CONTENT GENERATION
# ============================================================================

class AIContentGeneration(Base):
    __tablename__ = "ai_content_generation"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Content details
    content_type = Column(String(50), nullable=False)  # video_script, image_ad, carousel, ugc_script, organic_post, blog
    procedure_category = Column(String(100))

    # Generation info
    prompt_used = Column(Text)
    generated_content = Column(Text)
    status = Column(String(50), default="generated")  # generated, approved, rejected, published
    score = Column(Float, default=0)  # 0-100 quality score

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", backref="ai_content_generations")


# ============================================================================
# 10. LEGAL & FINANCE
# ============================================================================

class ClinicDocument(Base):
    __tablename__ = "clinic_documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Document details
    title = Column(String(300), nullable=False)
    document_type = Column(String(50), nullable=False)  # contract, agreement, nda, consent_form, policy, license
    file_url = Column(Text)

    # Status & validity
    status = Column(String(50), default="draft")  # draft, active, expired, archived
    valid_until = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", backref="documents")


class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Record type & category
    record_type = Column(String(50), nullable=False)  # income, expense
    category = Column(String(100), nullable=False)  # ad_spend, salary, rent, equipment, marketing, consultation_fee, treatment_fee, product_sale

    # Financial details
    amount = Column(Float, nullable=False)
    description = Column(Text)
    date = Column(DateTime, nullable=False)
    payment_method = Column(String(50))  # cash, card, bank_transfer, upi, etc.
    reference_number = Column(String(100))  # invoice number, receipt number, etc.

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", backref="finance_records")


# ============================================================================
# MISSING MODELS & ALIASES FOR V2.1 ROUTERS
# ============================================================================

import enum

class ConversationPlatform(str, enum.Enum):
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    X = "x"
    SNAPCHAT = "snapchat"

# Aliases for inbox_router.py compatibility
Conversation = UnifiedConversation
ConversationMessage = UnifiedMessage


# ============================================================================
# CONSULTATION TRANSCRIPTION & ANALYSIS (consultations_router.py)
# ============================================================================

class ConsultationTranscription(Base):
    __tablename__ = "consultation_transcriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    consultation_id = Column(String, ForeignKey("video_consultations.id"), nullable=False)
    content = Column(Text)
    language = Column(String(10), default="en")
    duration_seconds = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    consultation = relationship("VideoConsultation", backref="transcriptions")


class ConsultationAnalysis(Base):
    __tablename__ = "consultation_analyses"

    id = Column(String, primary_key=True, default=generate_uuid)
    consultation_id = Column(String, ForeignKey("video_consultations.id"), nullable=False)
    summary = Column(Text)
    key_concerns = Column(JSON, default=list)
    recommended_procedures = Column(JSON, default=list)
    follow_up_actions = Column(JSON, default=list)
    sentiment_score = Column(Float)
    ai_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    consultation = relationship("VideoConsultation", backref="analyses")


# ============================================================================
# PATIENT PROCEDURE HISTORY (operations_router.py)
# ============================================================================

class PatientProcedureHistory(Base):
    __tablename__ = "patient_procedure_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    patient_id = Column(String, ForeignKey("patient_records.id"), nullable=False)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    procedure_name = Column(String(200), nullable=False)
    procedure_date = Column(DateTime, nullable=False)
    doctor_name = Column(String(200))
    notes = Column(Text)
    cost = Column(Float)
    outcome = Column(String(100))  # successful, follow_up_needed, complications
    before_photos = Column(JSON, default=list)
    after_photos = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("PatientRecord", backref="procedure_history")


# ============================================================================
# GENERATED CONTENT / AI CONTENT (marketing_router.py)
# ============================================================================

# Alias for marketing_router.py compatibility
GeneratedContent = AIContentGeneration


# ============================================================================
# LEGAL DOCUMENT (legal_finance_router.py)
# ============================================================================

# Alias for legal_finance_router.py compatibility
LegalDocument = ClinicDocument
