"""
CallCoach CRM - Marketing Extended Models
Content Calendar, Creative Library, Market Research, AI Feedback, Campaign Workspace
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# ============================================================================
# CONTENT CALENDAR
# ============================================================================

class ContentCalendar(Base):
    __tablename__ = "content_calendars"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Calendar details
    month = Column(String(20), nullable=False)  # "2026-03"
    theme = Column(String(200))
    status = Column(String(50), default="draft")  # draft, active, completed
    total_posts = Column(Integer, default=0)

    # AI-generated calendar data
    calendar_data = Column(JSON, default=list)  # full calendar from AI
    content_mix = Column(JSON, default=dict)  # percentage breakdown
    notes = Column(Text)

    # Tracking
    posts_published = Column(Integer, default=0)
    posts_pending = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    clinic = relationship("Clinic", backref="content_calendars")


# ============================================================================
# CONTENT CALENDAR POSTS (individual post items from calendar)
# ============================================================================

class ContentCalendarPost(Base):
    __tablename__ = "content_calendar_posts"

    id = Column(String, primary_key=True, default=generate_uuid)
    calendar_id = Column(String, ForeignKey("content_calendars.id"), nullable=False)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Post details
    scheduled_date = Column(DateTime, nullable=False)
    platform = Column(String(50), nullable=False)  # instagram, facebook, youtube, linkedin, x, snapchat
    content_type = Column(String(50), nullable=False)  # reel, carousel, post, story, youtube, blog
    title = Column(String(300))
    description = Column(Text)
    procedure_focus = Column(String(200))
    funnel_stage = Column(String(50))  # awareness, consideration, decision

    # Content
    content_text = Column(Text)  # actual post content/script
    hashtags = Column(JSON, default=list)
    media_urls = Column(JSON, default=list)  # attached media

    # Status
    status = Column(String(50), default="planned")  # planned, content_ready, approved, published, skipped
    published_at = Column(DateTime)
    published_url = Column(Text)

    # Performance (filled after publishing)
    impressions = Column(Integer, default=0)
    engagement = Column(Integer, default=0)
    clicks = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    calendar = relationship("ContentCalendar", backref="posts")


# ============================================================================
# MARKET RESEARCH REPORTS
# ============================================================================

class MarketResearch(Base):
    __tablename__ = "market_research"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Research parameters
    city = Column(String(200))
    procedures = Column(JSON, default=list)
    competitors = Column(JSON, default=list)
    research_focus = Column(String(100))  # full, competitor, patient_psychology, ads, content_gap

    # AI research results
    research_data = Column(JSON, default=dict)  # full research output from AI
    market_overview = Column(JSON, default=dict)
    competitor_analysis = Column(JSON, default=list)
    patient_psychology = Column(JSON, default=dict)
    content_gaps = Column(JSON, default=list)
    ad_opportunities = Column(JSON, default=list)
    positioning_recommendations = Column(JSON, default=list)
    budget_allocation = Column(JSON, default=dict)

    # Status
    status = Column(String(50), default="completed")

    created_at = Column(DateTime, default=datetime.utcnow)

    clinic = relationship("Clinic", backref="market_research")


# ============================================================================
# AD CAMPAIGN WORKSPACE
# ============================================================================

class CampaignWorkspace(Base):
    __tablename__ = "campaign_workspaces"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # Campaign details
    name = Column(String(300), nullable=False)
    platform = Column(String(50), nullable=False)  # meta, google, linkedin, youtube, x, snapchat
    objective = Column(String(100))  # lead_generation, brand_awareness, website_traffic, conversions
    procedure_focus = Column(String(200))

    # Budget
    daily_budget = Column(Float, default=0)
    total_budget = Column(Float, default=0)
    spent = Column(Float, default=0)

    # Targeting
    targeting = Column(JSON, default=dict)  # location, age, interests, custom audiences
    ad_sets = Column(JSON, default=list)  # ad set configurations

    # Creative assets
    ad_angles = Column(JSON, default=list)  # generated ad angles
    scripts = Column(JSON, default=list)  # generated scripts
    creatives = Column(JSON, default=list)  # image/video creative specs

    # Status & tracking
    status = Column(String(50), default="draft")  # draft, review, active, paused, completed
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # AI analysis
    ai_recommendations = Column(JSON, default=list)
    optimization_log = Column(JSON, default=list)  # track of AI optimizations applied

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    clinic = relationship("Clinic", backref="campaign_workspaces")


# ============================================================================
# MARKETING AI FEEDBACK (Self-Learning)
# ============================================================================

class MarketingAIFeedback(Base):
    __tablename__ = "marketing_ai_feedback"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)

    # What was generated
    content_type = Column(String(50), nullable=False)  # video_script, image_ad, carousel, etc.
    original_content = Column(Text)
    prompt_used = Column(Text)

    # Feedback
    rating = Column(Integer)  # 1-5
    feedback_text = Column(Text)
    was_used = Column(Boolean, default=False)  # did they actually use the content?
    was_edited = Column(Boolean, default=False)  # did they edit before using?
    edited_version = Column(Text)  # if edited, what did they change it to?

    # Performance (if published)
    performance_metrics = Column(JSON, default=dict)  # impressions, clicks, leads from this content

    # AI learning extraction
    ai_learnings = Column(JSON, default=dict)  # extracted patterns from feedback
    learning_type = Column(String(50))  # style, tone, structure, messaging, targeting

    created_at = Column(DateTime, default=datetime.utcnow)

    clinic = relationship("Clinic", backref="marketing_ai_feedback")


# ============================================================================
# MARKETING COACH CONVERSATIONS
# ============================================================================

class MarketingCoachChat(Base):
    __tablename__ = "marketing_coach_chats"

    id = Column(String, primary_key=True, default=generate_uuid)
    clinic_id = Column(String, ForeignKey("clinics.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Conversation
    topic = Column(String(300))
    messages = Column(JSON, default=list)  # [{role, content, timestamp}]
    message_count = Column(Integer, default=0)

    # Context
    context_type = Column(String(50))  # general, campaign, content, research, ads
    context_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    clinic = relationship("Clinic", backref="marketing_coach_chats")
