"""
CallCoach CRM - HR & MIS Router
HR management, team tracking, daily MIS reports, and performance sync.
"""
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.services.activity_logger import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hr", tags=["hr-mis"])


def _call_claude_hr(prompt: str, max_tokens: int = 2500):
    from app.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"): text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except:
        return text


# ---------------------------------------------------------------------------
# Team Members
# ---------------------------------------------------------------------------

@router.get("/team")
def list_team(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    team = settings.get("team_members", [])
    return {"team": team, "total": len(team)}


@router.post("/team")
def add_team_member(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    team = list(settings.get("team_members", []))
    member = {
        "id": str(len(team) + 1),
        "name": data.get("name", ""),
        "role": data.get("role", ""),
        "department": data.get("department", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "joining_date": data.get("joining_date", datetime.utcnow().strftime("%Y-%m-%d")),
        "salary": data.get("salary", 0),
        "status": "active",
        "kpis": data.get("kpis", []),
        "verticals": data.get("verticals", []),
        "reporting_to": data.get("reporting_to", ""),
        "created_at": datetime.utcnow().isoformat()
    }
    team.append(member)
    settings["team_members"] = team
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "team_member_added",
                 {"name": member["name"], "role": member["role"], "department": member["department"]},
                 current_user.email)
    return {"status": "added", "member": member}


@router.put("/team/{member_id}")
def update_team_member(member_id: str, data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    team = list(settings.get("team_members", []))
    for i, m in enumerate(team):
        if m.get("id") == member_id:
            for k, v in data.items():
                if v is not None: team[i][k] = v
            settings["team_members"] = team
            clinic.settings = settings
            db.commit()
            log_activity(db, current_user.clinic_id, "hr", "team_member_updated",
                         {"member_id": member_id, "updated_fields": list(data.keys())},
                         current_user.email)
            return {"status": "updated", "member": team[i]}
    raise HTTPException(status_code=404, detail="Member not found")


@router.delete("/team/{member_id}")
def remove_team_member(member_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    team = [m for m in settings.get("team_members", []) if m.get("id") != member_id]
    settings["team_members"] = team
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "team_member_removed",
                 {"member_id": member_id}, current_user.email)
    return {"status": "removed"}


# ---------------------------------------------------------------------------
# MIS Daily Reports
# ---------------------------------------------------------------------------

@router.get("/mis/reports")
def list_mis_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    reports = settings.get("mis_reports", [])
    return {"reports": reports[-30:], "total": len(reports)}


@router.post("/mis/reports")
def submit_mis_report(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    reports = list(settings.get("mis_reports", []))
    report = {
        "id": str(len(reports) + 1),
        "date": data.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
        "submitted_by": data.get("submitted_by", current_user.email),
        "member_name": data.get("member_name", ""),
        "department": data.get("department", ""),
        "tasks_completed": data.get("tasks_completed", []),
        "tasks_pending": data.get("tasks_pending", []),
        "blockers": data.get("blockers", ""),
        "metrics": data.get("metrics", {}),
        "notes": data.get("notes", ""),
        "channels_worked": data.get("channels_worked", []),
        "clients_worked": data.get("clients_worked", []),
        "hours_worked": data.get("hours_worked", 8),
        "created_at": datetime.utcnow().isoformat()
    }
    reports.append(report)
    settings["mis_reports"] = reports
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "report", "mis_daily_report_submitted",
                 {"member_name": report["member_name"], "department": report["department"], "date": report["date"]},
                 current_user.email)
    return {"status": "submitted", "report": report}


# ---------------------------------------------------------------------------
# Attendance & Leave
# ---------------------------------------------------------------------------

@router.get("/attendance")
def get_attendance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    return {"attendance": settings.get("attendance_records", [])[-60:]}


@router.post("/attendance")
def mark_attendance(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    records = list(settings.get("attendance_records", []))
    record = {
        "id": str(len(records) + 1),
        "member_id": data.get("member_id"),
        "member_name": data.get("member_name"),
        "date": data.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
        "status": data.get("status", "present"),
        "check_in": data.get("check_in", ""),
        "check_out": data.get("check_out", ""),
        "notes": data.get("notes", "")
    }
    records.append(record)
    settings["attendance_records"] = records
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "attendance_marked",
                 {"member_name": record["member_name"], "status": record["status"], "date": record["date"]},
                 current_user.email)
    return {"status": "recorded"}


@router.get("/leaves")
def get_leaves(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    return {"leaves": settings.get("leave_requests", [])}


@router.post("/leaves")
def request_leave(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    leaves = list(settings.get("leave_requests", []))
    leave = {
        "id": str(len(leaves) + 1),
        "member_id": data.get("member_id"),
        "member_name": data.get("member_name"),
        "type": data.get("type", "casual"),
        "from_date": data.get("from_date"),
        "to_date": data.get("to_date"),
        "reason": data.get("reason", ""),
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    leaves.append(leave)
    settings["leave_requests"] = leaves
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "leave_requested",
                 {"member_name": leave["member_name"], "type": leave["type"], "from": leave["from_date"], "to": leave["to_date"]},
                 current_user.email)
    return {"status": "submitted", "leave": leave}


# ---------------------------------------------------------------------------
# Payroll
# ---------------------------------------------------------------------------

@router.get("/payroll")
def get_payroll(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    return {"payroll": settings.get("payroll_records", [])}


@router.post("/payroll")
def add_payroll(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinic not found")
    settings = dict(clinic.settings or {})
    payroll = list(settings.get("payroll_records", []))
    record = {
        "id": str(len(payroll) + 1),
        "member_id": data.get("member_id"),
        "member_name": data.get("member_name"),
        "month": data.get("month"),
        "base_salary": data.get("base_salary", 0),
        "bonus": data.get("bonus", 0),
        "deductions": data.get("deductions", 0),
        "net_pay": data.get("base_salary", 0) + data.get("bonus", 0) - data.get("deductions", 0),
        "status": data.get("status", "pending"),
        "paid_date": data.get("paid_date", ""),
        "notes": data.get("notes", "")
    }
    payroll.append(record)
    settings["payroll_records"] = payroll
    clinic.settings = settings
    db.commit()
    log_activity(db, current_user.clinic_id, "hr", "payroll_record_added",
                 {"member_name": record["member_name"], "month": record["month"], "net_pay": record["net_pay"]},
                 current_user.email)
    return {"status": "added", "record": record}


# ---------------------------------------------------------------------------
# AI-Powered HR Tools
# ---------------------------------------------------------------------------

@router.post("/generate-jd")
def generate_job_description(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a job description using AI."""
    role = data.get("role", "Marketing Executive")
    department = data.get("department", "Marketing")
    experience = data.get("experience", "1-3 years")
    skills = data.get("skills", "")

    prompt = f"""Generate a detailed job description for a clinic marketing agency:

Role: {role}
Department: {department}
Experience Required: {experience}
Key Skills: {skills or 'Digital marketing, clinic marketing'}

Include:
1. job_title
2. department
3. reporting_to
4. job_summary (2-3 sentences)
5. responsibilities: Array of 8-10 detailed responsibilities
6. requirements: Array of 6-8 requirements
7. nice_to_have: Array of 4-5 preferred qualifications
8. salary_range: Suggested range in INR
9. benefits: Array of benefits
10. kpis: Array of 5 measurable KPIs for this role

Format as JSON object."""

    try:
        parsed = _call_claude_hr(prompt)
        log_activity(db, current_user.clinic_id, "hr", "job_description_generated",
                     {"role": role, "department": department, "experience": experience},
                     current_user.email)
        return {"jd": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="JD generation failed")


@router.post("/generate-interview")
def generate_interview_questions(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate interview questions for a role."""
    role = data.get("role", "Marketing Executive")
    round_type = data.get("round_type", "technical")

    prompt = f"""Generate interview questions for a clinic marketing agency:

Role: {role}
Round Type: {round_type} (options: screening, technical, practical_task, culture_fit, final)

Provide:
1. round_name
2. duration_minutes
3. questions: Array of 10 questions, each with:
   - question
   - what_to_look_for (ideal answer signals)
   - red_flags (concerning responses)
   - scoring_criteria (1-5 scale description)
4. practical_task: A take-home or live task for the candidate
5. evaluation_rubric: Overall scoring framework

Format as JSON object."""

    try:
        parsed = _call_claude_hr(prompt)
        log_activity(db, current_user.clinic_id, "hr", "interview_questions_generated",
                     {"role": role, "round_type": round_type},
                     current_user.email)
        return {"interview": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Interview question generation failed")


@router.post("/generate-onboarding")
def generate_onboarding_plan(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate an onboarding plan for a new hire."""
    role = data.get("role", "Marketing Executive")
    department = data.get("department", "Marketing")

    prompt = f"""Generate a 30-day onboarding plan for a clinic marketing agency:

Role: {role}
Department: {department}

Provide a detailed week-by-week plan:
1. week_1: Array of daily tasks (Day 1 through Day 5), including training modules, people to meet, tools to set up
2. week_2: Array of daily tasks focusing on hands-on training
3. week_3: Array of daily tasks focusing on supervised work
4. week_4: Array of daily tasks focusing on independent work with review
5. tools_access: List of tools/platforms to give access to with setup instructions
6. training_resources: Links and materials to study
7. milestone_checkpoints: What they should accomplish by day 7, 14, 21, 30
8. buddy_system: How to pair them with a mentor

Format as JSON object."""

    try:
        parsed = _call_claude_hr(prompt)
        log_activity(db, current_user.clinic_id, "hr", "onboarding_plan_generated",
                     {"role": role, "department": department},
                     current_user.email)
        return {"onboarding": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Onboarding plan generation failed")


@router.post("/generate-performance-review")
def generate_performance_review(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a performance review template."""
    role = data.get("role", "Marketing Executive")
    period = data.get("period", "quarterly")

    prompt = f"""Generate a performance review framework for a clinic marketing agency:

Role: {role}
Review Period: {period}

Include:
1. review_categories: Array of 5-6 categories (e.g., Quality of Work, Communication, Initiative), each with weight percentage and description
2. rating_scale: 1-5 scale with descriptions
3. self_assessment_questions: 5 questions for the employee
4. manager_assessment_questions: 5 questions for the manager
5. goal_setting_template: Framework for setting next period goals
6. development_plan: Template for identifying growth areas
7. compensation_review: Framework for salary revision recommendations

Format as JSON object."""

    try:
        parsed = _call_claude_hr(prompt)
        log_activity(db, current_user.clinic_id, "hr", "performance_review_generated",
                     {"role": role, "period": period},
                     current_user.email)
        return {"review": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Performance review generation failed")


# ---------------------------------------------------------------------------
# MIS AI Analysis
# ---------------------------------------------------------------------------

@router.post("/mis/analyze")
def analyze_mis_data(data: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """AI analysis of MIS data to identify patterns and issues."""
    from app.models import Clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    settings = clinic.settings or {} if clinic else {}
    reports = settings.get("mis_reports", [])[-14:]

    prompt = f"""Analyze these daily MIS reports from a clinic marketing agency team and provide insights:

Reports (last 14 days): {json.dumps(reports[:14])}

Provide:
1. team_productivity_score: Overall score 1-100
2. top_performers: Who is performing best and why
3. concerns: Any red flags (missed deadlines, low hours, repeated blockers)
4. bottlenecks: Common blockers across the team
5. recommendations: 5 actionable recommendations to improve team performance
6. channel_performance: Which channels (Meta Ads, Google Ads, Content, WhatsApp) are getting most attention
7. client_coverage: Are all clients getting equal attention
8. workload_balance: Is work evenly distributed

Format as JSON object."""

    try:
        parsed = _call_claude_hr(prompt, 2000)
        log_activity(db, current_user.clinic_id, "report", "mis_ai_analysis_generated",
                     {"reports_analyzed": len(reports)},
                     current_user.email)
        return {"analysis": parsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="MIS analysis failed")
