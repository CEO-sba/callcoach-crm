"""
CallCoach CRM - Admin Portal Router
Super admin endpoints for managing clinics, users, and platform analytics.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Clinic, Call
from app.schemas import (
    AdminClinicCreate, AdminDashboardStats, PlatformAverages,
    ClinicUpdate, UserCreate, UserOut, Token
)
from app.auth import (
    hash_password, get_current_user, require_super_admin, create_access_token
)
from app.config import SECRET_KEY
from app.services.admin_service import (
    get_platform_stats, get_platform_averages, get_clinic_detail_stats, list_all_clinics
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---- Bootstrap ----
class BootstrapRequest(BaseModel):
    email: str
    password: str
    full_name: str
    secret_key: str


@router.post("/bootstrap")
def bootstrap_super_admin(data: BootstrapRequest, db: Session = Depends(get_db)):
    """One-time endpoint to create the first super admin. Secured by SECRET_KEY."""
    if data.secret_key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid secret key")

    # Check if a super admin already exists
    existing_sa = db.query(User).filter(User.is_super_admin == True).first()
    if existing_sa:
        raise HTTPException(status_code=400, detail="Super admin already exists")

    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        clinic_id=None,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role="admin",
        is_super_admin=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "sub": new_user.id,
        "clinic_id": None,
        "role": "admin",
        "is_super_admin": True
    })
    return {
        "status": "ok",
        "message": "Super admin created successfully",
        "user_id": new_user.id,
        "access_token": token
    }


# ---- Dashboard ----
@router.get("/dashboard", response_model=AdminDashboardStats)
def admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get platform-wide dashboard statistics."""
    return get_platform_stats(db)


# ---- Clinic Management ----
@router.post("/clinics")
def create_clinic(
    data: AdminClinicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Create a new doctor account (clinic + admin user)."""
    existing_email = db.query(User).filter(User.email == data.admin_email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Admin email already registered")

    # Create clinic
    clinic = Clinic(
        name=data.clinic_name,
        phone=data.clinic_phone,
        email=data.clinic_email,
        city=data.clinic_city,
        specialty=data.clinic_specialty,
    )
    db.add(clinic)
    db.flush()

    # Create clinic admin user
    admin_user = User(
        clinic_id=clinic.id,
        email=data.admin_email,
        hashed_password=hash_password(data.admin_password),
        full_name=data.admin_full_name,
        role="admin",
        is_super_admin=False
    )
    db.add(admin_user)
    db.commit()
    db.refresh(clinic)
    db.refresh(admin_user)

    return {
        "status": "ok",
        "clinic_id": clinic.id,
        "clinic_name": clinic.name,
        "admin_user_id": admin_user.id,
        "admin_email": admin_user.email,
    }


@router.get("/clinics")
def list_clinics(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """List all clinics with stats."""
    return list_all_clinics(db, active_only)


@router.get("/clinics/{clinic_id}")
def get_clinic(
    clinic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get detailed info for a specific clinic including staff list."""
    result = get_clinic_detail_stats(db, clinic_id)
    if not result:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return result


@router.patch("/clinics/{clinic_id}")
def update_clinic(
    clinic_id: str,
    data: ClinicUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Update a clinic (activate/deactivate, toggle leaderboard, etc.)."""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(clinic, key, value)

    db.commit()
    db.refresh(clinic)
    return {
        "status": "ok",
        "clinic_id": clinic.id,
        "name": clinic.name,
        "is_active": clinic.is_active,
        "leaderboard_visible": clinic.leaderboard_visible,
    }


# ---- Staff Management within Clinics ----
@router.get("/clinics/{clinic_id}/users")
def list_clinic_users(
    clinic_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get all users in a specific clinic."""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    users = db.query(User).filter(
        User.clinic_id == clinic_id, User.is_super_admin == False
    ).all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/clinics/{clinic_id}/users", response_model=UserOut)
def add_clinic_user(
    clinic_id: str,
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Add a staff member to a specific clinic."""
    clinic = db.query(Clinic).filter(Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        clinic_id=clinic_id,
        email=user.email,
        hashed_password=hash_password(user.password),
        full_name=user.full_name,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.patch("/clinics/{clinic_id}/users/{user_id}")
def update_clinic_user(
    clinic_id: str,
    user_id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Update or deactivate a staff member in a clinic."""
    user = db.query(User).filter(
        User.id == user_id, User.clinic_id == clinic_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this clinic")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return {
        "status": "ok",
        "user_id": user.id,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }


# ---- Platform Analytics ----
@router.get("/analytics/platform-averages", response_model=PlatformAverages)
def platform_averages(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get platform-wide average scores across all dimensions (anonymized)."""
    return get_platform_averages(db)
