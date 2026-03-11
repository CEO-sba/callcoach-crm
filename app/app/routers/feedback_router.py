"""
CallCoach CRM - AI Feedback Router (Self-Learning System)
Universal feedback endpoints for all AI-powered modules.
Stores ratings, feedback, and edited versions to improve
AI coaching quality over time.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.self_learning import (
    store_feedback,
    get_feedback_stats,
    get_learning_context,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["ai-feedback"])

VALID_MODULES = [
    "consultations", "hiring", "operations", "inbox",
    "marketing", "legal_finance"
]


# =============================================================================
# 1. SUBMIT FEEDBACK
# =============================================================================

@router.post("/submit")
async def submit_feedback(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback on any AI-generated output.
    Required: module, action_type, rating (1-5)
    Optional: feedback_text, input_summary, output_summary,
              was_useful, was_edited, edited_version,
              input_data, output_data
    """
    module = data.get("module")
    action_type = data.get("action_type")
    rating = data.get("rating")

    if not module or module not in VALID_MODULES:
        raise HTTPException(
            status_code=400,
            detail=f"module required. Valid: {VALID_MODULES}"
        )
    if not action_type:
        raise HTTPException(status_code=400, detail="action_type is required")
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="rating must be integer 1-5")

    feedback = store_feedback(
        db=db,
        clinic_id=current_user.clinic_id,
        module=module,
        action_type=action_type,
        rating=rating,
        feedback_text=data.get("feedback_text", ""),
        input_summary=data.get("input_summary", ""),
        input_data=data.get("input_data", {}),
        output_summary=data.get("output_summary", ""),
        output_data=data.get("output_data", {}),
        was_useful=data.get("was_useful", True),
        was_edited=data.get("was_edited", False),
        edited_version=data.get("edited_version", ""),
    )

    return {
        "status": "feedback_stored",
        "feedback_id": feedback.id,
        "module": module,
        "action_type": action_type,
        "rating": rating,
    }


# =============================================================================
# 2. FEEDBACK STATS
# =============================================================================

@router.get("/stats")
async def feedback_stats_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback stats across all modules."""
    all_stats = {}
    for module in VALID_MODULES:
        all_stats[module] = get_feedback_stats(
            db=db,
            clinic_id=current_user.clinic_id,
            module=module,
        )

    return {"modules": all_stats}


@router.get("/stats/{module}")
async def feedback_stats_module(
    module: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback stats for a specific module."""
    if module not in VALID_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid module. Valid: {VALID_MODULES}")

    stats = get_feedback_stats(
        db=db,
        clinic_id=current_user.clinic_id,
        module=module,
    )

    return {"module": module, "stats": stats}


# =============================================================================
# 3. LEARNING CONTEXT (for debugging/inspection)
# =============================================================================

@router.get("/learning-context/{module}")
async def get_module_learning_context(
    module: str,
    action_type: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View what the AI is learning from for a specific module.
    Shows the past high-rated outputs that inform future AI responses.
    """
    if module not in VALID_MODULES:
        raise HTTPException(status_code=400, detail=f"Invalid module. Valid: {VALID_MODULES}")

    context = get_learning_context(
        db=db,
        clinic_id=current_user.clinic_id,
        module=module,
        action_type=action_type,
    )

    return {
        "module": module,
        "action_type": action_type,
        "learning_context": context or "No feedback data yet. Rate AI outputs to start self-learning.",
    }
