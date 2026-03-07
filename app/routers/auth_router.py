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
from app.auth import hash_password, verify_password, create_access_token, get_current_user

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

    token = create_access_token({"sub": new_user.id, "clinic_id": clinic.id, "role": new_user.role})
    return Token(access_token=token, user_id=new_user.id, clinic_id=clinic.id, role=new_user.role)


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

    token = create_access_token({"sub": new_user.id, "clinic_id": clinic.id, "role": new_user.role})
    return Token(access_token=token, user_id=new_user.id, clinic_id=clinic.id, role=new_user.role)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token({"sub": user.id, "clinic_id": user.clinic_id, "role": user.role})
    return Token(access_token=token, user_id=user.id, clinic_id=user.clinic_id, role=user.role)


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
    return new_user


@router.get("/team", response_model=list[UserOut])
def get_team(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all team members for the clinic."""
    return db.query(User).filter(User.clinic_id == current_user.clinic_id).all()
