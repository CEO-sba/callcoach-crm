"""
CallCoach CRM - WhatsApp, Leads, Nurture, Social Media & Meta Models
"""
import uuid
import secrets
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def generate_api_key():
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# Lead (Central model - ties WhatsApp, forms, calls, Meta together)
# ---------------------------------------------------------------------------
class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Contact info
    name = Column(String(200))
    phone = Column(String(20))
    email = Column(String(200))

    # Source tracking
    source = Column(String(50), default="manual")  # whatsapp, form_google, form_meta, meta_lead_form, call, walk_in, manual
    campaign_name = Column(String(200))
    campaign_source = Column(String(50))  # google, meta, organic, direct
    campaign_medium = Column(String(50))  # cpc, social, email
    campaign_content = Column(String(200))

    # Scoring & status
    lead_score = Column(Integer, default=0)  # 0-100
    status = Column(String(50), default="new")  # new, contacted, qualified, consultation_booked, converted, lost
    lost_reason = Column(Text)

    # Assignment
    assigned_agent_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Form data
    form_data = Column(JSON)  # raw form field responses
    procedure_interest = Column(String(200))  # hair_transplant, botox, etc.

    # Tags
    tags = Column(JSON, default=list)  # ["hot", "callback", "price_sensitive"]

    # Linked deal
    deal_id = Column(String, ForeignKey("pipeline_deals.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    conversations = relationship("WhatsAppConversation", back_populates="lead")
    nurture_enrollments = relationship("NurtureEnrollment", back_populates="lead")


# ---------------------------------------------------------------------------
# WhatsApp Config (per clinic - stores API credentials)
# ---------------------------------------------------------------------------
class WhatsAppConfig(Base):
    __tablename__ = "whatsapp_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False, unique=True)

    # Meta WhatsApp Cloud API credentials
    phone_number_id = Column(String(50))
    waba_id = Column(String(50))  # WhatsApp Business Account ID
    access_token = Column(Text)  # permanent token from System User

    # Business info for display
    business_name = Column(String(200))
    business_phone = Column(String(20))  # display phone number

    # Webhook security
    webhook_verify_token = Column(String(100), default=lambda: secrets.token_urlsafe(24))

    is_active = Column(Boolean, default=False)
    connected_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# AI Employee (per clinic - chatbot config)
# ---------------------------------------------------------------------------
class AIEmployee(Base):
    __tablename__ = "ai_employees"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False, unique=True)

    # Identity
    name = Column(String(200), default="Clinic Assistant")

    # Prompt & behavior
    system_prompt = Column(Text)  # auto-generated, user can customize
    greeting_message = Column(Text, default="Hello! Thank you for reaching out. How can I help you today?")
    after_hours_message = Column(Text, default="Thank you for your message. Our team is currently unavailable but we'll get back to you first thing in the morning. Is there anything specific you'd like us to address?")

    # Business config
    business_hours = Column(JSON, default=lambda: {"start": "09:00", "end": "19:00", "days": [1, 2, 3, 4, 5, 6]})  # Mon=1, Sun=7
    procedures_offered = Column(JSON, default=list)  # [{name, description, price_range, duration}]
    clinic_address = Column(Text)
    clinic_phone = Column(String(20))
    booking_link = Column(String(500))
    doctor_name = Column(String(200))

    # Behavior settings
    tone = Column(String(50), default="professional")  # professional, friendly, warm
    language = Column(String(50), default="english")  # english, hindi, hinglish
    auto_reply_enabled = Column(Boolean, default=True)
    followup_enabled = Column(Boolean, default=True)
    max_messages_before_handoff = Column(Integer, default=15)

    # Advanced Personalization (makes the AI feel like an extension of the clinic)
    personality_traits = Column(JSON, default=list)  # e.g. ["empathetic", "knowledgeable", "reassuring", "cheerful"]
    brand_voice_description = Column(Text)  # Free-text description of how the clinic communicates
    custom_faqs = Column(JSON, default=list)  # [{question, answer}] - clinic-specific knowledge base
    objection_responses = Column(JSON, default=list)  # [{objection, response}] - pre-trained objection handling
    usp_points = Column(JSON, default=list)  # ["15+ years experience", "10000+ patients treated"] - unique selling points
    competitor_differentiators = Column(Text)  # How to position against competitors if patients compare
    follow_up_style = Column(String(50), default="gentle")  # gentle, assertive, educational
    emoji_usage = Column(String(50), default="moderate")  # none, minimal, moderate, expressive
    message_length_preference = Column(String(50), default="concise")  # concise, balanced, detailed
    qualification_questions = Column(JSON, default=list)  # Questions to naturally ask to qualify leads
    escalation_triggers = Column(JSON, default=list)  # Keywords/phrases that trigger human handoff
    special_instructions = Column(Text)  # Any additional clinic-specific instructions
    welcome_offer = Column(Text)  # Special offer to mention for first-time inquiries
    doctor_credentials = Column(Text)  # Full doctor credentials to mention when building authority
    success_stories = Column(JSON, default=list)  # [{procedure, story_summary}] - anonymized success stories for social proof
    banned_phrases = Column(JSON, default=list)  # Phrases the AI should never use
    preferred_phrases = Column(JSON, default=list)  # Phrases the clinic wants the AI to use

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# WhatsApp Conversation
# ---------------------------------------------------------------------------
class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=True)

    # Contact
    wa_phone = Column(String(20), nullable=False)  # contact's WhatsApp number
    contact_name = Column(String(200))

    # Status
    status = Column(String(50), default="active")  # active, handed_off, closed
    is_ai_handling = Column(Boolean, default=True)
    ai_message_count = Column(Integer, default=0)  # track AI messages sent in this convo

    # Assignment
    assigned_agent_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Metadata
    unread_count = Column(Integer, default=0)
    last_message_at = Column(DateTime)
    last_message_preview = Column(String(200))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="conversations")
    messages = relationship("WhatsAppMessage", back_populates="conversation", order_by="WhatsAppMessage.created_at")


# ---------------------------------------------------------------------------
# WhatsApp Message
# ---------------------------------------------------------------------------
class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("whatsapp_conversations.id"), nullable=False)

    # Message details
    direction = Column(String(20), nullable=False)  # inbound, outbound
    message_type = Column(String(50), default="text")  # text, image, document, audio, video, template
    content = Column(Text)
    media_url = Column(Text)

    # WhatsApp metadata
    wa_message_id = Column(String(100))  # Meta's message ID
    sender_type = Column(String(50), default="lead")  # lead, ai_employee, agent
    status = Column(String(50), default="sent")  # sent, delivered, read, failed

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("WhatsAppConversation", back_populates="messages")


# ---------------------------------------------------------------------------
# Nurture Sequence
# ---------------------------------------------------------------------------
class NurtureSequence(Base):
    __tablename__ = "nurture_sequences"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)  # NULL for global templates

    name = Column(String(200), nullable=False)
    description = Column(Text)
    procedure_category = Column(String(100))  # hair_transplant, rhinoplasty, botox, etc.

    # Trigger
    trigger_type = Column(String(50), default="manual")  # form_submit, whatsapp_first_message, manual, lead_created

    # Status
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)  # True = pre-built template, False = custom
    total_steps = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = relationship("NurtureStep", back_populates="sequence", order_by="NurtureStep.step_number")
    enrollments = relationship("NurtureEnrollment", back_populates="sequence")


# ---------------------------------------------------------------------------
# Nurture Step
# ---------------------------------------------------------------------------
class NurtureStep(Base):
    __tablename__ = "nurture_steps"

    id = Column(String, primary_key=True, default=generate_uuid)
    sequence_id = Column(String, ForeignKey("nurture_sequences.id"), nullable=False)

    step_number = Column(Integer, nullable=False)
    delay_hours = Column(Integer, default=0)  # hours after previous step (or enrollment)
    delay_type = Column(String(20), default="hours")  # hours, days, weeks (for display)

    # Message
    message_template = Column(Text, nullable=False)  # supports {name}, {procedure}, {clinic_name}, {doctor_name}, {booking_link}
    channel = Column(String(50), default="whatsapp")  # whatsapp, email

    # Type
    step_type = Column(String(50), default="message")  # message, wait, condition
    is_ai_generated = Column(Boolean, default=False)  # If True, Claude personalizes at send time

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sequence = relationship("NurtureSequence", back_populates="steps")


# ---------------------------------------------------------------------------
# Nurture Enrollment (tracks which leads are in which sequences)
# ---------------------------------------------------------------------------
class NurtureEnrollment(Base):
    __tablename__ = "nurture_enrollments"

    id = Column(String, primary_key=True, default=generate_uuid)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    sequence_id = Column(String, ForeignKey("nurture_sequences.id"), nullable=False)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Progress
    current_step = Column(Integer, default=0)  # 0 = not started yet
    status = Column(String(50), default="active")  # active, paused, completed, cancelled
    next_send_at = Column(DateTime)

    # Personalization data
    personalization_data = Column(JSON, default=dict)  # {name, procedure, clinic_name, doctor_name, booking_link, phone}

    enrolled_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    lead = relationship("Lead", back_populates="nurture_enrollments")
    sequence = relationship("NurtureSequence", back_populates="enrollments")


# ---------------------------------------------------------------------------
# Clinic API Key (for webhook authentication)
# ---------------------------------------------------------------------------
class ClinicApiKey(Base):
    __tablename__ = "clinic_api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False, unique=True)
    api_key = Column(String(100), nullable=False, unique=True, default=generate_api_key)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# API Key (for lead webhooks and external integrations)
# ---------------------------------------------------------------------------
class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)

    name = Column(String(200), nullable=False)  # e.g., "Lead Webhook", "Website Integration"
    description = Column(Text)  # description of what this key is used for
    key = Column(String(100), nullable=False, unique=True, default=generate_api_key)

    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", foreign_keys=[clinic_id])
    created_by = relationship("User", foreign_keys=[created_by_id])


# ---------------------------------------------------------------------------
# Meta Integration Config (per clinic)
# ---------------------------------------------------------------------------
class MetaConfig(Base):
    __tablename__ = "meta_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False, unique=True)

    # OAuth tokens
    access_token = Column(Text)
    page_id = Column(String(50))
    page_name = Column(String(200))
    ad_account_id = Column(String(50))

    # Connected forms
    connected_forms = Column(JSON, default=list)  # [{form_id, form_name, page_id}]

    is_active = Column(Boolean, default=False)
    connected_at = Column(DateTime)
    token_expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Social Media Account
# ---------------------------------------------------------------------------
class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    platform = Column(String(50), nullable=False)  # instagram, facebook, youtube, linkedin, twitter, snapchat
    account_name = Column(String(200))
    account_id = Column(String(100))  # platform-specific account ID
    profile_url = Column(String(500))
    profile_image_url = Column(String(500))

    # Auth
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)

    # Stats (cached)
    followers_count = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    connected_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Social Media Post
# ---------------------------------------------------------------------------
class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Content
    content = Column(Text, nullable=False)
    media_urls = Column(JSON, default=list)  # list of image/video URLs
    media_type = Column(String(50))  # image, video, carousel, text_only

    # Targeting
    platforms = Column(JSON, nullable=False)  # ["instagram", "facebook", "linkedin"]
    platform_specific = Column(JSON, default=dict)  # per-platform overrides {instagram: {hashtags: [...]}, ...}

    # Scheduling
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    status = Column(String(50), default="draft")  # draft, scheduled, publishing, published, failed

    # Results
    published_urls = Column(JSON, default=dict)  # {instagram: "url", facebook: "url"}
    publish_errors = Column(JSON, default=dict)  # {platform: "error message"}

    # AI generated
    is_ai_generated = Column(Boolean, default=False)
    ai_prompt = Column(Text)  # prompt used to generate

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Marketing Insight (AI-generated from call data)
# ---------------------------------------------------------------------------
class MarketingInsight(Base):
    __tablename__ = "marketing_insights"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    call_id = Column(String, ForeignKey("calls.id"), nullable=True)

    insight_type = Column(String(50))  # ad_angle, content_idea, objection_pattern, faq, testimonial_theme
    category = Column(String(100))  # procedure category
    title = Column(String(300))
    content = Column(Text, nullable=False)
    source_quote = Column(Text)  # relevant quote from call transcript

    # Usage tracking
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
