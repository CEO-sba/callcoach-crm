"""
CallCoach CRM - Database Setup
Supports both SQLite (dev) and PostgreSQL (production on Hostinger Cloud).
"""
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

logger = logging.getLogger(__name__)

_is_sqlite = DATABASE_URL.startswith("sqlite")

# SQLite needs check_same_thread=False; Postgres needs pool settings
if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # auto-reconnect on stale connections
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. create_all is safe -- it only adds missing tables, never drops existing ones."""
    from app.models import (
        User, Clinic, Call, CallNote, PipelineDeal,
        DealActivity, CoachingInsight, CallScore, Tag,
        LearningProgress, Certification, WeeklyReport
    )
    from app.models_whatsapp import (
        Lead, WhatsAppConfig, AIEmployee, WhatsAppConversation,
        WhatsAppMessage, NurtureSequence, NurtureStep, NurtureEnrollment,
        ClinicApiKey, MetaConfig, SocialAccount, SocialPost, MarketingInsight
    )
    from app.models_expanded import (
        UnifiedConversation, UnifiedMessage, ContactActivity, ContactTag,
        ContactReminder, ContactTask, HiringPosition, HiringCandidate,
        HiringInterview, VideoConsultation, Invoice, InventoryItem,
        PatientRecord, AdPerformance, WeeklyAdReport, AIContentGeneration,
        ClinicDocument, FinanceRecord, ConsultationTranscription,
        ConsultationAnalysis, PatientProcedureHistory
    )
    from app.models_marketing import (
        ContentCalendar, ContentCalendarPost, MarketResearch,
        CampaignWorkspace, MarketingAIFeedback, MarketingCoachChat
    )
    Base.metadata.create_all(bind=engine)
    _run_column_migrations()


def _safe_add_column(conn, table: str, column: str, col_type: str):
    """Add a column if it doesn't exist. Works with both SQLite and PostgreSQL."""
    try:
        insp = inspect(engine)
        existing = [c["name"] for c in insp.get_columns(table)]
        if column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            logger.info(f"Added column {table}.{column}")
    except Exception as e:
        logger.debug(f"Column {table}.{column} migration skipped: {e}")


def _run_column_migrations():
    """Run lightweight column migrations on startup. Safe to call repeatedly."""
    is_pg = not _is_sqlite
    json_type = "JSONB" if is_pg else "TEXT"
    text_type = "TEXT"
    varchar50 = "VARCHAR(50)"

    with engine.begin() as conn:
        # AI Employee advanced personalization columns (added v2.1)
        ai_cols = [
            ("personality_traits", json_type),
            ("brand_voice_description", text_type),
            ("custom_faqs", json_type),
            ("objection_responses", json_type),
            ("usp_points", json_type),
            ("competitor_differentiators", text_type),
            ("follow_up_style", varchar50),
            ("emoji_usage", varchar50),
            ("message_length_preference", varchar50),
            ("qualification_questions", json_type),
            ("escalation_triggers", json_type),
            ("special_instructions", text_type),
            ("welcome_offer", text_type),
            ("doctor_credentials", text_type),
            ("success_stories", json_type),
            ("banned_phrases", json_type),
            ("preferred_phrases", json_type),
        ]
        for col_name, col_type in ai_cols:
            _safe_add_column(conn, "ai_employees", col_name, col_type)
