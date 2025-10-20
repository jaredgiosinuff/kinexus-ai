"""
FastAPI dependencies for authentication, database sessions, and common utilities.

These dependencies are used across multiple router modules to ensure
consistent authentication, database access, and user authorization.
"""

from datetime import datetime
from typing import Generator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.config import settings
from database.connection import get_db_session
from database.models import User, UserRole

# Security scheme for JWT tokens
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    yield from get_db_session()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: JWT token from Authorization header
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Extract user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Convert to UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is disabled"
        )

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (alias for get_current_user with better name).

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: Active user object
    """
    return current_user


def require_role(required_role: UserRole):
    """
    Create a dependency that requires a specific user role or higher.

    Args:
        required_role: Minimum required role

    Returns:
        Dependency function that checks user role
    """

    def check_role(current_user: User = Depends(get_current_active_user)) -> User:
        # Role hierarchy (higher index = more permissions)
        role_hierarchy = [
            UserRole.VIEWER,
            UserRole.REVIEWER,
            UserRole.LEAD_REVIEWER,
            UserRole.ADMIN,
        ]

        if current_user.role not in role_hierarchy:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid user role"
            )

        user_level = role_hierarchy.index(current_user.role)
        required_level = role_hierarchy.index(required_role)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )

        return current_user

    return check_role


# Common role dependencies
require_viewer = require_role(UserRole.VIEWER)
require_reviewer = require_role(UserRole.REVIEWER)
require_lead_reviewer = require_role(UserRole.LEAD_REVIEWER)
require_admin = require_role(UserRole.ADMIN)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """
    Extract User-Agent from request.

    Args:
        request: FastAPI request object

    Returns:
        str: User agent string
    """
    return request.headers.get("User-Agent", "unknown")


async def validate_webhook_signature(
    request: Request, signature_header: str, secret: str
) -> bool:
    """
    Validate webhook signature using HMAC.

    Args:
        request: FastAPI request object
        signature_header: Header name containing signature
        secret: Webhook secret for validation

    Returns:
        bool: True if signature is valid

    Raises:
        HTTPException: If signature validation fails
    """
    import hashlib
    import hmac

    # Get signature from headers
    signature = request.headers.get(signature_header)
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature"
        )

    # Read request body
    body = await request.body()

    # Calculate expected signature
    expected_signature = (
        "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )

    # Compare signatures (constant time comparison)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    return True


class AuditLogger:
    """Dependency for logging user actions for audit trail."""

    def __init__(
        self, action: str, resource_type: str, resource_id: Optional[UUID] = None
    ):
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id

    def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        """Log audit event."""
        from database.models import AuditLog

        audit_log = AuditLog(
            user_id=current_user.id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        db.add(audit_log)
        db.commit()

        return audit_log


def create_audit_logger(action: str, resource_type: str):
    """
    Create an audit logger dependency.

    Args:
        action: Action being performed
        resource_type: Type of resource being acted upon

    Returns:
        AuditLogger dependency
    """
    return AuditLogger(action, resource_type)
