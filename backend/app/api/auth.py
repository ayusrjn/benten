from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.organization import Organization, Member
from app.api.security import verify_password, get_password_hash, create_access_token, get_current_active_user
from app.config import settings
from app.schemas import UserCreate

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    
    # 1. Create User
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        onboarding_completed=False
    )
    db.add(new_user)
    db.flush()  # Generate user.id
    
    # 2. Create Organization
    org = Organization(name=user.org_name)
    db.add(org)
    db.flush()  # Generate org.id
    
    # 3. Create Member mapping
    member = Member(
        organization_id=org.id,
        email=user.email,
        role="Owner"
    )
    db.add(member)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully"}

@router.post("/login")
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "onboarding_completed": current_user.onboarding_completed
    }

@router.post("/onboarding/complete")
def complete_onboarding(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    current_user.onboarding_completed = True
    db.commit()
    return {"message": "Onboarding completed successfully"}
