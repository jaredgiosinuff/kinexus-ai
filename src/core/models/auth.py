from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Table, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum
import uuid

Base = declarative_base()

# Association table for user-role many-to-many relationship
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id'), primary_key=True),
    Column('role_id', String, ForeignKey('roles.id'), primary_key=True)
)

# Association table for role-permission many-to-many relationship
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', String, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', String, ForeignKey('permissions.id'), primary_key=True)
)

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"

class AuthProvider(str, Enum):
    LOCAL = "local"
    COGNITO = "cognito"
    SAML = "saml"
    OAUTH = "oauth"

class Permission(Base):
    """Database model for permissions."""
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class Role(Base):
    """Database model for user roles."""
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

class User(Base):
    """Database model for users."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for external auth providers

    # Status and flags
    is_active = Column(Boolean, default=True, index=True)
    is_admin = Column(Boolean, default=False, index=True)
    is_verified = Column(Boolean, default=False)
    status = Column(String(50), default=UserStatus.ACTIVE, index=True)

    # Authentication provider info
    provider = Column(String(50), default=AuthProvider.LOCAL, index=True)
    provider_user_id = Column(String(255), nullable=True, index=True)
    provider_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)

    # Profile information
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="UTC")
    preferences = Column(JSON, nullable=True)

    # Security
    failed_login_attempts = Column(String, default="0")
    locked_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

class UserSession(Base):
    """Database model for user sessions."""
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    refresh_token_hash = Column(String(255), nullable=True)

    # Session metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

class AuthConfig(Base):
    """Database model for authentication configuration."""
    __tablename__ = "auth_config"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_type = Column(String(50), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    config = Column(JSON, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey('users.id'), nullable=True)

# Pydantic models for API

class UserRole(BaseModel):
    """Role information for API responses."""
    id: str
    name: str
    description: Optional[str]
    permissions: List[str] = []

class UserPermission(BaseModel):
    """Permission information for API responses."""
    id: str
    name: str
    description: Optional[str]
    category: str

class UserResponse(BaseModel):
    """User data for API responses."""
    id: str
    email: str
    name: str
    is_active: bool
    is_admin: bool
    is_verified: bool
    status: UserStatus
    provider: AuthProvider
    created_at: datetime
    last_login: Optional[datetime]
    timezone: str
    roles: List[UserRole] = []

class UserCreate(BaseModel):
    """Request model for creating users."""
    email: str
    name: str
    password: Optional[str] = None
    is_admin: bool = False
    provider: AuthProvider = AuthProvider.LOCAL
    roles: List[str] = []

class UserUpdate(BaseModel):
    """Request model for updating users."""
    name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    timezone: Optional[str] = None
    roles: Optional[List[str]] = None

class LoginRequest(BaseModel):
    """Request model for user login."""
    email: str
    password: str
    remember_me: bool = False

class LoginResponse(BaseModel):
    """Response model for successful login."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenValidationRequest(BaseModel):
    """Request model for token validation."""
    token: str

class TokenValidationResponse(BaseModel):
    """Response model for token validation."""
    valid: bool
    user: Optional[UserResponse] = None
    error: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    """Request model for password change."""
    current_password: str
    new_password: str

class PasswordResetRequest(BaseModel):
    """Request model for password reset."""
    email: str

class PasswordResetConfirmRequest(BaseModel):
    """Request model for password reset confirmation."""
    token: str
    new_password: str

class RoleCreateRequest(BaseModel):
    """Request model for creating roles."""
    name: str
    description: Optional[str] = None
    permissions: List[str] = []

class RoleUpdateRequest(BaseModel):
    """Request model for updating roles."""
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class PermissionCreateRequest(BaseModel):
    """Request model for creating permissions."""
    name: str
    description: Optional[str] = None
    category: str

class AuthConfigRequest(BaseModel):
    """Request model for authentication configuration."""
    provider_type: AuthProvider
    enabled: bool
    config: Dict[str, Any]

class AuthConfigResponse(BaseModel):
    """Response model for authentication configuration."""
    id: str
    provider_type: AuthProvider
    enabled: bool
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class UserPreferences(BaseModel):
    """User preferences model."""
    theme: str = "light"
    language: str = "en"
    notifications: Dict[str, bool] = {}
    dashboard_layout: Dict[str, Any] = {}

class SecurityEvent(BaseModel):
    """Security event model for audit logging."""
    event_type: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = {}
    timestamp: datetime = datetime.utcnow()

class SessionInfo(BaseModel):
    """Session information model."""
    id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    is_current: bool = False

class UserProfile(BaseModel):
    """Extended user profile model."""
    user: UserResponse
    sessions: List[SessionInfo] = []
    recent_activity: List[Dict[str, Any]] = []
    security_events: List[SecurityEvent] = []

# Default permissions for the system
DEFAULT_PERMISSIONS = [
    # Admin permissions
    {"name": "admin.users.create", "description": "Create new users", "category": "admin"},
    {"name": "admin.users.read", "description": "View user information", "category": "admin"},
    {"name": "admin.users.update", "description": "Update user information", "category": "admin"},
    {"name": "admin.users.delete", "description": "Delete users", "category": "admin"},
    {"name": "admin.roles.manage", "description": "Manage user roles", "category": "admin"},
    {"name": "admin.system.config", "description": "Configure system settings", "category": "admin"},
    {"name": "admin.integrations.manage", "description": "Manage integrations", "category": "admin"},
    {"name": "admin.monitoring.view", "description": "View system monitoring", "category": "admin"},

    # Agent permissions
    {"name": "agents.view", "description": "View agent information", "category": "agents"},
    {"name": "agents.manage", "description": "Manage agents", "category": "agents"},
    {"name": "agents.conversations.view", "description": "View agent conversations", "category": "agents"},
    {"name": "agents.conversations.manage", "description": "Manage agent conversations", "category": "agents"},

    # Document permissions
    {"name": "documents.read", "description": "Read documents", "category": "documents"},
    {"name": "documents.write", "description": "Create and edit documents", "category": "documents"},
    {"name": "documents.delete", "description": "Delete documents", "category": "documents"},
    {"name": "documents.review", "description": "Review document changes", "category": "documents"},

    # Integration permissions
    {"name": "integrations.use", "description": "Use integrations", "category": "integrations"},
    {"name": "integrations.configure", "description": "Configure integrations", "category": "integrations"},

    # API permissions
    {"name": "api.read", "description": "Read via API", "category": "api"},
    {"name": "api.write", "description": "Write via API", "category": "api"},
]

# Default roles for the system
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "System administrator with full access",
        "permissions": [p["name"] for p in DEFAULT_PERMISSIONS]
    },
    {
        "name": "user",
        "description": "Standard user with basic access",
        "permissions": [
            "documents.read",
            "documents.write",
            "integrations.use",
            "agents.view",
            "agents.conversations.view",
            "api.read"
        ]
    },
    {
        "name": "reviewer",
        "description": "Document reviewer with review permissions",
        "permissions": [
            "documents.read",
            "documents.review",
            "agents.view",
            "agents.conversations.view",
            "api.read"
        ]
    },
    {
        "name": "operator",
        "description": "System operator with monitoring access",
        "permissions": [
            "admin.monitoring.view",
            "agents.view",
            "agents.conversations.view",
            "documents.read",
            "api.read"
        ]
    }
]