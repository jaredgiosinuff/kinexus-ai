"""
Configuration management for Kinexus AI.

Centralizes all environment-based configuration with proper validation
and type safety using Pydantic settings.
"""

import os
from typing import List, Optional
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "kinexusai"
    DB_USER: str = "kinexus"
    DB_PASSWORD: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # Redis (for caching and real-time features)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # AI/ML Configuration
    BEDROCK_REGION: str = "us-east-1"
    DEFAULT_AI_MODEL: str = "anthropic.claude-3-opus-20240229"
    AI_MAX_TOKENS: int = 4000
    AI_TEMPERATURE: float = 0.3
    AI_TIMEOUT_SECONDS: int = 60

    # Review Configuration
    DEFAULT_REVIEW_PRIORITY: int = 5
    MAX_REVIEW_QUEUE_SIZE: int = 1000
    REVIEW_TIMEOUT_HOURS: int = 72
    AUTO_ASSIGN_REVIEWS: bool = True

    # Webhook Configuration
    WEBHOOK_SECRET_GITHUB: Optional[str] = None
    WEBHOOK_SECRET_JIRA: Optional[str] = None
    WEBHOOK_TIMEOUT_SECONDS: int = 30

    # File Storage
    STORAGE_BACKEND: str = "s3"  # 's3' or 'local'
    S3_BUCKET_NAME: Optional[str] = None
    LOCAL_STORAGE_PATH: str = "/tmp/kinexus-docs"

    # Email (for notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@kinexusai.local"

    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_INTERVAL_SECONDS: int = 60
    METRICS_PORT: int = 8090

    # Automation
    ENABLE_MULTI_AGENT_AUTOMATION: bool = False
    SYSTEM_USER_EMAIL: str = "admin@kinexusai.com"
    GITHUB_ACTIONS_WEBHOOK_TOKEN: Optional[str] = None

    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ['development', 'staging', 'production']
        if v not in allowed:
            raise ValueError(f'Environment must be one of: {allowed}')
        return v

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v

    @property
    def database_url(self) -> str:
        """Build database URL from components."""
        password = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return f"postgresql://{self.DB_USER}{password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
