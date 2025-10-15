"""
Prometheus Metrics Service for Kinexus AI
Comprehensive monitoring and metrics collection
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

from prometheus_client import CollectorRegistry, Counter
from prometheus_client import Enum as PrometheusEnum
from prometheus_client import (
    Gauge,
    Histogram,
    Info,
    MetricsHandler,
    Summary,
    generate_latest,
    start_http_server,
)
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST

from ..config import get_settings
from .logging_service import LogCategory, StructuredLogger


class MetricCategory(Enum):
    """Categories for organizing metrics"""

    AGENT = "agent"
    API = "api"
    DATABASE = "database"
    INTEGRATION = "integration"
    BUSINESS = "business"
    SYSTEM = "system"
    SECURITY = "security"


@dataclass
class MetricDefinition:
    """Definition for a custom metric"""

    name: str
    description: str
    metric_type: str  # counter, histogram, gauge, summary
    labels: List[str]
    category: MetricCategory


class MetricsService:
    """Centralized metrics collection and management service"""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.settings = get_settings()
        self.logger = StructuredLogger("metrics", LogCategory.SYSTEM)

        self._metrics_server_started = False

        # In-memory rolling histories used for admin summaries
        self._lock = asyncio.Lock()
        self._retention_seconds = 3600  # keep one hour of history for snapshots
        self._request_history: Deque[Tuple[float, float, int]] = deque()
        self._error_history: Deque[Tuple[float, str, str]] = deque()
        self._agent_activity: Dict[str, Tuple[float, str]] = {}
        self._reasoning_history: Deque[Tuple[float, int]] = deque()
        self._model_usage_history: Deque[Tuple[float, str, float, int, int]] = deque()

        # Initialize core metrics
        self._initialize_core_metrics()
        self._initialize_agent_metrics()
        self._initialize_api_metrics()
        self._initialize_database_metrics()
        self._initialize_integration_metrics()
        self._initialize_business_metrics()

    def _initialize_core_metrics(self):
        """Initialize core system metrics"""
        # System info
        self.system_info = Info(
            "kinexus_system_info", "System information", registry=self.registry
        )
        self.system_info.info(
            {
                "version": "1.0.0",
                "environment": self.settings.ENVIRONMENT,
                "service": "kinexus-ai",
            }
        )

        # Application status
        self.app_status = PrometheusEnum(
            "kinexus_application_status",
            "Application status",
            states=["starting", "healthy", "degraded", "unhealthy"],
            registry=self.registry,
        )
        self.app_status.state("starting")

        # Component health
        self.component_health = Gauge(
            "kinexus_component_health",
            "Health status of components (1=healthy, 0=unhealthy)",
            ["component", "category"],
            registry=self.registry,
        )

        # Request/response metrics
        self.requests_total = Counter(
            "kinexus_requests_total",
            "Total number of requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            "kinexus_request_duration_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        # Error tracking
        self.errors_total = Counter(
            "kinexus_errors_total",
            "Total number of errors",
            ["category", "error_type", "severity"],
            registry=self.registry,
        )

    def _initialize_agent_metrics(self):
        """Initialize AI agent metrics"""
        # Agent performance
        self.agent_reasoning_duration = Histogram(
            "kinexus_agent_reasoning_duration_seconds",
            "Time spent on reasoning processes",
            ["agent_type", "reasoning_pattern"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
            registry=self.registry,
        )

        self.agent_confidence_scores = Histogram(
            "kinexus_agent_confidence_scores",
            "Distribution of agent confidence scores",
            ["agent_type"],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry,
        )

        self.agent_thoughts_per_reasoning = Histogram(
            "kinexus_agent_thoughts_per_reasoning",
            "Number of thoughts per reasoning chain",
            ["agent_type", "reasoning_pattern"],
            buckets=(1, 2, 3, 5, 8, 13, 21, 34),
            registry=self.registry,
        )

        self.agent_model_usage = Counter(
            "kinexus_agent_model_usage_total",
            "Total model API calls by agents",
            ["agent_type", "model_provider", "model_type"],
            registry=self.registry,
        )

        self.agent_model_tokens = Counter(
            "kinexus_agent_model_tokens_total",
            "Total tokens used by agents",
            ["agent_type", "model_provider", "model_type", "token_type"],
            registry=self.registry,
        )

        self.agent_model_cost = Counter(
            "kinexus_agent_model_cost_dollars_total",
            "Total cost of model usage",
            ["agent_type", "model_provider", "model_type"],
            registry=self.registry,
        )

        self.active_reasoning_chains = Gauge(
            "kinexus_active_reasoning_chains",
            "Number of active reasoning chains",
            ["agent_type"],
            registry=self.registry,
        )

        # Agent success rates
        self.agent_task_success_rate = Gauge(
            "kinexus_agent_task_success_rate",
            "Success rate of agent tasks (0-1)",
            ["agent_type"],
            registry=self.registry,
        )

    def _initialize_api_metrics(self):
        """Initialize API-specific metrics"""
        # Authentication metrics
        self.auth_attempts = Counter(
            "kinexus_auth_attempts_total",
            "Total authentication attempts",
            ["method", "status"],
            registry=self.registry,
        )

        # WebSocket connections
        self.websocket_connections = Gauge(
            "kinexus_websocket_connections_active",
            "Number of active WebSocket connections",
            ["user_role"],
            registry=self.registry,
        )

        self.websocket_messages = Counter(
            "kinexus_websocket_messages_total",
            "Total WebSocket messages",
            ["message_type", "direction"],
            registry=self.registry,
        )

        # File operations
        self.file_operations = Counter(
            "kinexus_file_operations_total",
            "Total file operations",
            ["operation", "file_type", "status"],
            registry=self.registry,
        )

        self.file_sizes = Histogram(
            "kinexus_file_sizes_bytes",
            "Distribution of file sizes",
            ["file_type", "operation"],
            buckets=(1024, 10240, 102400, 1048576, 10485760, 104857600),  # 1KB to 100MB
            registry=self.registry,
        )

    def _initialize_database_metrics(self):
        """Initialize database metrics"""
        # Query performance
        self.db_query_duration = Histogram(
            "kinexus_db_query_duration_seconds",
            "Database query duration",
            ["query_type", "table"],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry,
        )

        self.db_connections = Gauge(
            "kinexus_db_connections_active",
            "Number of active database connections",
            ["database", "pool"],
            registry=self.registry,
        )

        self.db_operations = Counter(
            "kinexus_db_operations_total",
            "Total database operations",
            ["operation", "table", "status"],
            registry=self.registry,
        )

        # Migration tracking
        self.db_migrations = Gauge(
            "kinexus_db_migration_version",
            "Current database migration version",
            registry=self.registry,
        )

    def _initialize_integration_metrics(self):
        """Initialize integration metrics"""
        # External API calls
        self.external_api_calls = Counter(
            "kinexus_external_api_calls_total",
            "Total external API calls",
            ["service", "endpoint", "status"],
            registry=self.registry,
        )

        self.external_api_duration = Histogram(
            "kinexus_external_api_duration_seconds",
            "External API call duration",
            ["service", "endpoint"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry,
        )

        # Webhook processing
        self.webhook_events = Counter(
            "kinexus_webhook_events_total",
            "Total webhook events received",
            ["source", "event_type", "status"],
            registry=self.registry,
        )

        self.webhook_processing_duration = Histogram(
            "kinexus_webhook_processing_duration_seconds",
            "Webhook processing duration",
            ["source", "event_type"],
            registry=self.registry,
        )

        # Integration health
        self.integration_health = Gauge(
            "kinexus_integration_health",
            "Health status of integrations (1=healthy, 0=unhealthy)",
            ["integration", "type"],
            registry=self.registry,
        )

    def _initialize_business_metrics(self):
        """Initialize business-specific metrics"""
        # Document metrics
        self.documents_total = Gauge(
            "kinexus_documents_total",
            "Total number of documents",
            ["document_type", "status"],
            registry=self.registry,
        )

        self.documents_analyzed = Counter(
            "kinexus_documents_analyzed_total",
            "Total documents analyzed",
            ["document_type", "source"],
            registry=self.registry,
        )

        # Review metrics
        self.reviews_total = Gauge(
            "kinexus_reviews_total",
            "Total number of reviews",
            ["status", "workflow_type"],
            registry=self.registry,
        )

        self.review_processing_time = Histogram(
            "kinexus_review_processing_time_seconds",
            "Time from review creation to completion",
            ["workflow_type", "status"],
            buckets=(300, 1800, 3600, 7200, 86400, 259200, 604800),  # 5m to 1 week
            registry=self.registry,
        )

        self.auto_approval_rate = Gauge(
            "kinexus_auto_approval_rate",
            "Rate of automatic approvals (0-1)",
            ["document_type"],
            registry=self.registry,
        )

        # Change detection
        self.changes_detected = Counter(
            "kinexus_changes_detected_total",
            "Total changes detected",
            ["source", "change_type"],
            registry=self.registry,
        )

        self.change_impact_scores = Histogram(
            "kinexus_change_impact_scores",
            "Distribution of change impact scores",
            ["source", "change_type"],
            buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
            registry=self.registry,
        )

    # Recording methods for different metric types

    async def record_request(
        self, method: str, endpoint: str, status: int, duration: float
    ):
        """Record API request metrics"""
        self.requests_total.labels(
            method=method, endpoint=endpoint, status=str(status)
        ).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)

        timestamp = time.time()
        async with self._lock:
            self._request_history.append((timestamp, duration, status))
            self._trim_history(self._request_history, timestamp)

    async def record_error(
        self, category: str, error_type: str, severity: str = "error"
    ):
        """Record error metrics"""
        self.errors_total.labels(
            category=category, error_type=error_type, severity=severity
        ).inc()

        timestamp = time.time()
        async with self._lock:
            self._error_history.append((timestamp, category, severity))
            self._trim_history(self._error_history, timestamp)

    async def record_agent_performance(
        self,
        agent_id: str,
        agent_type: str = "unknown",
        reasoning_time: float = 0.0,
        confidence_score: float = 0.0,
        thoughts_count: int = 0,
        models_used: int = 0,
        success: bool = True,
        reasoning_pattern: str = "unknown",
    ):
        """Record agent performance metrics"""
        self.agent_reasoning_duration.labels(
            agent_type=agent_type, reasoning_pattern=reasoning_pattern
        ).observe(reasoning_time)

        self.agent_confidence_scores.labels(agent_type=agent_type).observe(
            confidence_score
        )

        self.agent_thoughts_per_reasoning.labels(
            agent_type=agent_type, reasoning_pattern=reasoning_pattern
        ).observe(thoughts_count)

        # Update success rate (this would need to be calculated over time)
        # For now, just track individual successes
        if success:
            self.logger.debug(
                f"Agent {agent_id} task successful", agent_type=agent_type
            )

        timestamp = time.time()
        async with self._lock:
            self._agent_activity[agent_id] = (timestamp, agent_type)
            self._reasoning_history.append((timestamp, thoughts_count))
            self._trim_history(self._reasoning_history, timestamp)
            self._trim_agent_activity(timestamp)

    async def record_model_usage(
        self,
        agent_type: str,
        model_provider: str,
        model_type: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ):
        """Record AI model usage metrics"""
        self.agent_model_usage.labels(
            agent_type=agent_type, model_provider=model_provider, model_type=model_type
        ).inc()

        self.agent_model_tokens.labels(
            agent_type=agent_type,
            model_provider=model_provider,
            model_type=model_type,
            token_type="input",
        ).inc(input_tokens)

        self.agent_model_tokens.labels(
            agent_type=agent_type,
            model_provider=model_provider,
            model_type=model_type,
            token_type="output",
        ).inc(output_tokens)

        self.agent_model_cost.labels(
            agent_type=agent_type, model_provider=model_provider, model_type=model_type
        ).inc(cost)

        timestamp = time.time()
        async with self._lock:
            self._model_usage_history.append(
                (timestamp, agent_type, cost, input_tokens, output_tokens)
            )
            self._trim_history(self._model_usage_history, timestamp)

    async def record_database_operation(
        self, operation: str, table: str, duration: float, status: str = "success"
    ):
        """Record database operation metrics"""
        self.db_query_duration.labels(query_type=operation, table=table).observe(
            duration
        )
        self.db_operations.labels(operation=operation, table=table, status=status).inc()

    async def record_external_api_call(
        self, service: str, endpoint: str, duration: float, status: int
    ):
        """Record external API call metrics"""
        self.external_api_calls.labels(
            service=service, endpoint=endpoint, status=str(status)
        ).inc()

        self.external_api_duration.labels(service=service, endpoint=endpoint).observe(
            duration
        )

    async def record_webhook_event(
        self,
        source: str,
        event_type: str,
        processing_duration: float,
        status: str = "success",
    ):
        """Record webhook event metrics"""
        self.webhook_events.labels(
            source=source, event_type=event_type, status=status
        ).inc()

        self.webhook_processing_duration.labels(
            source=source, event_type=event_type
        ).observe(processing_duration)

    async def record_document_analysis(self, document_type: str, source: str):
        """Record document analysis metrics"""
        self.documents_analyzed.labels(document_type=document_type, source=source).inc()

    async def record_change_detection(
        self, source: str, change_type: str, impact_score: float
    ):
        """Record change detection metrics"""
        self.changes_detected.labels(source=source, change_type=change_type).inc()
        self.change_impact_scores.labels(
            source=source, change_type=change_type
        ).observe(impact_score)

    # Status update methods

    def set_application_status(self, status: str):
        """Set application status"""
        self.app_status.state(status)

    def set_component_health(self, component: str, category: str, healthy: bool):
        """Set component health status"""
        self.component_health.labels(component=component, category=category).set(
            1 if healthy else 0
        )

    def set_integration_health(
        self, integration: str, integration_type: str, healthy: bool
    ):
        """Set integration health status"""
        self.integration_health.labels(
            integration=integration, type=integration_type
        ).set(1 if healthy else 0)

    def update_active_connections(self, websocket_count: int, db_connections: int):
        """Update active connection counts"""
        # This would typically be called periodically
        self.websocket_connections.labels(user_role="all").set(websocket_count)
        self.db_connections.labels(database="postgres", pool="main").set(db_connections)

    def update_document_counts(self, document_counts: Dict[str, Dict[str, int]]):
        """Update document count metrics"""
        for doc_type, status_counts in document_counts.items():
            for status, count in status_counts.items():
                self.documents_total.labels(document_type=doc_type, status=status).set(
                    count
                )

    def update_review_counts(self, review_counts: Dict[str, Dict[str, int]]):
        """Update review count metrics"""
        for workflow_type, status_counts in review_counts.items():
            for status, count in status_counts.items():
                self.reviews_total.labels(
                    status=status, workflow_type=workflow_type
                ).set(count)

    # Utility methods

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        return generate_latest(self.registry)

    def get_registry(self) -> CollectorRegistry:
        """Get the metrics registry"""
        return self.registry

    async def start_metrics_server(self, port: int = 8090):
        """Start Prometheus metrics HTTP server"""
        if self._metrics_server_started:
            return

        try:
            start_http_server(port, registry=self.registry)
            self.logger.info(f"Metrics server started on port {port}")
            self.set_component_health("metrics_server", "monitoring", True)
            self._metrics_server_started = True
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}")
            self.set_component_health("metrics_server", "monitoring", False)
            self._metrics_server_started = False
            raise

    def create_custom_metric(self, definition: MetricDefinition):
        """Create a custom metric based on definition"""
        if definition.metric_type == "counter":
            return Counter(
                definition.name,
                definition.description,
                definition.labels,
                registry=self.registry,
            )
        elif definition.metric_type == "histogram":
            return Histogram(
                definition.name,
                definition.description,
                definition.labels,
                registry=self.registry,
            )
        elif definition.metric_type == "gauge":
            return Gauge(
                definition.name,
                definition.description,
                definition.labels,
                registry=self.registry,
            )
        elif definition.metric_type == "summary":
            return Summary(
                definition.name,
                definition.description,
                definition.labels,
                registry=self.registry,
            )
        else:
            raise ValueError(f"Unsupported metric type: {definition.metric_type}")

    # Snapshot helper methods used by the admin API

    async def get_active_agent_count(
        self, start_time: datetime, end_time: datetime
    ) -> int:
        """Return number of agents that reported activity within the window."""
        if end_time <= start_time:
            return 0
        start_ts, _ = self._coerce_timestamps(start_time, end_time)
        async with self._lock:
            self._trim_agent_activity(time.time())
            return sum(1 for ts, _ in self._agent_activity.values() if ts >= start_ts)

    async def get_active_reasoning_chains(
        self, start_time: datetime, end_time: datetime
    ) -> int:
        """Return total reasoning chains observed in the window."""
        if end_time <= start_time:
            return 0
        start_ts, end_ts = self._coerce_timestamps(start_time, end_time)
        async with self._lock:
            self._trim_history(self._reasoning_history, time.time())
            return sum(
                thoughts
                for ts, thoughts in self._reasoning_history
                if start_ts <= ts <= end_ts and thoughts > 0
            )

    async def get_request_rate(self, start_time: datetime, end_time: datetime) -> float:
        """Requests per second over the window."""
        interval = (end_time - start_time).total_seconds()
        if interval <= 0:
            return 0.0
        start_ts, end_ts = self._coerce_timestamps(start_time, end_time)
        async with self._lock:
            self._trim_history(self._request_history, time.time())
            count = sum(
                1 for ts, _, _ in self._request_history if start_ts <= ts <= end_ts
            )
        return count / interval if count > 0 else 0.0

    async def get_error_rate(self, start_time: datetime, end_time: datetime) -> float:
        """Error percentage over the window."""
        interval = (end_time - start_time).total_seconds()
        if interval <= 0:
            return 0.0
        start_ts, end_ts = self._coerce_timestamps(start_time, end_time)
        async with self._lock:
            self._trim_history(self._request_history, time.time())
            self._trim_history(self._error_history, time.time())
            total_requests = sum(
                1 for ts, _, _ in self._request_history if start_ts <= ts <= end_ts
            )
            total_errors = sum(
                1 for ts, _, _ in self._error_history if start_ts <= ts <= end_ts
            )
        if total_requests == 0:
            return 0.0
        return total_errors / total_requests

    async def get_avg_response_time(
        self, start_time: datetime, end_time: datetime
    ) -> float:
        """Average response time in seconds over the window."""
        start_ts, end_ts = self._coerce_timestamps(start_time, end_time)
        async with self._lock:
            self._trim_history(self._request_history, time.time())
            durations = [
                duration
                for ts, duration, _ in self._request_history
                if start_ts <= ts <= end_ts
            ]
        if not durations:
            return 0.0
        return sum(durations) / len(durations)

    async def get_total_cost(self, start_time: datetime, end_time: datetime) -> float:
        """Sum of AI model costs over the window."""
        start_ts, end_ts = self._coerce_timestamps(start_time, end_time)
        async with self._lock:
            self._trim_history(self._model_usage_history, time.time())
            return sum(
                cost
                for ts, _, cost, _, _ in self._model_usage_history
                if start_ts <= ts <= end_ts
            )

    async def get_tokens_processed(
        self, start_time: datetime, end_time: datetime
    ) -> int:
        """Total tokens (input + output) processed over the window."""
        start_ts, end_ts = self._coerce_timestamps(start_time, end_time)
        async with self._lock:
            self._trim_history(self._model_usage_history, time.time())
            return sum(
                (input_tokens + output_tokens)
                for ts, _, _, input_tokens, output_tokens in self._model_usage_history
                if start_ts <= ts <= end_ts
            )

    # Internal helpers

    def _trim_history(self, history: Deque[Tuple], current_ts: float):
        """Trim entries older than retention window from a deque."""
        cutoff = current_ts - self._retention_seconds
        while history and history[0][0] < cutoff:
            history.popleft()

    def _trim_agent_activity(self, current_ts: float):
        """Remove stale agent activity records."""
        cutoff = current_ts - self._retention_seconds
        stale_agents = [
            agent_id
            for agent_id, (ts, _) in self._agent_activity.items()
            if ts < cutoff
        ]
        for agent_id in stale_agents:
            del self._agent_activity[agent_id]

    def _coerce_timestamps(
        self, start_time: datetime, end_time: datetime
    ) -> tuple[float, float]:
        """Convert datetimes (naive or aware) into epoch seconds assuming UTC when naive."""

        def _to_epoch(dt: datetime) -> float:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc).timestamp()
            return dt.timestamp()

        start_ts = _to_epoch(start_time)
        end_ts = _to_epoch(end_time)
        return start_ts, end_ts


# Global metrics service instance
metrics_service = MetricsService()
