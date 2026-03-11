"""
CallCoach CRM - Database Setup
Supports both SQLite (dev) and PostgreSQL (production on Hostinger Cloud).
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

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
    Base.metadata.create_all(bind=engine)
