"""
CallCoach CRM - Database Backup Script

Creates a timestamped JSON export of all database tables.
Safe to run on both SQLite and PostgreSQL.

Usage:
    python scripts/backup_db.py
    python scripts/backup_db.py --output /path/to/backup.json
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATABASE_URL
from app.database import SessionLocal
from app.models import (
    User, Clinic, Call, CallNote, PipelineDeal,
    DealActivity, CoachingInsight, CallScore, Tag,
    LearningProgress, Certification, WeeklyReport
)


def serialize_row(row):
    """Convert a SQLAlchemy model instance to a dict, handling datetimes."""
    d = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        d[col.name] = val
    return d


def backup_table(db, model):
    """Backup all rows from a single table."""
    rows = db.query(model).all()
    return [serialize_row(r) for r in rows]


def run_backup(output_path=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not output_path:
        backup_dir = Path(__file__).resolve().parent.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        output_path = backup_dir / f"callcoach_backup_{timestamp}.json"

    db = SessionLocal()
    try:
        backup = {
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "database_url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "sqlite",
            },
            "tables": {
                "clinics": backup_table(db, Clinic),
                "users": backup_table(db, User),
                "calls": backup_table(db, Call),
                "call_notes": backup_table(db, CallNote),
                "call_scores": backup_table(db, CallScore),
                "pipeline_deals": backup_table(db, PipelineDeal),
                "deal_activities": backup_table(db, DealActivity),
                "coaching_insights": backup_table(db, CoachingInsight),
                "tags": backup_table(db, Tag),
                "learning_progress": backup_table(db, LearningProgress),
                "certifications": backup_table(db, Certification),
                "weekly_reports": backup_table(db, WeeklyReport),
            }
        }

        # Add row counts
        backup["meta"]["row_counts"] = {
            table: len(rows) for table, rows in backup["tables"].items()
        }
        backup["meta"]["total_rows"] = sum(backup["meta"]["row_counts"].values())

        with open(output_path, "w") as f:
            json.dump(backup, f, indent=2, default=str)

        print(f"Backup saved: {output_path}")
        print(f"Total rows: {backup['meta']['total_rows']}")
        for table, count in backup["meta"]["row_counts"].items():
            if count > 0:
                print(f"  {table}: {count} rows")

    finally:
        db.close()


if __name__ == "__main__":
    output = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output = sys.argv[idx + 1]
    run_backup(output)
