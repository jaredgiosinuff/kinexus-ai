import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session, sessionmaker

from ..database import get_database_session
from ..models.integrations import (
    Integration,
    IntegrationStatus,
    IntegrationSyncLog,
    IntegrationType,
    WebhookDelivery,
)
from ..services.logging_service import StructuredLogger

logger = StructuredLogger("repository.integration")


class IntegrationRepository:
    """Repository for managing integration data."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_database_session()

    async def create_integration(
        self,
        name: str,
        integration_type: str,
        config: Dict[str, Any],
        auth_type: str,
        auth_config: Dict[str, Any],
        created_by: Optional[str] = None,
    ) -> Integration:
        """Create a new integration."""
        try:
            integration = Integration(
                id=str(uuid.uuid4()),
                name=name,
                integration_type=integration_type,
                config=config,
                auth_type=auth_type,
                auth_config=auth_config,
                status=IntegrationStatus.INACTIVE,
                created_by=created_by,
                created_at=datetime.utcnow(),
            )

            self.db.add(integration)
            self.db.commit()
            self.db.refresh(integration)

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
            self.db.rollback()
            logger.error(
                "Failed to create integration",
                {"name": name, "type": integration_type, "error": str(e)},
            )
            raise

    async def get_by_id(self, integration_id: str) -> Optional[Integration]:
        """Get an integration by ID."""
        try:
            integration = (
                self.db.query(Integration)
                .filter(Integration.id == integration_id)
                .first()
            )

            if integration:
                logger.debug(
                    "Integration retrieved", {"integration_id": integration_id}
                )

            return integration

        except Exception as e:
            logger.error(
                "Failed to get integration",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def get_all(self, status_filter: Optional[str] = None) -> List[Integration]:
        """Get all integrations with optional status filter."""
        try:
            query = self.db.query(Integration)

            if status_filter:
                query = query.filter(Integration.status == status_filter)

            integrations = query.order_by(desc(Integration.created_at)).all()

            logger.debug(
                "Integrations retrieved",
                {"count": len(integrations), "status_filter": status_filter},
            )

            return integrations

        except Exception as e:
            logger.error("Failed to get all integrations", {"error": str(e)})
            raise

    async def get_active_integrations(self) -> List[Integration]:
        """Get all active integrations."""
        return await self.get_all(IntegrationStatus.ACTIVE)

    async def update_integration(
        self, integration_id: str, update_data: Dict[str, Any]
    ) -> Optional[Integration]:
        """Update an integration."""
        try:
            integration = await self.get_by_id(integration_id)
            if not integration:
                return None

            # Update fields
            for field, value in update_data.items():
                if hasattr(integration, field):
                    setattr(integration, field, value)

            integration.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(integration)

            logger.info(
                "Integration updated",
                {
                    "integration_id": integration_id,
                    "updated_fields": list(update_data.keys()),
                },
            )

            return integration

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to update integration",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def delete_integration(self, integration_id: str) -> bool:
        """Delete an integration."""
        try:
            integration = await self.get_by_id(integration_id)
            if not integration:
                return False

            self.db.delete(integration)
            self.db.commit()

            logger.info("Integration deleted", {"integration_id": integration_id})
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to delete integration",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def create_sync_log(
        self,
        integration_id: str,
        sync_type: str,
        direction: str,
        status: str = "started",
    ) -> IntegrationSyncLog:
        """Create a new sync log."""
        try:
            sync_log = IntegrationSyncLog(
                id=str(uuid.uuid4()),
                integration_id=integration_id,
                sync_type=sync_type,
                direction=direction,
                status=status,
                started_at=datetime.utcnow(),
            )

            self.db.add(sync_log)
            self.db.commit()
            self.db.refresh(sync_log)

            logger.debug(
                "Sync log created",
                {
                    "sync_log_id": sync_log.id,
                    "integration_id": integration_id,
                    "sync_type": sync_type,
                },
            )

            return sync_log

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to create sync log",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def update_sync_log(
        self, sync_log_id: str, update_data: Dict[str, Any]
    ) -> Optional[IntegrationSyncLog]:
        """Update a sync log."""
        try:
            sync_log = (
                self.db.query(IntegrationSyncLog)
                .filter(IntegrationSyncLog.id == sync_log_id)
                .first()
            )

            if not sync_log:
                return None

            # Update fields
            for field, value in update_data.items():
                if hasattr(sync_log, field):
                    setattr(sync_log, field, value)

            self.db.commit()
            self.db.refresh(sync_log)

            logger.debug(
                "Sync log updated",
                {"sync_log_id": sync_log_id, "status": sync_log.status},
            )

            return sync_log

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to update sync log",
                {"sync_log_id": sync_log_id, "error": str(e)},
            )
            raise

    async def get_sync_logs(
        self, integration_id: str, limit: int = 50, status_filter: Optional[str] = None
    ) -> List[IntegrationSyncLog]:
        """Get sync logs for an integration."""
        try:
            query = self.db.query(IntegrationSyncLog).filter(
                IntegrationSyncLog.integration_id == integration_id
            )

            if status_filter:
                query = query.filter(IntegrationSyncLog.status == status_filter)

            sync_logs = (
                query.order_by(desc(IntegrationSyncLog.started_at)).limit(limit).all()
            )

            logger.debug(
                "Sync logs retrieved",
                {
                    "integration_id": integration_id,
                    "count": len(sync_logs),
                    "status_filter": status_filter,
                },
            )

            return sync_logs

        except Exception as e:
            logger.error(
                "Failed to get sync logs",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def create_webhook_delivery(
        self,
        integration_id: str,
        event_type: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> WebhookDelivery:
        """Create a new webhook delivery record."""
        try:
            delivery = WebhookDelivery(
                id=str(uuid.uuid4()),
                integration_id=integration_id,
                event_type=event_type,
                payload=payload,
                headers=headers,
                status="pending",
                created_at=datetime.utcnow(),
            )

            self.db.add(delivery)
            self.db.commit()
            self.db.refresh(delivery)

            logger.debug(
                "Webhook delivery created",
                {
                    "delivery_id": delivery.id,
                    "integration_id": integration_id,
                    "event_type": event_type,
                },
            )

            return delivery

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to create webhook delivery",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def update_webhook_delivery(
        self, delivery_id: str, update_data: Dict[str, Any]
    ) -> Optional[WebhookDelivery]:
        """Update a webhook delivery."""
        try:
            delivery = (
                self.db.query(WebhookDelivery)
                .filter(WebhookDelivery.id == delivery_id)
                .first()
            )

            if not delivery:
                return None

            # Update fields
            for field, value in update_data.items():
                if hasattr(delivery, field):
                    setattr(delivery, field, value)

            self.db.commit()
            self.db.refresh(delivery)

            logger.debug(
                "Webhook delivery updated",
                {"delivery_id": delivery_id, "status": delivery.status},
            )

            return delivery

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to update webhook delivery",
                {"delivery_id": delivery_id, "error": str(e)},
            )
            raise

    async def get_failed_webhook_deliveries(
        self, max_age_hours: int = 24
    ) -> List[WebhookDelivery]:
        """Get failed webhook deliveries for retry."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

            deliveries = (
                self.db.query(WebhookDelivery)
                .filter(
                    and_(
                        WebhookDelivery.status == "failed",
                        WebhookDelivery.attempts < WebhookDelivery.max_attempts,
                        WebhookDelivery.created_at >= cutoff_time,
                        or_(
                            WebhookDelivery.next_retry.is_(None),
                            WebhookDelivery.next_retry <= datetime.utcnow(),
                        ),
                    )
                )
                .all()
            )

            return deliveries

        except Exception as e:
            logger.error("Failed to get failed webhook deliveries", {"error": str(e)})
            raise

    async def get_integration_stats(
        self, integration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics for integrations."""
        try:
            stats = {}

            # Base query
            base_query = self.db.query(Integration)
            if integration_id:
                base_query = base_query.filter(Integration.id == integration_id)

            # Basic counts
            stats["total_integrations"] = base_query.count()
            stats["active_integrations"] = base_query.filter(
                Integration.status == IntegrationStatus.ACTIVE
            ).count()
            stats["failed_integrations"] = base_query.filter(
                Integration.status == IntegrationStatus.ERROR
            ).count()

            # Sync statistics for today
            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            sync_query = self.db.query(IntegrationSyncLog).filter(
                IntegrationSyncLog.started_at >= today_start
            )
            if integration_id:
                sync_query = sync_query.filter(
                    IntegrationSyncLog.integration_id == integration_id
                )

            stats["total_syncs_today"] = sync_query.count()
            stats["successful_syncs_today"] = sync_query.filter(
                IntegrationSyncLog.status == "success"
            ).count()
            stats["failed_syncs_today"] = sync_query.filter(
                IntegrationSyncLog.status == "failure"
            ).count()

            # Average sync duration
            avg_duration = self.db.query(
                func.avg(IntegrationSyncLog.duration_seconds)
            ).filter(
                and_(
                    IntegrationSyncLog.started_at >= today_start,
                    IntegrationSyncLog.status == "success",
                    IntegrationSyncLog.duration_seconds.isnot(None),
                )
            )
            if integration_id:
                avg_duration = avg_duration.filter(
                    IntegrationSyncLog.integration_id == integration_id
                )

            stats["avg_sync_duration"] = float(avg_duration.scalar() or 0)

            # Data processed today
            data_processed = self.db.query(
                func.sum(IntegrationSyncLog.records_processed)
            ).filter(IntegrationSyncLog.started_at >= today_start)
            if integration_id:
                data_processed = data_processed.filter(
                    IntegrationSyncLog.integration_id == integration_id
                )

            stats["data_processed_today"] = int(data_processed.scalar() or 0)

            logger.debug(
                "Integration stats calculated",
                {"integration_id": integration_id, "stats": stats},
            )

            return stats

        except Exception as e:
            logger.error(
                "Failed to get integration stats",
                {"integration_id": integration_id, "error": str(e)},
            )
            raise

    async def cleanup_old_sync_logs(self, cutoff_date: datetime) -> int:
        """Clean up old sync logs."""
        try:
            deleted_count = (
                self.db.query(IntegrationSyncLog)
                .filter(IntegrationSyncLog.started_at < cutoff_date)
                .delete()
            )

            self.db.commit()

            logger.info(
                "Old sync logs cleaned up",
                {
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )

            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to cleanup sync logs", {"error": str(e)})
            raise

    async def cleanup_old_webhook_deliveries(self, cutoff_date: datetime) -> int:
        """Clean up old webhook deliveries."""
        try:
            deleted_count = (
                self.db.query(WebhookDelivery)
                .filter(WebhookDelivery.created_at < cutoff_date)
                .delete()
            )

            self.db.commit()

            logger.info(
                "Old webhook deliveries cleaned up",
                {
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                },
            )

            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to cleanup webhook deliveries", {"error": str(e)})
            raise

    async def get_integrations_by_type(
        self, integration_type: str
    ) -> List[Integration]:
        """Get all integrations of a specific type."""
        try:
            integrations = (
                self.db.query(Integration)
                .filter(Integration.integration_type == integration_type)
                .order_by(desc(Integration.created_at))
                .all()
            )

            return integrations

        except Exception as e:
            logger.error(
                "Failed to get integrations by type",
                {"integration_type": integration_type, "error": str(e)},
            )
            raise

    async def search_integrations(
        self,
        query: str,
        integration_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Integration]:
        """Search integrations by name or description."""
        try:
            search_query = self.db.query(Integration)

            # Text search
            if query:
                search_term = f"%{query}%"
                search_query = search_query.filter(
                    or_(
                        Integration.name.ilike(search_term),
                        Integration.description.ilike(search_term),
                    )
                )

            # Type filter
            if integration_type:
                search_query = search_query.filter(
                    Integration.integration_type == integration_type
                )

            # Status filter
            if status:
                search_query = search_query.filter(Integration.status == status)

            integrations = (
                search_query.order_by(desc(Integration.created_at)).limit(limit).all()
            )

            logger.debug(
                "Integration search completed",
                {
                    "query": query,
                    "type": integration_type,
                    "status": status,
                    "results": len(integrations),
                },
            )

            return integrations

        except Exception as e:
            logger.error("Integration search failed", {"query": query, "error": str(e)})
            raise
