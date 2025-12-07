from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models.user import User
from app.auth.jwt import JWTHandler, PasswordHandler
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    PasswordChange
)
from app.schemas.token import Token

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Hash password
    hashed_password = PasswordHandler.hash_password(user.password)
    
    # Create new user (active by default, no email verification)
    new_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not PasswordHandler.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = JWTHandler.create_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
        token_type="access"
    )
    
    refresh_token = JWTHandler.create_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh"
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
def logout():
    """Logout endpoint (stateless, no DB change)."""
    return {"message": "Successfully logged out"}


@router.post("/refresh-token", response_model=Token)
def refresh_token(
    current_user: User = Depends(get_current_user),
):
    """Get a new access token using an existing token."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = JWTHandler.create_token(
        data={"sub": str(current_user.id)},
        expires_delta=access_token_expires,
        token_type="access"
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/change-password")
def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change the current user's password."""
    # Verify current password
    if not PasswordHandler.verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current password"
        )
    
    # Update password
    current_user.hashed_password = PasswordHandler.hash_password(password_change.new_password)
    db.add(current_user)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return current_user
