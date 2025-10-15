"""
Authentication router for Kinexus AI.

Handles user login, token generation, and user management endpoints.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from api.dependencies import (
    get_client_ip,
    get_current_active_user,
    get_db,
    get_user_agent,
    require_admin,
)
from core.config import settings
from database.models import AuditLog, User, UserRole

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Pydantic models
class Token(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""

    id: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    last_login: datetime = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model."""

    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.REVIEWER


class UserUpdate(BaseModel):
    """User update model."""

    first_name: str = None
    last_name: str = None
    role: UserRole = None
    is_active: bool = None


class PasswordChange(BaseModel):
    """Password change model."""

    current_password: str
    new_password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return access token.

    Args:
        request: FastAPI request object
        form_data: Login form data (username/email and password)
        db: Database session

    Returns:
        Token: JWT access token and metadata

    Raises:
        HTTPException: If authentication fails
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        # Log failed login attempt
        audit_log = AuditLog(
            action="login_failed",
            resource_type="user",
            resource_id=None,
            audit_metadata={"email": form_data.username},
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        db.add(audit_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled"
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # Update last login and log successful login
    user.last_login = datetime.utcnow()

    audit_log = AuditLog(
        user_id=user.id,
        action="login_success",
        resource_type="user",
        resource_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    db.add(audit_log)
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Current user data
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update current user information.

    Args:
        user_update: User update data
        request: FastAPI request object
        current_user: Current authenticated user
        db: Database session

    Returns:
        UserResponse: Updated user data
    """
    # Store old values for audit
    old_values = {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role.value if current_user.role else None,
    }

    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "role" and current_user.role != UserRole.ADMIN:
            # Only admins can change their own role
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can change user roles",
            )
        setattr(current_user, field, value)

    # Log the update
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_updated",
        resource_type="user",
        resource_id=current_user.id,
        old_values=old_values,
        new_values=update_data,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    db.add(audit_log)
    db.commit()

    return current_user


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Change current user's password.

    Args:
        password_change: Password change data
        request: FastAPI request object
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Success message
    """
    # Verify current password
    if not verify_password(
        password_change.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.password_hash = get_password_hash(password_change.new_password)

    # Log password change
    audit_log = AuditLog(
        user_id=current_user.id,
        action="password_changed",
        resource_type="user",
        resource_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    db.add(audit_log)
    db.commit()

    return {"detail": "Password changed successfully"}


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_create: UserCreate,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new user (admin only).

    Args:
        user_create: User creation data
        request: FastAPI request object
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        UserResponse: Created user data
    """
    from uuid import uuid4

    # Check if user already exists
    existing_user = (
        db.query(User).filter(User.email == user_create.email.lower()).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Create new user
    new_user = User(
        id=uuid4(),
        email=user_create.email.lower(),
        password_hash=get_password_hash(user_create.password),
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        role=user_create.role,
        is_active=True,
    )

    db.add(new_user)

    # Log user creation
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_created",
        resource_type="user",
        resource_id=new_user.id,
        new_values={
            "email": new_user.email,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "role": new_user.role.value,
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    db.add(audit_log)
    db.commit()

    return new_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Logout current user (invalidate token on client side).

    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        db: Database session

    Returns:
        dict: Success message
    """
    # Log logout
    audit_log = AuditLog(
        user_id=current_user.id,
        action="logout",
        resource_type="user",
        resource_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    db.add(audit_log)
    db.commit()

    return {"detail": "Successfully logged out"}
