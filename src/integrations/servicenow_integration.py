import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_integration import BaseIntegration, SyncResult, TestResult

class ServiceNowIntegration(BaseIntegration):
    """ServiceNow integration for IT service management."""

    def __init__(self, integration):
        super().__init__(integration)
        self.required_config_fields = ["instance_url", "tables"]

    @property
    def api_base_url(self) -> str:
        """Get the API base URL from configuration."""
        instance_url = self.integration.config.get("instance_url", "")
        return f"{instance_url.rstrip('/')}/api/now"

    async def test_connection(self) -> TestResult:
        """Test connection to ServiceNow API."""
        try:
            headers = self.get_auth_headers()
            headers["Accept"] = "application/json"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_base_url}/table/sys_user?sysparm_limit=1",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        return TestResult(
                            success=True,
                            message="Connection successful",
                            details={"users_found": len(data.get("result", []))}
                        )
                    else:
                        return TestResult(
                            success=False,
                            message=f"HTTP {response.status}"
                        )

        except Exception as e:
            return TestResult(
                success=False,
                message=f"Connection failed: {str(e)}"
            )

    async def sync(self) -> SyncResult:
        """Sync data from ServiceNow tables."""
        # Implementation would sync incidents, change requests, problems, etc.
        # This is a placeholder implementation

        return SyncResult(
            success=True,
            records_processed=0,
            metadata={"implementation": "placeholder"}
        )

    async def process_webhook(self, event_type: str, payload: Dict[str, Any]) -> bool:
        """Process ServiceNow webhook events."""
        self.log_webhook_received(event_type)

        # Implementation would handle record insert, update, delete events
        # This is a placeholder implementation

        return True