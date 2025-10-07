from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

from ..core.models.integrations import Integration
from ..core.services.logging_service import StructuredLogger

class SyncResult(BaseModel):
    """Result of a sync operation."""
    success: bool
    records_processed: int = 0
    records_added: int = 0
    records_updated: int = 0
    records_deleted: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

class TestResult(BaseModel):
    """Result of a connection test."""
    success: bool
    message: str
    details: Dict[str, Any] = {}
    response_time_ms: Optional[float] = None

class BaseIntegration(ABC):
    """Base class for all integrations."""

    def __init__(self, integration: Integration):
        self.integration = integration
        self.logger = StructuredLogger(f"integration.{integration.integration_type}")

    @abstractmethod
    async def test_connection(self) -> TestResult:
        """Test the connection to the external service."""
        pass

    @abstractmethod
    async def sync(self) -> SyncResult:
        """Perform data synchronization."""
        pass

    @abstractmethod
    async def process_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Process an incoming webhook."""
        pass

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type."""
        auth_config = self.integration.auth_config
        auth_type = self.integration.auth_type

        headers = {}

        if auth_type == "api_key":
            api_key = auth_config.get("api_key")
            header_name = auth_config.get("header_name", "Authorization")
            prefix = auth_config.get("prefix", "Bearer")

            if api_key:
                headers[header_name] = f"{prefix} {api_key}" if prefix else api_key

        elif auth_type == "basic_auth":
            import base64
            username = auth_config.get("username")
            password = auth_config.get("password")

            if username and password:
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

        elif auth_type == "token":
            token = auth_config.get("token")
            token_type = auth_config.get("token_type", "Bearer")

            if token:
                headers["Authorization"] = f"{token_type} {token}"

        return headers

    def log_sync_start(self, sync_type: str = "incremental"):
        """Log the start of a sync operation."""
        self.logger.info("Sync started", {
            "integration_id": self.integration.id,
            "integration_type": self.integration.integration_type,
            "sync_type": sync_type
        })

    def log_sync_complete(self, result: SyncResult, duration_ms: float):
        """Log the completion of a sync operation."""
        self.logger.info("Sync completed", {
            "integration_id": self.integration.id,
            "integration_type": self.integration.integration_type,
            "success": result.success,
            "duration_ms": duration_ms,
            "records_processed": result.records_processed,
            "records_added": result.records_added,
            "records_updated": result.records_updated,
            "records_failed": result.records_failed
        })

    def log_webhook_received(self, event_type: str):
        """Log the receipt of a webhook."""
        self.logger.info("Webhook received", {
            "integration_id": self.integration.id,
            "integration_type": self.integration.integration_type,
            "event_type": event_type
        })

    def validate_config(self, required_fields: List[str]) -> bool:
        """Validate that required configuration fields are present."""
        config = self.integration.config

        for field in required_fields:
            if field not in config or not config[field]:
                self.logger.error("Missing required configuration field", {
                    "integration_id": self.integration.id,
                    "field": field
                })
                return False

        return True

    def handle_rate_limit(self, response_headers: Dict[str, str]) -> Optional[int]:
        """Handle rate limiting and return retry delay in seconds."""
        # Common rate limit headers
        remaining = response_headers.get("X-RateLimit-Remaining") or response_headers.get("X-Rate-Limit-Remaining")
        reset_time = response_headers.get("X-RateLimit-Reset") or response_headers.get("X-Rate-Limit-Reset")

        if remaining and int(remaining) == 0:
            if reset_time:
                try:
                    reset_timestamp = int(reset_time)
                    current_timestamp = int(datetime.utcnow().timestamp())
                    delay = max(reset_timestamp - current_timestamp, 60)  # At least 60 seconds

                    self.logger.warning("Rate limit reached", {
                        "integration_id": self.integration.id,
                        "retry_delay": delay
                    })

                    return delay
                except ValueError:
                    pass

            # Default delay if reset time is not available
            return 300  # 5 minutes

        return None