import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type

from sqlalchemy.orm import Session

from ..database import get_database_session
from ..integrations.base_integration import BaseIntegration
from ..integrations.github_integration import GitHubIntegration
from ..integrations.jira_integration import JiraIntegration
from ..integrations.monday_integration import MondayIntegration
from ..integrations.servicenow_integration import ServiceNowIntegration
from ..integrations.sharepoint_integration import SharePointIntegration
from ..models.integrations import (
    INTEGRATION_CAPABILITIES,
    INTEGRATION_SCHEMAS,
    Integration,
    IntegrationStatus,
    IntegrationSyncLog,
    IntegrationTestResponse,
    IntegrationType,
    IntegrationUpdateRequest,
)
from ..repositories.integration_repository import IntegrationRepository
from ..services.logging_service import StructuredLogger

logger = StructuredLogger("service.integration")


class IntegrationService:
    """Service for managing integrations."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_database_session()
        self.integration_repo = IntegrationRepository(self.db)
        self._integration_classes = self._register_integration_classes()

    def _register_integration_classes(
        self,
    ) -> Dict[IntegrationType, Type[BaseIntegration]]:
        """Register all available integration classes."""
        return {
            IntegrationType.GITHUB: GitHubIntegration,
            IntegrationType.JIRA: JiraIntegration,
            IntegrationType.SHAREPOINT: SharePointIntegration,
            IntegrationType.MONDAY: MondayIntegration,
            IntegrationType.SERVICENOW: ServiceNowIntegration,
        }

    async def create_integration(
        self,
        name: str,
        integration_type: str,
        config: Dict[str, Any],
        auth_type: str = "api_key",
        auth_config: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> Integration:
        """Create a new integration."""
        try:
            # Validate integration type
            if integration_type not in [t.value for t in IntegrationType]:
                raise ValueError(f"Invalid integration type: {integration_type}")

            # Validate configuration
            self._validate_config(integration_type, config)

            # Create integration
            integration = await self.integration_repo.create_integration(
                name=name,
                integration_type=integration_type,
                config=config,
                auth_type=auth_type,
                auth_config=auth_config or {},
                created_by=created_by,
            )

            logger.info(
                "Integration created",
                {
                    "integration_id": integration.id,
                    "name": name,
                    "type": integration_type,
                },
            )

            return integration

        except Exception as e:
            logger.error(
                "Failed to create integration",
                {"name": name, "type": integration_type, "error": str(e)},
            )
            raise

    async def get_integration(self, integration_id: str) -> Optional[Integration]:
        """Get an integration by ID."""
        return await self.integration_repo.get_by_id(integration_id)

    async def get_all_integrations(self) -> List[Integration]:
        """Get all integrations."""
        return await self.integration_repo.get_all()

    async def update_integration(
        self, integration_id: str, update_data: IntegrationUpdateRequest
    ) -> Optional[Integration]:
        """Update an integration."""
        try:
            integration = await self.get_integration(integration_id)
            if not integration:
                return None

            # Validate new configuration if provided
            if update_data.config:
                self._validate_config(integration.integration_type, update_data.config)

            # Update integration
            updated_integration = await self.integration_repo.update_integration(
                integration_id, update_data.dict(exclude_unset=True)
            )

            logger.info(
                "Integration updated",
                {
                    "integration_id": integration_id,
                    "updated_fields": list(update_data.dict(exclude_unset=True).keys()),
                },
            )

            return updated_integration

        except Exception as e:
            logger.error(
                "Failed to update integration",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def delete_integration(self, integration_id: str) -> bool:
        """Delete an integration."""
        try:
            result = await self.integration_repo.delete_integration(integration_id)

            if result:
                logger.info("Integration deleted", {"integration_id": integration_id})

            return result

        except Exception as e:
            logger.error(
                "Failed to delete integration",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def toggle_integration(self, integration_id: str, enabled: bool) -> bool:
        """Enable or disable an integration."""
        try:
            integration = await self.get_integration(integration_id)
            if not integration:
                return False

            new_status = (
                IntegrationStatus.ACTIVE if enabled else IntegrationStatus.INACTIVE
            )

            await self.integration_repo.update_integration(
                integration_id, {"status": new_status, "sync_enabled": enabled}
            )

            logger.info(
                "Integration toggled",
                {
                    "integration_id": integration_id,
                    "enabled": enabled,
                    "new_status": new_status,
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to toggle integration",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def test_integration(self, integration_id: str) -> IntegrationTestResponse:
        """Test an integration connection."""
        try:
            integration = await self.get_integration(integration_id)
            if not integration:
                return IntegrationTestResponse(
                    success=False, message="Integration not found"
                )

            # Get integration class
            integration_class = self._integration_classes.get(
                IntegrationType(integration.integration_type)
            )
            if not integration_class:
                return IntegrationTestResponse(
                    success=False,
                    message=f"Integration type {integration.integration_type} not supported",
                )

            # Create integration instance and test
            integration_instance = integration_class(integration)
            test_result = await integration_instance.test_connection()

            logger.info(
                "Integration tested",
                {
                    "integration_id": integration_id,
                    "success": test_result.success,
                    "type": integration.integration_type,
                },
            )

            return test_result

        except Exception as e:
            logger.error(
                "Integration test failed",
                {"integration_id": integration_id, "error": str(e)},
            )
            return IntegrationTestResponse(
                success=False, message=f"Test failed: {str(e)}"
            )

    async def sync_integration(
        self,
        integration_id: str,
        sync_type: str = "incremental",
        direction: Optional[str] = None,
    ) -> str:
        """Trigger a manual sync for an integration."""
        try:
            integration = await self.get_integration(integration_id)
            if not integration:
                raise ValueError("Integration not found")

            if integration.status != IntegrationStatus.ACTIVE:
                raise ValueError("Integration is not active")

            # Create sync log
            sync_log = await self.integration_repo.create_sync_log(
                integration_id=integration_id,
                sync_type=sync_type,
                direction=direction or integration.sync_direction,
                status="started",
            )

            # Get integration class and perform sync
            integration_class = self._integration_classes.get(
                IntegrationType(integration.integration_type)
            )
            if not integration_class:
                raise ValueError(
                    f"Integration type {integration.integration_type} not supported"
                )

            integration_instance = integration_class(integration)

            # Start sync in background
            asyncio.create_task(self._perform_sync(integration_instance, sync_log.id))

            logger.info(
                "Manual sync triggered",
                {
                    "integration_id": integration_id,
                    "sync_log_id": sync_log.id,
                    "sync_type": sync_type,
                },
            )

            return sync_log.id

        except Exception as e:
            logger.error(
                "Failed to trigger sync",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def _perform_sync(
        self, integration_instance: BaseIntegration, sync_log_id: str
    ):
        """Perform the actual sync operation."""
        try:
            start_time = datetime.utcnow()

            # Perform sync
            result = await integration_instance.sync()

            # Update sync log with results
            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds())

            await self.integration_repo.update_sync_log(
                sync_log_id,
                {
                    "status": "success" if result.success else "failure",
                    "completed_at": end_time,
                    "duration_seconds": duration,
                    "records_processed": result.records_processed,
                    "records_added": result.records_added,
                    "records_updated": result.records_updated,
                    "records_deleted": result.records_deleted,
                    "records_failed": result.records_failed,
                    "error_message": result.error_message,
                    "metadata": result.metadata,
                },
            )

            # Update integration last sync time
            await self.integration_repo.update_integration(
                integration_instance.integration.id,
                {
                    "last_sync": end_time,
                    "next_sync": end_time
                    + timedelta(
                        seconds=integration_instance.integration.sync_frequency
                    ),
                    "error_count": (
                        0
                        if result.success
                        else integration_instance.integration.error_count + 1
                    ),
                    "error_message": (
                        result.error_message if not result.success else None
                    ),
                },
            )

            logger.info(
                "Sync completed",
                {
                    "integration_id": integration_instance.integration.id,
                    "sync_log_id": sync_log_id,
                    "success": result.success,
                    "duration": duration,
                    "records_processed": result.records_processed,
                },
            )

        except Exception as e:
            # Update sync log with error
            await self.integration_repo.update_sync_log(
                sync_log_id,
                {
                    "status": "failure",
                    "completed_at": datetime.utcnow(),
                    "error_message": str(e),
                },
            )

            logger.error(
                "Sync failed",
                {
                    "integration_id": integration_instance.integration.id,
                    "sync_log_id": sync_log_id,
                    "error": str(e),
                },
            )

    async def get_sync_logs(
        self, integration_id: str, limit: int = 50, status_filter: Optional[str] = None
    ) -> List[IntegrationSyncLog]:
        """Get sync logs for an integration."""
        return await self.integration_repo.get_sync_logs(
            integration_id, limit, status_filter
        )

    async def handle_webhook(
        self,
        integration_id: str,
        event_type: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Handle incoming webhook."""
        try:
            integration = await self.get_integration(integration_id)
            if not integration:
                logger.warning(
                    "Webhook received for unknown integration",
                    {"integration_id": integration_id},
                )
                return False

            if integration.status != IntegrationStatus.ACTIVE:
                logger.warning(
                    "Webhook received for inactive integration",
                    {"integration_id": integration_id, "status": integration.status},
                )
                return False

            # Create webhook delivery record
            delivery = await self.integration_repo.create_webhook_delivery(
                integration_id=integration_id,
                event_type=event_type,
                payload=payload,
                headers=headers or {},
            )

            # Get integration class and process webhook
            integration_class = self._integration_classes.get(
                IntegrationType(integration.integration_type)
            )
            if not integration_class:
                logger.error(
                    "Unsupported integration type for webhook",
                    {
                        "integration_id": integration_id,
                        "type": integration.integration_type,
                    },
                )
                return False

            integration_instance = integration_class(integration)

            # Process webhook in background
            asyncio.create_task(
                self._process_webhook(
                    integration_instance, delivery.id, event_type, payload
                )
            )

            logger.info(
                "Webhook received and queued",
                {
                    "integration_id": integration_id,
                    "delivery_id": delivery.id,
                    "event_type": event_type,
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to handle webhook",
                {
                    "integration_id": integration_id,
                    "event_type": event_type,
                    "error": str(e),
                },
            )
            return False

    async def _process_webhook(
        self,
        integration_instance: BaseIntegration,
        delivery_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ):
        """Process a webhook delivery."""
        try:
            _start_time = datetime.utcnow()

            # Process the webhook
            result = await integration_instance.process_webhook(event_type, payload)

            # Update delivery record
            await self.integration_repo.update_webhook_delivery(
                delivery_id,
                {
                    "status": "delivered" if result else "failed",
                    "delivered_at": datetime.utcnow(),
                    "response_status_code": 200 if result else 500,
                    "attempts": 1,
                },
            )

            logger.info(
                "Webhook processed",
                {
                    "integration_id": integration_instance.integration.id,
                    "delivery_id": delivery_id,
                    "success": result,
                    "event_type": event_type,
                },
            )

        except Exception as e:
            # Update delivery record with error
            await self.integration_repo.update_webhook_delivery(
                delivery_id,
                {"status": "failed", "error_message": str(e), "attempts": 1},
            )

            logger.error(
                "Webhook processing failed",
                {
                    "integration_id": integration_instance.integration.id,
                    "delivery_id": delivery_id,
                    "event_type": event_type,
                    "error": str(e),
                },
            )

    async def get_integration_stats(
        self, integration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics for integrations."""
        return await self.integration_repo.get_integration_stats(integration_id)

    async def get_available_integration_types(self) -> List[Dict[str, Any]]:
        """Get list of available integration types with their capabilities."""
        types = []
        for integration_type in IntegrationType:
            capabilities = INTEGRATION_CAPABILITIES.get(integration_type, {})
            types.append(
                {
                    "type": integration_type.value,
                    "name": integration_type.value.replace("_", " ").title(),
                    "capabilities": capabilities,
                    "supported": integration_type in self._integration_classes,
                }
            )

        return types

    def _validate_config(self, integration_type: str, config: Dict[str, Any]):
        """Validate integration configuration against schema."""
        try:
            schema = INTEGRATION_SCHEMAS.get(IntegrationType(integration_type))
            if not schema:
                return  # No validation schema available

            # Basic validation - check required fields
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")

            # Type validation for properties
            properties = schema.get("properties", {})
            for field, value in config.items():
                if field in properties:
                    field_schema = properties[field]
                    self._validate_field(field, value, field_schema)

        except Exception as e:
            logger.error(
                "Configuration validation failed",
                {"integration_type": integration_type, "error": str(e)},
            )
            raise ValueError(f"Invalid configuration: {str(e)}")

    def _validate_field(
        self, field_name: str, value: Any, field_schema: Dict[str, Any]
    ):
        """Validate a single field against its schema."""
        field_type = field_schema.get("type")

        if field_type == "string" and not isinstance(value, str):
            raise ValueError(f"Field {field_name} must be a string")
        elif field_type == "integer" and not isinstance(value, int):
            raise ValueError(f"Field {field_name} must be an integer")
        elif field_type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"Field {field_name} must be a boolean")
        elif field_type == "array" and not isinstance(value, list):
            raise ValueError(f"Field {field_name} must be an array")
        elif field_type == "object" and not isinstance(value, dict):
            raise ValueError(f"Field {field_name} must be an object")

        # Additional validations
        if field_schema.get("format") == "uri" and not self._is_valid_uri(value):
            raise ValueError(f"Field {field_name} must be a valid URI")

    def _is_valid_uri(self, uri: str) -> bool:
        """Check if a string is a valid URI."""
        try:
            from urllib.parse import urlparse

            result = urlparse(uri)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    async def schedule_syncs(self):
        """Schedule automatic syncs for active integrations."""
        try:
            active_integrations = await self.integration_repo.get_active_integrations()
            current_time = datetime.utcnow()

            for integration in active_integrations:
                if (
                    integration.sync_enabled
                    and integration.next_sync
                    and integration.next_sync <= current_time
                ):

                    try:
                        await self.sync_integration(integration.id, "incremental")
                    except Exception as e:
                        logger.error(
                            "Scheduled sync failed",
                            {"integration_id": integration.id, "error": str(e)},
                        )

        except Exception as e:
            logger.error("Failed to schedule syncs", {"error": str(e)})

    async def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old sync logs and webhook deliveries."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            deleted_logs = await self.integration_repo.cleanup_old_sync_logs(
                cutoff_date
            )
            deleted_deliveries = (
                await self.integration_repo.cleanup_old_webhook_deliveries(cutoff_date)
            )

            logger.info(
                "Cleanup completed",
                {
                    "deleted_sync_logs": deleted_logs,
                    "deleted_webhook_deliveries": deleted_deliveries,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )

        except Exception as e:
            logger.error("Cleanup failed", {"error": str(e)})

    async def retry_failed_webhooks(self):
        """Retry failed webhook deliveries."""
        try:
            failed_deliveries = (
                await self.integration_repo.get_failed_webhook_deliveries()
            )

            for delivery in failed_deliveries:
                if delivery.attempts < delivery.max_attempts:
                    integration = await self.get_integration(delivery.integration_id)
                    if integration and integration.status == IntegrationStatus.ACTIVE:
                        # Increment attempt count
                        await self.integration_repo.update_webhook_delivery(
                            delivery.id,
                            {
                                "attempts": delivery.attempts + 1,
                                "last_attempt": datetime.utcnow(),
                            },
                        )

                        # Get integration class and retry
                        integration_class = self._integration_classes.get(
                            IntegrationType(integration.integration_type)
                        )
                        if integration_class:
                            integration_instance = integration_class(integration)
                            asyncio.create_task(
                                self._process_webhook(
                                    integration_instance,
                                    delivery.id,
                                    delivery.event_type,
                                    delivery.payload,
                                )
                            )

        except Exception as e:
            logger.error("Failed to retry webhooks", {"error": str(e)})
