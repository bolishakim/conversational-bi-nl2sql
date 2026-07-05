"""
Authentication API Endpoints
Handles user login and authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession
from pydantic import BaseModel, EmailStr
from typing import Optional
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import settings
from database.models import User, Session
from utils.security import verify_password, create_access_token, decode_access_token, get_token_expiry


# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Security scheme
security = HTTPBearer()

# Database setup
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class AuthResponse(BaseModel):
    """Authentication response model"""
    access_token: str
    token_type: str = "bearer"
    user: dict

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True
                }
            }
        }


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    role: str
    can_access_chatbot: bool
    can_access_dashboards: bool
    can_access_admin: bool
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_admin": False,
                "role": "participant_control",
                "can_access_chatbot": False,
                "can_access_dashboards": True,
                "can_access_admin": False,
                "created_at": "2025-12-04T12:00:00+00:00"
            }
        }


# ============================================================================
# Dependencies
# ============================================================================

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DBSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: Bearer token from request header
        db: Database session

    Returns:
        User object if authenticated

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


# ============================================================================
# Helper Functions
# ============================================================================

def create_user_session(db: DBSession, user_id: str, token: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Session:
    """Create a new session for a user"""
    session = Session(
        user_id=user_id,
        token=token,
        ip_address=ip_address,
        user_agent=user_agent,
        is_active=True,
        expires_at=get_token_expiry()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def user_to_dict(user: User) -> dict:
    """Convert User model to dictionary"""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "role": getattr(user, 'role', 'participant_control'),
        "can_access_chatbot": user.can_access_chatbot() if hasattr(user, 'can_access_chatbot') else True,
        "can_access_dashboards": user.can_access_dashboards() if hasattr(user, 'can_access_dashboards') else True,
        "can_access_admin": user.can_access_admin() if hasattr(user, 'can_access_admin') else user.is_admin,
        "created_at": user.created_at.isoformat()
    }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: DBSession = Depends(get_db)
):
    """
    Login with email and password

    - **email**: Registered email address
    - **password**: User password
    """
    # Find user (case-insensitive email match)
    from sqlalchemy import func
    user = db.query(User).filter(func.lower(User.email) == request.email.lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    # Create session
    create_user_session(db, user.id, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_to_dict(user)
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information

    Requires: Bearer token in Authorization header
    """
    return user_to_dict(current_user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DBSession = Depends(get_db)
):
    """
    Refresh access token — issues a new token if the current one is still valid.
    Call this before the token expires to keep the session alive.
    """
    old_token = credentials.credentials

    # Deactivate old session
    old_session = db.query(Session).filter(
        Session.token == old_token,
        Session.user_id == current_user.id
    ).first()
    if old_session:
        old_session.is_active = False

    # Create new token and session
    new_token = create_access_token(data={"sub": current_user.id})
    create_user_session(db, current_user.id, new_token)

    db.commit()

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "user": user_to_dict(current_user)
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: DBSession = Depends(get_db)
):
    """
    Logout current user (invalidate session)

    Requires: Bearer token in Authorization header
    """
    token = credentials.credentials

    # Find and deactivate session
    session = db.query(Session).filter(
        Session.token == token,
        Session.user_id == current_user.id
    ).first()

    if session:
        session.is_active = False
        db.commit()

    return {"message": "Successfully logged out"}


# Export router
__all__ = ["router"]
