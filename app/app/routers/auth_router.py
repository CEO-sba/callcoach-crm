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


@router.post("/register", response_model=Token)
def register(data: ClinicCreate, user: UserCreate, db: Session = Depends(get_db)):
    """Register a new clinic and admin user."""
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create clinic
    clinic = Clinic(name=data.name, phone=data.phone, email=data.email,
                    address=data.address, city=data.city, specialty=data.specialty)
    db.add(clinic)
    db.flush()

    # Create admin user
    new_user = User(
        clinic_id=clinic.id,
        email=user.email,
        hashed_password=hash_password(user.password),
        full_name=user.full_name,
        role="admin"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "sub": new_user.id,
        "clinic_id": clinic.id,
        "role": new_user.role,
        "is_super_admin": False
    })
    log_activity(db, clinic.id, "system", "clinic_registered",
                 {"clinic_name": data.name, "admin_email": user.email,
                  "city": data.city, "specialty": data.specialty},
                 user.email)
    return Token(access_token=token, user_id=new_user.id, clinic_id=clinic.id, role=new_user.role, is_super_admin=False)


class SimpleRegister(BaseModel):
    email: str
    password: str
    full_name: str
    clinic_name: str


@router.post("/register-simple", response_model=Token)
def register_simple(data: SimpleRegister, db: Session = Depends(get_db)):
    """Simplified registration endpoint."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    clinic = Clinic(name=data.clinic_name)
    db.add(clinic)
    db.flush()

    new_user = User(
        clinic_id=clinic.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role="admin"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "sub": new_user.id,
        "clinic_id": clinic.id,
        "role": new_user.role,
        "is_super_admin": False
    })
    log_activity(db, clinic.id, "system", "clinic_registered_simple",
                 {"clinic_name": data.clinic_name, "admin_email": data.email},
                 data.email)
    return Token(access_token=token, user_id=new_user.id, clinic_id=clinic.id, role=new_user.role, is_super_admin=False)


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
