"""
CallCoach CRM - Learning Academy API Router

Endpoints for the SBA Learning Academy: modules, quizzes, mock calls,
progress tracking, and certification.
"""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.auth import get_current_user
from app.models import User, LearningProgress, Certification
from app.services.learning_content import (
    get_all_modules,
    get_module_by_id,
    get_modules_by_category,
    get_quiz_for_module,
    get_mock_scenarios_for_module,
    grade_quiz,
    get_certification_levels,
    check_certification_eligibility,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/learning", tags=["learning"])


# ---- Schemas ----

class QuizSubmission(BaseModel):
    answers: dict  # {question_id: selected_index}

class MockCallSubmission(BaseModel):
    scenario_id: str
    transcript: str  # user's mock call attempt
    self_score: Optional[float] = None

class ModuleProgressUpdate(BaseModel):
    status: Optional[str] = None
    time_spent_minutes: Optional[int] = None

class ModuleListOut(BaseModel):
    id: str
    order: int
    title: str
    subtitle: str
    description: str
    duration_minutes: int
    category: str
    icon: str
    color: str
    status: str = "not_started"
    quiz_score: Optional[float] = None
    quiz_passed: bool = False
    mock_score: Optional[float] = None

class CertificationOut(BaseModel):
    id: str
    certification_id: str
    title: str
    earned_at: datetime
    avg_quiz_score: Optional[float]
    avg_mock_score: Optional[float]


# ---- Module Endpoints ----

@router.get("/modules")
def list_modules(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all learning modules with user's progress status."""
    if category:
        modules = get_modules_by_category(category)
    else:
        modules = get_all_modules()

    # Get user progress for all modules
    progress_records = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id
    ).all()
    progress_map = {p.module_id: p for p in progress_records}

    result = []
    for mod in modules:
        prog = progress_map.get(mod["id"])
        result.append({
            "id": mod["id"],
            "order": mod["order"],
            "title": mod["title"],
            "subtitle": mod["subtitle"],
            "description": mod["description"],
            "duration_minutes": mod["duration_minutes"],
            "category": mod["category"],
            "icon": mod["icon"],
            "color": mod["color"],
            "learning_objectives": mod["learning_objectives"],
            "status": prog.status if prog else "not_started",
            "quiz_score": prog.quiz_score if prog else None,
            "quiz_passed": prog.quiz_passed if prog else False,
            "mock_score": prog.mock_score if prog else None,
            "time_spent_minutes": prog.time_spent_minutes if prog else 0,
        })

    return {"modules": result, "total": len(result)}


@router.get("/modules/{module_id}")
def get_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get full module content including concepts, exercises, quiz, and mock scenarios."""
    mod = get_module_by_id(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")

    # Get user progress
    prog = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id,
        LearningProgress.module_id == module_id
    ).first()

    # Auto-create progress record if not exists
    if not prog:
        prog = LearningProgress(
            user_id=current_user.id,
            clinic_id=current_user.clinic_id,
            module_id=module_id,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        db.add(prog)
        db.commit()
        db.refresh(prog)

    # Return full module with progress
    return {
        **mod,
        "progress": {
            "status": prog.status,
            "started_at": prog.started_at.isoformat() if prog.started_at else None,
            "completed_at": prog.completed_at.isoformat() if prog.completed_at else None,
            "quiz_score": prog.quiz_score,
            "quiz_attempts": prog.quiz_attempts,
            "quiz_passed": prog.quiz_passed,
            "mock_score": prog.mock_score,
            "mock_attempts": prog.mock_attempts,
            "time_spent_minutes": prog.time_spent_minutes,
        }
    }


@router.patch("/modules/{module_id}/progress")
def update_module_progress(
    module_id: str,
    update: ModuleProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update module progress (status, time spent)."""
    prog = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id,
        LearningProgress.module_id == module_id
    ).first()

    if not prog:
        prog = LearningProgress(
            user_id=current_user.id,
            clinic_id=current_user.clinic_id,
            module_id=module_id,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        db.add(prog)

    if update.status:
        prog.status = update.status
        if update.status == "completed" and not prog.completed_at:
            prog.completed_at = datetime.utcnow()

    if update.time_spent_minutes:
        prog.time_spent_minutes = (prog.time_spent_minutes or 0) + update.time_spent_minutes

    db.commit()
    return {"status": "updated", "module_id": module_id}


# ---- Quiz Endpoints ----

@router.get("/modules/{module_id}/quiz")
def get_quiz(
    module_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get quiz questions for a module (without correct answers)."""
    quiz = get_quiz_for_module(module_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found for this module")

    # Strip correct answers and explanations for the response
    safe_quiz = []
    for idx, q in enumerate(quiz):
        safe_quiz.append({
            "id": str(idx),
            "question": q["question"],
            "options": q["options"]
        })

    return {"module_id": module_id, "questions": safe_quiz, "total": len(safe_quiz)}


@router.post("/modules/{module_id}/quiz/submit")
def submit_quiz(
    module_id: str,
    submission: QuizSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit quiz answers and get graded results."""
    result = grade_quiz(module_id, submission.answers)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # Update progress
    prog = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id,
        LearningProgress.module_id == module_id
    ).first()

    if not prog:
        prog = LearningProgress(
            user_id=current_user.id,
            clinic_id=current_user.clinic_id,
            module_id=module_id,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        db.add(prog)

    prog.quiz_score = result["percentage"]
    prog.quiz_attempts = (prog.quiz_attempts or 0) + 1
    prog.quiz_passed = result["passed"]
    prog.quiz_answers = submission.answers

    # Auto-complete module if quiz passed and mock done (or no mock required)
    if result["passed"]:
        mock_scenarios = get_mock_scenarios_for_module(module_id)
        if not mock_scenarios or (prog.mock_score and prog.mock_score >= 70):
            prog.status = "completed"
            prog.completed_at = datetime.utcnow()

    db.commit()

    return result


# ---- Mock Call Endpoints ----

@router.get("/modules/{module_id}/mock-scenarios")
def get_mock_calls(
    module_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get mock call scenarios for a module."""
    scenarios = get_mock_scenarios_for_module(module_id)
    if not scenarios:
        raise HTTPException(status_code=404, detail="No mock scenarios for this module")

    return {"module_id": module_id, "scenarios": scenarios}


@router.post("/modules/{module_id}/mock-scenarios/evaluate")
async def evaluate_mock_call(
    module_id: str,
    submission: MockCallSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Evaluate a mock call attempt using AI coaching."""
    from app.services.ai_coach import get_client
    from app.config import ANTHROPIC_MODEL

    mod = get_module_by_id(module_id)
    scenario = None
    for s in mod.get("mock_scenarios", []):
        if s["id"] == submission.scenario_id:
            scenario = s
            break

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # AI evaluation
    try:
        client = get_client()
        eval_prompt = f"""You are evaluating a clinic staff member's mock call performance for the SBA Sales Training program.

MODULE: {mod['title']}
SCENARIO: {scenario['title']}
PATIENT PROFILE: {scenario['patient_profile']}
PATIENT PERSONALITY: {scenario['patient_personality']}
CONTEXT: {scenario['opening_context']}
EVALUATION CRITERIA: {json.dumps(scenario['evaluation_criteria'])}

STAFF MEMBER'S MOCK CALL TRANSCRIPT:
{submission.transcript}

Evaluate their performance and return JSON:
{{
    "overall_score": 0-100,
    "criteria_scores": [
        {{"criterion": "criterion text", "score": 0-100, "feedback": "specific feedback"}}
    ],
    "strengths": ["what they did well"],
    "improvements": ["what to work on with specific example of what to say instead"],
    "micro_win": "one thing to focus on next time"
}}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1500,
            system="You are an SBA Sales Trainer evaluating mock call performance. Be specific, constructive, and reference exact phrases from the transcript. Score fairly but push for improvement.",
            messages=[{"role": "user", "content": eval_prompt}]
        )

        result_text = response.content[0].text.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

        evaluation = json.loads(result_text.strip())

    except Exception as e:
        logger.error(f"Mock call evaluation failed: {e}")
        evaluation = {
            "overall_score": submission.self_score or 50,
            "criteria_scores": [],
            "strengths": ["Attempted the mock call"],
            "improvements": ["AI evaluation unavailable. Try again."],
            "micro_win": "Keep practicing"
        }

    # Update progress
    prog = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id,
        LearningProgress.module_id == module_id
    ).first()

    if not prog:
        prog = LearningProgress(
            user_id=current_user.id,
            clinic_id=current_user.clinic_id,
            module_id=module_id,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        db.add(prog)

    prog.mock_score = evaluation.get("overall_score", 0)
    prog.mock_attempts = (prog.mock_attempts or 0) + 1
    prog.mock_feedback = evaluation

    # Check for module completion
    if prog.quiz_passed and prog.mock_score and prog.mock_score >= 70:
        prog.status = "completed"
        prog.completed_at = datetime.utcnow()

    db.commit()

    return {"module_id": module_id, "scenario_id": submission.scenario_id, "evaluation": evaluation}


# ---- Progress & Certification Endpoints ----

@router.get("/progress")
def get_user_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete learning progress for the current user."""
    all_progress = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id
    ).all()

    modules = get_all_modules()
    total_modules = len(modules)
    completed = [p for p in all_progress if p.status == "completed"]
    in_progress = [p for p in all_progress if p.status == "in_progress"]

    quiz_scores = [p.quiz_score for p in all_progress if p.quiz_score is not None]
    mock_scores = [p.mock_score for p in all_progress if p.mock_score is not None]
    total_time = sum(p.time_spent_minutes or 0 for p in all_progress)

    avg_quiz = round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else 0
    avg_mock = round(sum(mock_scores) / len(mock_scores), 1) if mock_scores else 0

    # Check certification eligibility
    completed_module_ids = [p.module_id for p in completed]
    user_progress_data = {
        "completed_modules": completed_module_ids,
        "avg_quiz_score": avg_quiz,
        "avg_mock_score": avg_mock,
        "real_calls_above_70": 0,  # Will be computed from actual call data
        "real_calls_above_80": 0,
        "leaderboard_top_3_weeks": 0,
    }
    eligible_certs = check_certification_eligibility(user_progress_data)

    # Get earned certifications
    earned_certs = db.query(Certification).filter(
        Certification.user_id == current_user.id
    ).all()

    return {
        "total_modules": total_modules,
        "completed_count": len(completed),
        "in_progress_count": len(in_progress),
        "not_started_count": total_modules - len(completed) - len(in_progress),
        "completion_percentage": round((len(completed) / total_modules) * 100) if total_modules else 0,
        "avg_quiz_score": avg_quiz,
        "avg_mock_score": avg_mock,
        "total_time_spent_minutes": total_time,
        "module_progress": [
            {
                "module_id": p.module_id,
                "status": p.status,
                "quiz_score": p.quiz_score,
                "quiz_passed": p.quiz_passed,
                "mock_score": p.mock_score,
                "time_spent_minutes": p.time_spent_minutes or 0,
            }
            for p in all_progress
        ],
        "eligible_certifications": eligible_certs,
        "earned_certifications": [
            {
                "certification_id": c.certification_id,
                "title": c.title,
                "earned_at": c.earned_at.isoformat(),
                "avg_quiz_score": c.avg_quiz_score,
                "avg_mock_score": c.avg_mock_score,
            }
            for c in earned_certs
        ]
    }


@router.get("/certifications")
def get_certifications(
    current_user: User = Depends(get_current_user)
):
    """Get all certification level definitions."""
    return {"certifications": get_certification_levels()}


@router.post("/certifications/{cert_id}/claim")
def claim_certification(
    cert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Claim a certification if eligible."""
    # Check if already earned
    existing = db.query(Certification).filter(
        Certification.user_id == current_user.id,
        Certification.certification_id == cert_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Certification already earned")

    # Get progress data
    all_progress = db.query(LearningProgress).filter(
        LearningProgress.user_id == current_user.id
    ).all()

    completed_ids = [p.module_id for p in all_progress if p.status == "completed"]
    quiz_scores = [p.quiz_score for p in all_progress if p.quiz_score is not None]
    mock_scores = [p.mock_score for p in all_progress if p.mock_score is not None]

    user_data = {
        "completed_modules": completed_ids,
        "avg_quiz_score": round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else 0,
        "avg_mock_score": round(sum(mock_scores) / len(mock_scores), 1) if mock_scores else 0,
        "real_calls_above_70": 0,
        "real_calls_above_80": 0,
        "leaderboard_top_3_weeks": 0,
    }

    eligible = check_certification_eligibility(user_data)
    if cert_id not in eligible:
        raise HTTPException(status_code=403, detail="Not yet eligible for this certification")

    # Find cert title
    cert_levels = get_certification_levels()
    cert_title = next((c["title"] for c in cert_levels if c["id"] == cert_id), cert_id)

    cert = Certification(
        user_id=current_user.id,
        clinic_id=current_user.clinic_id,
        certification_id=cert_id,
        title=cert_title,
        avg_quiz_score=user_data["avg_quiz_score"],
        avg_mock_score=user_data["avg_mock_score"],
        total_modules_completed=len(completed_ids),
    )
    db.add(cert)
    db.commit()

    return {"status": "certified", "certification": cert_title, "earned_at": cert.earned_at.isoformat()}


# ---- Leaderboard ----

@router.get("/leaderboard")
def get_learning_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get learning leaderboard for the clinic."""
    from sqlalchemy import func

    # Get all users in clinic
    users = db.query(User).filter(
        User.clinic_id == current_user.clinic_id,
        User.is_active == True
    ).all()

    leaderboard = []
    for user in users:
        progress = db.query(LearningProgress).filter(
            LearningProgress.user_id == user.id
        ).all()

        completed = len([p for p in progress if p.status == "completed"])
        quiz_scores = [p.quiz_score for p in progress if p.quiz_score is not None]
        avg_quiz = round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else 0

        certs = db.query(Certification).filter(Certification.user_id == user.id).count()

        leaderboard.append({
            "user_id": user.id,
            "name": user.full_name,
            "modules_completed": completed,
            "avg_quiz_score": avg_quiz,
            "certifications_earned": certs,
            "total_modules": len(get_all_modules()),
        })

    # Sort by modules completed, then by avg quiz score
    leaderboard.sort(key=lambda x: (x["modules_completed"], x["avg_quiz_score"]), reverse=True)

    return {"leaderboard": leaderboard}


@router.get("/training-documents")
def list_training_documents():
    """List available downloadable training documents."""
    from pathlib import Path
    training_dir = Path(__file__).parent.parent / "static" / "training"
    documents = []
    if training_dir.exists():
        for f in sorted(training_dir.glob("*.docx")):
            documents.append({
                "filename": f.name,
                "title": f.stem.replace("_", " "),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "download_url": f"/api/learning/training-documents/{f.name}",
            })
    return {"documents": documents}


@router.get("/training-documents/{filename}")
def download_training_document(filename: str):
    """Download a training document."""
    from pathlib import Path
    filepath = Path(__file__).parent.parent / "static" / "training" / filename
    if not filepath.exists() or not filepath.suffix == ".docx":
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
