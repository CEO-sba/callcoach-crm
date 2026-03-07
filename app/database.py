"""
CallCoach CRM - Database Setup
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# check_same_thread is SQLite-only; skip it for PostgreSQL on Railway
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
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
    Base.metadata.create_all(bind=engine)
