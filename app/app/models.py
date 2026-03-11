"""
CallCoach CRM - Database Models
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum, JSON, Table
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# Association table for call tags
call_tags = Table(
    "call_tags", Base.metadata,
    Column("call_id", String, ForeignKey("calls.id")),
    Column("tag_id", String, ForeignKey("tags.id"))
)


class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    phone = Column(String(20))
    email = Column(String(200))
    address = Column(Text)
    city = Column(String(100))
    specialty = Column(String(100))  # dermatology, aesthetics, hair_transplant, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    leaderboard_visible = Column(Boolean, default=True)  # Toggle leaderboard visibility for agents
    settings = Column(JSON, default=dict)  # Stores activity_logs, gmb config, backlinks, google_ads config, etc.

    users = relationship("User", back_populates="clinic")
    calls = relationship("Call", back_populates="clinic")
    deals = relationship("PipelineDeal", back_populates="clinic")
    weekly_reports = relationship("WeeklyReport", back_populates="clinic")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=True)  # NULL for super admins
    email = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(50), default="agent")  # admin, manager, agent
    is_super_admin = Column(Boolean, default=False)  # Platform-level super admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    clinic = relationship("Clinic", back_populates="users")
    calls = relationship("Call", back_populates="agent")
    coaching_insights = relationship("CoachingInsight", back_populates="user")


class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    agent_id = Column(String, ForeignKey("users.id"), nullable=False)
    deal_id = Column(String, ForeignKey("pipeline_deals.id"), nullable=True)

    # Call metadata
    caller_name = Column(String(200))
    caller_phone = Column(String(20))
    caller_email = Column(String(200))
    call_type = Column(String(50), default="inbound")  # inbound, outbound, follow_up
    direction = Column(String(20), default="inbound")  # inbound, outbound
    duration_seconds = Column(Integer, default=0)
    call_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="completed")  # completed, missed, voicemail, in_progress

    # Recording and transcription
    recording_path = Column(Text)
    transcription = Column(Text)
    transcription_status = Column(String(50), default="none")  # none, pending, processing, completed, failed
    transcription_segments = Column(JSON)  # timestamped segments

    # AI Analysis
    ai_summary = Column(Text)
    ai_sentiment = Column(String(50))  # positive, neutral, negative, mixed
    ai_intent = Column(String(100))  # booking, inquiry, complaint, follow_up, price_check
    ai_key_topics = Column(JSON)  # list of detected topics
    ai_action_items = Column(JSON)  # suggested next steps
    ai_objections_detected = Column(JSON)  # objections raised by caller
    ai_buying_signals = Column(JSON)  # buying signals detected

    # Scoring
    overall_score = Column(Float)  # 0-100

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", back_populates="calls")
    agent = relationship("User", back_populates="calls")
    deal = relationship("PipelineDeal", back_populates="calls")
    notes = relationship("CallNote", back_populates="call", cascade="all, delete-orphan")
    scores = relationship("CallScore", back_populates="call", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=call_tags, back_populates="calls")
    coaching_insights = relationship("CoachingInsight", back_populates="call", cascade="all, delete-orphan")


class CallNote(Base):
    __tablename__ = "call_notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    call_id = Column(String, ForeignKey("calls.id"), nullable=False)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default="manual")  # manual, ai_generated, system
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="notes")


class CallScore(Base):
    __tablename__ = "call_scores"

    id = Column(String, primary_key=True, default=generate_uuid)
    call_id = Column(String, ForeignKey("calls.id"), nullable=False)

    # Individual scoring dimensions (0-100)
    greeting_score = Column(Float, default=0)
    discovery_score = Column(Float, default=0)  # needs identification
    presentation_score = Column(Float, default=0)  # solution presentation
    objection_handling_score = Column(Float, default=0)
    closing_score = Column(Float, default=0)
    rapport_score = Column(Float, default=0)
    active_listening_score = Column(Float, default=0)
    urgency_creation_score = Column(Float, default=0)
    follow_up_setup_score = Column(Float, default=0)
    overall_score = Column(Float, default=0)

    # AI feedback per dimension
    scoring_details = Column(JSON)  # detailed breakdown
    improvement_tips = Column(JSON)  # specific tips per area
    what_went_well = Column(JSON)  # positive highlights
    what_to_improve = Column(JSON)  # areas for improvement

    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="scores")


class PipelineDeal(Base):
    __tablename__ = "pipeline_deals"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Contact info
    contact_name = Column(String(200), nullable=False)
    contact_phone = Column(String(20))
    contact_email = Column(String(200))

    # Deal details
    title = Column(String(300), nullable=False)
    treatment_interest = Column(String(200))  # hair_transplant, botox, laser, etc.
    deal_value = Column(Float, default=0)
    stage = Column(String(50), default="new_inquiry")
    # Stages: new_inquiry -> contacted -> consultation_booked -> consultation_done -> proposal_sent -> won -> lost
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    source = Column(String(100))  # phone, walk_in, website, referral, social_media, ad

    # Status
    status = Column(String(50), default="open")  # open, won, lost, stale
    lost_reason = Column(Text)
    expected_close_date = Column(DateTime)
    actual_close_date = Column(DateTime)

    # Follow-up
    next_follow_up = Column(DateTime)
    follow_up_notes = Column(Text)
    total_calls = Column(Integer, default=0)
    total_touchpoints = Column(Integer, default=0)

    # AI insights
    ai_win_probability = Column(Float)  # 0-100
    ai_recommended_action = Column(Text)
    ai_deal_health = Column(String(50))  # healthy, at_risk, cold, hot

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", back_populates="deals")
    calls = relationship("Call", back_populates="deal")
    activities = relationship("DealActivity", back_populates="deal", cascade="all, delete-orphan")


class DealActivity(Base):
    __tablename__ = "deal_activities"

    id = Column(String, primary_key=True, default=generate_uuid)
    deal_id = Column(String, ForeignKey("pipeline_deals.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    activity_type = Column(String(50), nullable=False)  # call, note, stage_change, email, task
    description = Column(Text)
    extra_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    deal = relationship("PipelineDeal", back_populates="activities")


class CoachingInsight(Base):
    __tablename__ = "coaching_insights"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    call_id = Column(String, ForeignKey("calls.id"), nullable=True)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    insight_type = Column(String(50))  # tip, pattern, milestone, warning, praise
    category = Column(String(100))  # greeting, discovery, closing, objection_handling, etc.
    title = Column(String(300))
    content = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")  # low, medium, high
    is_read = Column(Boolean, default=False)

    # Progress tracking
    metric_name = Column(String(100))  # e.g., "closing_rate", "avg_call_score"
    metric_before = Column(Float)
    metric_after = Column(Float)
    metric_change_pct = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="coaching_insights")
    call = relationship("Call", back_populates="coaching_insights")


class LearningProgress(Base):
    __tablename__ = "learning_progress"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    module_id = Column(String(50), nullable=False)

    # Progress state
    status = Column(String(20), default="not_started")  # not_started, in_progress, completed
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Quiz results
    quiz_score = Column(Float)  # percentage 0-100
    quiz_attempts = Column(Integer, default=0)
    quiz_passed = Column(Boolean, default=False)
    quiz_answers = Column(JSON)  # last quiz attempt answers

    # Mock call results
    mock_score = Column(Float)  # percentage 0-100
    mock_attempts = Column(Integer, default=0)
    mock_feedback = Column(JSON)  # AI feedback on last mock attempt

    # Time tracking
    time_spent_minutes = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Certification(Base):
    __tablename__ = "certifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    certification_id = Column(String(50), nullable=False)  # cert_foundation, cert_advanced, cert_master
    title = Column(String(200), nullable=False)

    earned_at = Column(DateTime, default=datetime.utcnow)
    avg_quiz_score = Column(Float)
    avg_mock_score = Column(Float)
    total_modules_completed = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(7), default="#3B82F6")
    created_at = Column(DateTime, default=datetime.utcnow)

    calls = relationship("Call", secondary=call_tags, back_populates="tags")


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Week boundaries
    week_start = Column(DateTime, nullable=False)  # Monday of the week
    week_end = Column(DateTime, nullable=False)    # Sunday of the week

    # Core metrics
    total_calls = Column(Integer, default=0)
    avg_score = Column(Float, default=0)  # 0-100
    conversion_rate = Column(Float, default=0)  # percentage

    # Top performer
    top_agent_id = Column(String, ForeignKey("users.id"), nullable=True)
    top_agent_name = Column(String(200))

    # Detailed data
    calls_by_day = Column(JSON)  # {date: count}
    sentiment_distribution = Column(JSON)  # {sentiment: {count, percentage}}

    # AI-generated insights
    ai_summary = Column(JSON)  # {executive_summary, overall_trend, team_highlights, etc}
    ai_recommendations = Column(JSON)  # [top 3 recommendations with details]
    revenue_impact = Column(JSON)  # {estimated_weekly_impact, improvement_opportunity, etc}

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", back_populates="weekly_reports")
