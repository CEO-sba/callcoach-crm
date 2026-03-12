"""
CallCoach CRM - Auth Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Clinic
from pydantic import BaseModel
from app.schemas import UserCreate, UserLogin, Token, UserOut, ClinicCreate, ClinicOut
from app.auth import hash_password, verify_password, create_access_token, get_current_user, create_password_reset_token, verify_password_reset_token
from app.config import APP_BASE_URL
from app.services.email_service import send_password_reset_email
from app.services.activity_logger import log_activity
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({
        "sub": user.id,
        "clinic_id": user.clinic_id,
        "role": user.role,
        "is_super_admin": user.is_super_admin
    })
    if user.clinic_id:
        try:
            log_activity(db, user.clinic_id, "system", "user_login",
                         {"email": user.email, "role": user.role},
                         user.email)
        except Exception:
            pass

    return Token(
        access_token=token,
        user_id=user.id,
        clinic_id=user.clinic_id,
        role=user.role,
        is_super_admin=user.is_super_admin
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user


@router.post("/team", response_model=UserOut)
def add_team_member(user: UserCreate, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """Add a team member (admin/manager only)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admin or manager can add team members")

    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        clinic_id=current_user.clinic_id,
        email=user.email,
        hashed_password=hash_password(user.password),
        full_name=user.full_name,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_activity(db, current_user.clinic_id, "system", "team_member_added",
                 {"email": user.email, "full_name": user.full_name, "role": user.role},
                 current_user.email, related_id=new_user.id, related_type="user")
    return new_user


@router.get("/team", response_model=list[UserOut])
def get_team(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all team members for the clinic."""
    return db.query(User).filter(User.clinic_id == current_user.clinic_id).all()


class TeamMemberUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    allowed_tabs: list[str] | None = None


@router.patch("/team/{user_id}", response_model=UserOut)
def update_team_member(user_id: str, data: TeamMemberUpdate, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    """Update a team member (admin/manager only, same clinic)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admin or manager can update team members")

    target = db.query(User).filter(User.id == user_id, User.clinic_id == current_user.clinic_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if data.full_name is not None:
        target.full_name = data.full_name
    if data.role is not None:
        if data.role not in ["admin", "manager", "agent"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        target.role = data.role
    if data.is_active is not None:
        target.is_active = data.is_active
    if data.allowed_tabs is not None:
        target.allowed_tabs = data.allowed_tabs

    db.commit()
    db.refresh(target)
    log_activity(db, current_user.clinic_id, "system", "team_member_updated",
                 {"target_email": target.email, "changes": data.model_dump(exclude_none=True)},
                 current_user.email, related_id=target.id, related_type="user")
    return target


@router.delete("/team/{user_id}")
def deactivate_team_member(user_id: str, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    """Soft-delete (deactivate) a team member (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can remove team members")

    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")

    target = db.query(User).filter(User.id == user_id, User.clinic_id == current_user.clinic_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = False
    db.commit()
    log_activity(db, current_user.clinic_id, "system", "team_member_deactivated",
                 {"target_email": target.email, "target_name": target.full_name},
                 current_user.email, related_id=target.id, related_type="user")
    return {"status": "ok", "message": f"{target.full_name} has been deactivated"}


class ResetTeamPasswordRequest(BaseModel):
    new_password: str


@router.patch("/team/{user_id}/reset-password")
def reset_team_member_password(user_id: str, data: ResetTeamPasswordRequest,
                                db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    """Reset a team member's password (admin/manager only)."""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only admin or manager can reset passwords")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    target = db.query(User).filter(User.id == user_id, User.clinic_id == current_user.clinic_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.hashed_password = hash_password(data.new_password)
    db.commit()
    log_activity(db, current_user.clinic_id, "system", "team_password_reset",
                 {"target_email": target.email}, current_user.email)
    return {"status": "ok", "message": "Password reset successfully"}


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send password reset email. Always returns success to prevent user enumeration."""
    user = db.query(User).filter(User.email == data.email, User.is_active == True).first()

    if user:
        token = create_password_reset_token(user.id)
        reset_link = f"{APP_BASE_URL}/reset-password?token={token}"
        send_password_reset_email(
            to_email=user.email,
            user_name=user.full_name,
            reset_link=reset_link
        )
        logger.info(f"Password reset requested for {data.email}")
    else:
        logger.info(f"Password reset requested for non-existent email: {data.email}")

    # Always return success to prevent email enumeration
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid reset token."""
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user_id = verify_password_reset_token(data.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(data.new_password)
    db.commit()

    if user.clinic_id:
        try:
            log_activity(db, user.clinic_id, "system", "password_reset_completed",
                         {"email": user.email}, user.email)
        except Exception:
            pass

    logger.info(f"Password reset completed for user {user.email}")
    return {"message": "Password has been reset successfully. You can now log in with your new password."}
