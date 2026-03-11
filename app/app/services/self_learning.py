"""
CallCoach CRM - Self-Learning Service
Stores AI feedback and retrieves past high-quality outputs
to improve AI coaching over time across all modules.
"""
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models_expanded import AIFeedback

logger = logging.getLogger(__name__)


def store_feedback(
    db: Session,
    clinic_id: str,
    module: str,
    action_type: str,
    rating: int,
    feedback_text: str = "",
    input_summary: str = "",
    input_data: dict = None,
    output_summary: str = "",
    output_data: dict = None,
    was_useful: bool = True,
    was_edited: bool = False,
    edited_version: str = "",
) -> AIFeedback:
    """Store feedback on an AI-generated output."""
    feedback = AIFeedback(
        clinic_id=clinic_id,
        module=module,
        action_type=action_type,
        rating=rating,
        feedback_text=feedback_text,
        input_summary=input_summary,
        input_data=input_data or {},
        output_summary=output_summary,
        output_data=output_data or {},
        was_useful=was_useful,
        was_edited=was_edited,
        edited_version=edited_version,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_learning_context(
    db: Session,
    clinic_id: str,
    module: str,
    action_type: str = None,
    min_rating: int = 4,
    limit: int = 5,
) -> str:
    """
    Retrieve past high-rated AI outputs to use as few-shot examples
    in future AI prompts. This is how the system learns over time.

    Returns a formatted string to inject into AI system prompts.
    """
    query = db.query(AIFeedback).filter(
        AIFeedback.clinic_id == clinic_id,
        AIFeedback.module == module,
        AIFeedback.rating >= min_rating,
        AIFeedback.was_useful == True,
    )

    if action_type:
        query = query.filter(AIFeedback.action_type == action_type)

    feedback_items = query.order_by(
        AIFeedback.rating.desc(),
        AIFeedback.created_at.desc()
    ).limit(limit).all()

    if not feedback_items:
        return ""

    # Build learning context string
    lines = [
        "\n--- LEARNING FROM PAST FEEDBACK (use these to improve your responses) ---"
    ]

    for item in feedback_items:
        lines.append(f"\nAction: {item.action_type} | Rating: {item.rating}/5")
        if item.input_summary:
            lines.append(f"Request: {item.input_summary[:200]}")
        if item.was_edited and item.edited_version:
            lines.append(f"User preferred version: {item.edited_version[:500]}")
        elif item.output_summary:
            lines.append(f"Well-received output: {item.output_summary[:500]}")
        if item.feedback_text:
            lines.append(f"User feedback: {item.feedback_text[:200]}")

    lines.append("\n--- END LEARNING CONTEXT ---\n")

    return "\n".join(lines)


def get_feedback_stats(
    db: Session,
    clinic_id: str,
    module: str = None,
) -> dict:
    """Get feedback statistics for a module or all modules."""
    query = db.query(AIFeedback).filter(
        AIFeedback.clinic_id == clinic_id
    )

    if module:
        query = query.filter(AIFeedback.module == module)

    total = query.count()
    if total == 0:
        return {
            "total_feedback": 0,
            "avg_rating": 0,
            "useful_percentage": 0,
            "edited_percentage": 0,
            "by_action": {}
        }

    avg_rating = db.query(func.avg(AIFeedback.rating)).filter(
        AIFeedback.clinic_id == clinic_id,
        AIFeedback.module == module if module else True,
        AIFeedback.rating.isnot(None),
    ).scalar() or 0

    useful_count = query.filter(AIFeedback.was_useful == True).count()
    edited_count = query.filter(AIFeedback.was_edited == True).count()

    # Breakdown by action type
    action_stats = db.query(
        AIFeedback.action_type,
        func.count(AIFeedback.id).label("count"),
        func.avg(AIFeedback.rating).label("avg_rating")
    ).filter(
        AIFeedback.clinic_id == clinic_id,
        AIFeedback.module == module if module else True,
    ).group_by(AIFeedback.action_type).all()

    return {
        "total_feedback": total,
        "avg_rating": round(float(avg_rating), 2),
        "useful_percentage": round(useful_count / total * 100, 1) if total > 0 else 0,
        "edited_percentage": round(edited_count / total * 100, 1) if total > 0 else 0,
        "by_action": {
            stat.action_type: {
                "count": stat.count,
                "avg_rating": round(float(stat.avg_rating or 0), 2)
            }
            for stat in action_stats
        }
    }
