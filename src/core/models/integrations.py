from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum
import uuid

Base = declarative_base()

class IntegrationType(str, Enum):
    """Types of integrations available."""
    # Source integrations (read data from)
    GITHUB = "github"
    GITLAB = "gitlab"
    JIRA = "jira"
    CONFLUENCE = "confluence"
    SHAREPOINT = "sharepoint"
    MONDAY = "monday"
    SERVICENOW = "servicenow"
    SLACK = "slack"
    TEAMS = "teams"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    NOTION = "notion"
    ASANA = "asana"
    TRELLO = "trello"

    # Target integrations (write data to)
    ZENDESK = "zendesk"
    FRESHDESK = "freshdesk"
    HELPSCOUT = "helpscout"
    INTERCOM = "intercom"

    # Analytics and monitoring
    GOOGLE_ANALYTICS = "google_analytics"
    MIXPANEL = "mixpanel"
    AMPLITUDE = "amplitude"

    # Communication
    EMAIL = "email"
    WEBHOOK = "webhook"
    ZAPIER = "zapier"

class IntegrationStatus(str, Enum):
    """Status of an integration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    CONFIGURING = "configuring"
    TESTING = "testing"

class SyncDirection(str, Enum):
    """Direction of data synchronization."""
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    BIDIRECTIONAL = "bidirectional"

class AuthType(str, Enum):
    """Authentication types for integrations."""
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC_AUTH = "basic_auth"
    TOKEN = "token"
    CUSTOM = "custom"

class Integration(Base):
    """Database model for integrations."""
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Integration type and configuration
    integration_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), default=IntegrationStatus.INACTIVE, index=True)
    sync_direction = Column(String(50), default=SyncDirection.READ_ONLY)

    # Authentication
    auth_type = Column(String(50), nullable=False)
    auth_config = Column(JSON, nullable=True)  # Encrypted sensitive data

    # Configuration
    config = Column(JSON, nullable=False)
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)

    # Sync settings
    sync_frequency = Column(Integer, default=3600)  # seconds
    last_sync = Column(DateTime, nullable=True)
    next_sync = Column(DateTime, nullable=True)
    sync_enabled = Column(Boolean, default=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    last_error = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey('users.id'), nullable=True)

    # Relationships
    sync_logs = relationship("IntegrationSyncLog", back_populates="integration", cascade="all, delete-orphan")
    webhook_deliveries = relationship("WebhookDelivery", back_populates="integration", cascade="all, delete-orphan")

class IntegrationSyncLog(Base):
    """Database model for integration sync logs."""
    __tablename__ = "integration_sync_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String, ForeignKey('integrations.id'), nullable=False, index=True)

    # Sync details
    sync_type = Column(String(50), nullable=False)  # full, incremental, webhook
    direction = Column(String(50), nullable=False)  # read, write
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Results
    status = Column(String(50), nullable=False)  # success, failure, partial
    records_processed = Column(Integer, default=0)
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_deleted = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)

    # Error information
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True)

    # Relationships
    integration = relationship("Integration", back_populates="sync_logs")

class WebhookDelivery(Base):
    """Database model for webhook deliveries."""
    __tablename__ = "webhook_deliveries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    integration_id = Column(String, ForeignKey('integrations.id'), nullable=False, index=True)

    # Webhook details
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    headers = Column(JSON, nullable=True)

    # Delivery status
    status = Column(String(50), nullable=False)  # pending, delivered, failed
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    first_attempt = Column(DateTime, nullable=True)
    last_attempt = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    next_retry = Column(DateTime, nullable=True)

    # Response information
    response_status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    integration = relationship("Integration", back_populates="webhook_deliveries")

# Pydantic models for API

class IntegrationConfig(BaseModel):
    """Base configuration for integrations."""
    pass

class GitHubConfig(IntegrationConfig):
    """GitHub integration configuration."""
    repositories: List[str] = Field(..., description="List of repositories to monitor")
    events: List[str] = Field(default=["push", "pull_request", "issues"], description="Events to listen for")
    branch_filter: Optional[str] = Field(None, description="Branch pattern to filter")
    include_private: bool = Field(default=False, description="Include private repositories")

class JiraConfig(IntegrationConfig):
    """Jira integration configuration."""
    server_url: str = Field(..., description="Jira server URL")
    projects: List[str] = Field(..., description="Jira projects to monitor")
    issue_types: List[str] = Field(default=["Story", "Bug", "Task"], description="Issue types to include")
    custom_fields: Dict[str, str] = Field(default={}, description="Custom field mappings")
    webhook_events: List[str] = Field(default=["jira:issue_created", "jira:issue_updated"], description="Webhook events")

class SharePointConfig(IntegrationConfig):
    """SharePoint integration configuration."""
    site_url: str = Field(..., description="SharePoint site URL")
    libraries: List[str] = Field(..., description="Document libraries to monitor")
    file_types: List[str] = Field(default=["docx", "pdf", "pptx"], description="File types to include")
    folders: List[str] = Field(default=["/"], description="Folders to monitor")

class MondayConfig(IntegrationConfig):
    """Monday.com integration configuration."""
    boards: List[int] = Field(..., description="Board IDs to monitor")
    columns: List[str] = Field(default=[], description="Specific columns to sync")
    webhook_events: List[str] = Field(default=["create_item", "change_column_value"], description="Webhook events")

class ServiceNowConfig(IntegrationConfig):
    """ServiceNow integration configuration."""
    instance_url: str = Field(..., description="ServiceNow instance URL")
    tables: List[str] = Field(default=["incident", "change_request", "problem"], description="Tables to monitor")
    filters: Dict[str, str] = Field(default={}, description="Table-specific filters")
    webhook_events: List[str] = Field(default=["insert", "update"], description="Webhook events")

class SlackConfig(IntegrationConfig):
    """Slack integration configuration."""
    channels: List[str] = Field(..., description="Channels to monitor")
    message_types: List[str] = Field(default=["message"], description="Message types to include")
    bot_mentions: bool = Field(default=True, description="Include bot mentions")
    keywords: List[str] = Field(default=[], description="Keywords to filter messages")

class AuthConfig(BaseModel):
    """Authentication configuration for integrations."""
    pass

class OAuth2Config(AuthConfig):
    """OAuth2 authentication configuration."""
    client_id: str
    client_secret: str
    scope: List[str] = []
    redirect_uri: Optional[str] = None
    authorization_url: Optional[str] = None
    token_url: Optional[str] = None

class APIKeyConfig(AuthConfig):
    """API key authentication configuration."""
    api_key: str
    header_name: str = "Authorization"
    prefix: str = "Bearer"

class BasicAuthConfig(AuthConfig):
    """Basic authentication configuration."""
    username: str
    password: str

class TokenConfig(AuthConfig):
    """Token-based authentication configuration."""
    token: str
    token_type: str = "Bearer"

# Request/Response models

class IntegrationCreateRequest(BaseModel):
    """Request model for creating integrations."""
    name: str
    description: Optional[str] = None
    integration_type: IntegrationType
    auth_type: AuthType
    auth_config: Dict[str, Any]
    config: Dict[str, Any]
    sync_direction: SyncDirection = SyncDirection.READ_ONLY
    sync_frequency: int = 3600
    webhook_url: Optional[str] = None

class IntegrationUpdateRequest(BaseModel):
    """Request model for updating integrations."""
    name: Optional[str] = None
    description: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    sync_direction: Optional[SyncDirection] = None
    sync_frequency: Optional[int] = None
    sync_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None

class IntegrationResponse(BaseModel):
    """Response model for integration data."""
    id: str
    name: str
    description: Optional[str]
    integration_type: IntegrationType
    status: IntegrationStatus
    sync_direction: SyncDirection
    auth_type: AuthType
    sync_frequency: int
    last_sync: Optional[datetime]
    next_sync: Optional[datetime]
    sync_enabled: bool
    error_message: Optional[str]
    error_count: int
    created_at: datetime
    updated_at: datetime

class DetailedIntegrationResponse(IntegrationResponse):
    """Detailed response model including configuration."""
    config: Dict[str, Any]
    webhook_url: Optional[str]
    recent_sync_logs: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {}

class IntegrationTestRequest(BaseModel):
    """Request model for testing integrations."""
    test_type: str = "connection"
    parameters: Dict[str, Any] = {}

class IntegrationTestResponse(BaseModel):
    """Response model for integration tests."""
    success: bool
    message: str
    details: Dict[str, Any] = {}
    test_results: List[Dict[str, Any]] = []

class SyncRequest(BaseModel):
    """Request model for manual sync triggers."""
    sync_type: str = "incremental"  # full, incremental
    direction: Optional[SyncDirection] = None
    parameters: Dict[str, Any] = {}

class SyncResponse(BaseModel):
    """Response model for sync operations."""
    sync_id: str
    status: str
    message: str
    estimated_duration: Optional[int] = None

class SyncLogResponse(BaseModel):
    """Response model for sync log data."""
    id: str
    sync_type: str
    direction: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    status: str
    records_processed: int
    records_added: int
    records_updated: int
    records_deleted: int
    records_failed: int
    error_message: Optional[str]

class IntegrationStats(BaseModel):
    """Statistics for integrations."""
    total_integrations: int
    active_integrations: int
    failed_integrations: int
    total_syncs_today: int
    successful_syncs_today: int
    failed_syncs_today: int
    avg_sync_duration: float
    data_processed_today: int

class WebhookConfig(BaseModel):
    """Webhook configuration."""
    url: str
    secret: Optional[str] = None
    events: List[str] = []
    headers: Dict[str, str] = {}
    retry_policy: Dict[str, Any] = {
        "max_attempts": 3,
        "backoff_factor": 2,
        "initial_delay": 60
    }

class IntegrationTemplate(BaseModel):
    """Template for common integration configurations."""
    name: str
    integration_type: IntegrationType
    description: str
    default_config: Dict[str, Any]
    auth_type: AuthType
    required_fields: List[str]
    optional_fields: List[str]
    setup_instructions: str
    documentation_url: Optional[str] = None

# Common configuration schemas for validation
INTEGRATION_SCHEMAS = {
    IntegrationType.GITHUB: {
        "type": "object",
        "properties": {
            "repositories": {"type": "array", "items": {"type": "string"}},
            "events": {"type": "array", "items": {"type": "string"}},
            "branch_filter": {"type": "string"},
            "include_private": {"type": "boolean"}
        },
        "required": ["repositories"]
    },
    IntegrationType.JIRA: {
        "type": "object",
        "properties": {
            "server_url": {"type": "string", "format": "uri"},
            "projects": {"type": "array", "items": {"type": "string"}},
            "issue_types": {"type": "array", "items": {"type": "string"}},
            "custom_fields": {"type": "object"},
            "webhook_events": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["server_url", "projects"]
    },
    IntegrationType.SHAREPOINT: {
        "type": "object",
        "properties": {
            "site_url": {"type": "string", "format": "uri"},
            "libraries": {"type": "array", "items": {"type": "string"}},
            "file_types": {"type": "array", "items": {"type": "string"}},
            "folders": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["site_url", "libraries"]
    },
    IntegrationType.MONDAY: {
        "type": "object",
        "properties": {
            "boards": {"type": "array", "items": {"type": "integer"}},
            "columns": {"type": "array", "items": {"type": "string"}},
            "webhook_events": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["boards"]
    },
    IntegrationType.SERVICENOW: {
        "type": "object",
        "properties": {
            "instance_url": {"type": "string", "format": "uri"},
            "tables": {"type": "array", "items": {"type": "string"}},
            "filters": {"type": "object"},
            "webhook_events": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["instance_url", "tables"]
    }
}

# Integration capabilities matrix
INTEGRATION_CAPABILITIES = {
    IntegrationType.GITHUB: {
        "supports_webhooks": True,
        "supports_polling": True,
        "supports_write": False,
        "rate_limit": 5000,  # requests per hour
        "batch_size": 100
    },
    IntegrationType.JIRA: {
        "supports_webhooks": True,
        "supports_polling": True,
        "supports_write": True,
        "rate_limit": 1000,
        "batch_size": 50
    },
    IntegrationType.SHAREPOINT: {
        "supports_webhooks": True,
        "supports_polling": True,
        "supports_write": True,
        "rate_limit": 2000,
        "batch_size": 25
    },
    IntegrationType.MONDAY: {
        "supports_webhooks": True,
        "supports_polling": True,
        "supports_write": True,
        "rate_limit": 1000,
        "batch_size": 50
    },
    IntegrationType.SERVICENOW: {
        "supports_webhooks": True,
        "supports_polling": True,
        "supports_write": True,
        "rate_limit": 5000,
        "batch_size": 100
    }
}