from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta
import uuid

from app.database import get_session
from app.models import User, UserCreate, UserResponse, Token, PasswordUpdate, KindleEmailUpdate
from app.auth_utils import (
    verify_password, get_password_hash, create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES, get_current_active_user
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserCreate, session: Session = Depends(get_session)):
    """Register a new standard user."""
    # Check if user exists
    existing_user = session.exec(select(User).where(User.email == user_in.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Eine Registrierung mit dieser E-Mail ist bereits vorhanden."
        )

    # Determine if this should be the admin
    is_admin = False
    config_admin = settings.POCKETBASE_ADMIN_EMAIL.lower()
    target_email = user_in.email.lower()
    
    logger.info(f"Registering user: {target_email}. Configured admin: '{config_admin}'")
    
    if target_email == config_admin:
        is_admin = True
        logger.info(f"User matches admin email. Setting is_admin=True")

    new_user = User(
        id=str(uuid.uuid4()),
        email=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        is_admin=is_admin,
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """OAuth2 compatible token login, get an access token for future requests."""
    user = session.exec(select(User).where(User.email == form_data.username.lower())).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falsche E-Mail oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Benutzerkonto inaktiv")
    
    config_admin = settings.POCKETBASE_ADMIN_EMAIL.lower()
    user_email = user.email.lower()
    
    logger.info(f"Login successful for {user_email}. is_admin in DB: {user.is_admin}. Config admin: '{config_admin}'")
    
    # Failsafe: Force is_admin for the configured admin email
    if user_email == config_admin and not user.is_admin:
        logger.info(f"Failsafe triggered: Promoting {user_email} to admin during login.")
        user.is_admin = True
        session.add(user)
        session.commit()
        session.refresh(user)
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get the profile of the currently logged-in user."""
    return current_user


@router.put("/me/password")
def update_password(
    data: PasswordUpdate, 
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """Update current user password."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Das aktuelle Passwort ist falsch.")
        
    current_user.hashed_password = get_password_hash(data.new_password)
    session.add(current_user)
    session.commit()
    return {"status": "success", "message": "Passwort erfolgreich geändert."}
    
    
@router.put("/me/kindle")
def update_kindle_email(
    data: KindleEmailUpdate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    current_user.kindle_email = data.kindle_email
    session.add(current_user)
    session.commit()
    return {"status": "success", "message": "Kindle-Adresse geändert."}
