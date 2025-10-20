"""
Comprehensive Logging Service for Kinexus AI
Supports structured logging, metrics, and monitoring integration
"""

import logging
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from pythonjsonlogger import jsonlogger

from ..config import get_settings


class LogLevel(Enum):
    """Log levels with numeric values"""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogCategory(Enum):
    """Categories for log organization"""

    AGENT = "agent"
    API = "api"
    AUTH = "auth"
    DATABASE = "database"
    INTEGRATION = "integration"
    SECURITY = "security"
    PERFORMANCE = "performance"
    USER_ACTION = "user_action"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"


class MetricType(Enum):
    """Types of metrics to collect"""

    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"


class StructuredLogger:
    """Enhanced structured logger with context management and metrics"""

    def __init__(
        self,
        name: str,
        category: LogCategory = LogCategory.SYSTEM,
        extra_context: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.category = category
        self.settings = get_settings()

        # Initialize structured logger
        self.logger = structlog.get_logger(name)

        # Base context that's always included
        self.base_context = {
            "logger_name": name,
            "category": category.value,
            "environment": self.settings.ENVIRONMENT,
            "service": "kinexus-ai",
            **(extra_context or {}),
        }

        # Metrics registry
        self.metrics_registry = CollectorRegistry()
        self._setup_metrics()

        # Request/session tracking
        self._request_context = {}

    def _setup_metrics(self):
        """Setup Prometheus metrics for logging"""
        self.log_counter = Counter(
            "kinexus_log_entries_total",
            "Total number of log entries",
            ["level", "category", "logger_name"],
            registry=self.metrics_registry,
        )

        self.error_counter = Counter(
            "kinexus_errors_total",
            "Total number of errors",
            ["category", "error_type", "logger_name"],
            registry=self.metrics_registry,
        )

        self.operation_duration = Histogram(
            "kinexus_operation_duration_seconds",
            "Duration of operations",
            ["operation", "category", "status"],
            registry=self.metrics_registry,
        )

        self.active_operations = Gauge(
            "kinexus_active_operations",
            "Number of active operations",
            ["operation", "category"],
            registry=self.metrics_registry,
        )

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with optional exception details"""
        if error:
            kwargs.update(
                {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "traceback": traceback.format_exc(),
                }
            )
            self.error_counter.labels(
                category=self.category.value,
                error_type=type(error).__name__,
                logger_name=self.name,
            ).inc()

        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, **kwargs)

    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal logging method with context enrichment"""
        # Merge all context
        log_context = {
            **self.base_context,
            **self._request_context,
            **kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_level": level.name,
            "message": message,
        }

        # Update metrics
        self.log_counter.labels(
            level=level.name, category=self.category.value, logger_name=self.name
        ).inc()

        # Log using structlog
        log_method = getattr(self.logger, level.name.lower())
        log_method(message, **log_context)

    @contextmanager
    def operation_timer(self, operation_name: str, **extra_context):
        """Context manager for timing operations"""
        start_time = time.time()
        operation_id = str(uuid4())

        # Update active operations gauge
        self.active_operations.labels(
            operation=operation_name, category=self.category.value
        ).inc()

        try:
            self.info(
                f"Operation started: {operation_name}",
                operation_id=operation_id,
                operation=operation_name,
                **extra_context,
            )

            yield operation_id

            duration = time.time() - start_time
            self.operation_duration.labels(
                operation=operation_name, category=self.category.value, status="success"
            ).observe(duration)

            self.info(
                f"Operation completed: {operation_name}",
                operation_id=operation_id,
                operation=operation_name,
                duration_seconds=duration,
                status="success",
                **extra_context,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.operation_duration.labels(
                operation=operation_name, category=self.category.value, status="error"
            ).observe(duration)

            self.error(
                f"Operation failed: {operation_name}",
                error=e,
                operation_id=operation_id,
                operation=operation_name,
                duration_seconds=duration,
                status="error",
                **extra_context,
            )
            raise

        finally:
            # Decrement active operations gauge
            self.active_operations.labels(
                operation=operation_name, category=self.category.value
            ).dec()

    @contextmanager
    def request_context(
        self, request_id: str, user_id: Optional[str] = None, **extra_context
    ):
        """Context manager for request-scoped logging"""
        previous_context = self._request_context.copy()

        self._request_context.update(
            {"request_id": request_id, "user_id": user_id, **extra_context}
        )

        try:
            yield
        finally:
            self._request_context = previous_context

    def add_persistent_context(self, **context):
        """Add context that persists for all future log entries"""
        self.base_context.update(context)

    def remove_persistent_context(self, *keys):
        """Remove keys from persistent context"""
        for key in keys:
            self.base_context.pop(key, None)

    def get_metrics_registry(self):
        """Get the Prometheus metrics registry"""
        return self.metrics_registry


class AgentConversationLogger:
    """Specialized logger for tracking agent conversations and reasoning"""

    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.logger = StructuredLogger(
            name=f"agent-{agent_type}",
            category=LogCategory.AGENT,
            extra_context={"agent_id": agent_id, "agent_type": agent_type},
        )
        self.conversation_history: List[Dict[str, Any]] = []

    def log_reasoning_start(self, task: Dict[str, Any], reasoning_pattern: str):
        """Log the start of a reasoning process"""
        entry = {
            "event_type": "reasoning_start",
            "task_id": task.get("id"),
            "task_description": task.get("description"),
            "reasoning_pattern": reasoning_pattern,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.conversation_history.append(entry)
        self.logger.info(f"Agent reasoning started: {reasoning_pattern}", **entry)

    def log_thought(
        self,
        thought_id: str,
        thought_type: str,
        content: str,
        model_used: str,
        confidence: float,
        reasoning_chain_id: str,
        parent_thought_id: Optional[str] = None,
    ):
        """Log a single thought in the reasoning chain"""
        entry = {
            "event_type": "thought",
            "thought_id": thought_id,
            "thought_type": thought_type,
            "content": content,
            "model_used": model_used,
            "confidence": confidence,
            "reasoning_chain_id": reasoning_chain_id,
            "parent_thought_id": parent_thought_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.conversation_history.append(entry)
        self.logger.debug(f"Thought generated: {thought_type}", **entry)

    def log_model_interaction(
        self,
        model_name: str,
        prompt: str,
        response: str,
        tokens_used: int,
        response_time: float,
        cost: float = 0.0,
    ):
        """Log interaction with AI models"""
        entry = {
            "event_type": "model_interaction",
            "model_name": model_name,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "tokens_used": tokens_used,
            "response_time": response_time,
            "cost": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.conversation_history.append(entry)
        self.logger.info(f"Model interaction: {model_name}", **entry)

    def log_reasoning_complete(
        self,
        reasoning_chain_id: str,
        final_decision: str,
        confidence_score: float,
        total_duration: float,
        thoughts_count: int,
        models_used: List[str],
    ):
        """Log completion of reasoning process"""
        entry = {
            "event_type": "reasoning_complete",
            "reasoning_chain_id": reasoning_chain_id,
            "final_decision": final_decision,
            "confidence_score": confidence_score,
            "total_duration": total_duration,
            "thoughts_count": thoughts_count,
            "models_used": models_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.conversation_history.append(entry)
        self.logger.info("Agent reasoning completed", **entry)

    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log agent errors with full context"""
        entry = {
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.conversation_history.append(entry)
        self.logger.error("Agent error occurred", error=error, **entry)

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of the agent's conversation"""
        if not self.conversation_history:
            return {"agent_id": self.agent_id, "no_activity": True}

        # Analyze conversation
        event_counts = {}
        total_thoughts = 0
        total_model_interactions = 0
        total_cost = 0.0
        models_used = set()

        for entry in self.conversation_history:
            event_type = entry.get("event_type")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            if event_type == "thought":
                total_thoughts += 1
            elif event_type == "model_interaction":
                total_model_interactions += 1
                total_cost += entry.get("cost", 0.0)
                models_used.add(entry.get("model_name"))

        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "conversation_start": (
                self.conversation_history[0]["timestamp"]
                if self.conversation_history
                else None
            ),
            "conversation_end": (
                self.conversation_history[-1]["timestamp"]
                if self.conversation_history
                else None
            ),
            "total_events": len(self.conversation_history),
            "event_counts": event_counts,
            "total_thoughts": total_thoughts,
            "total_model_interactions": total_model_interactions,
            "total_cost": total_cost,
            "models_used": list(models_used),
        }

    def export_conversation(self) -> List[Dict[str, Any]]:
        """Export full conversation history"""
        return self.conversation_history.copy()


class PerformanceLogger:
    """Specialized logger for performance monitoring"""

    def __init__(self):
        self.logger = StructuredLogger(
            name="performance", category=LogCategory.PERFORMANCE
        )

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Log API request performance"""
        self.logger.info(
            f"API request: {method} {endpoint}",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_seconds=duration,
            user_id=user_id,
            request_size_bytes=request_size,
            response_size_bytes=response_size,
        )

    def log_database_query(
        self,
        query_type: str,
        table: str,
        duration: float,
        rows_affected: int = 0,
        query_hash: Optional[str] = None,
    ):
        """Log database query performance"""
        self.logger.info(
            f"Database query: {query_type} on {table}",
            query_type=query_type,
            table=table,
            duration_seconds=duration,
            rows_affected=rows_affected,
            query_hash=query_hash,
        )

    def log_model_inference(
        self,
        model_name: str,
        tokens_input: int,
        tokens_output: int,
        duration: float,
        cost: float = 0.0,
    ):
        """Log AI model inference performance"""
        self.logger.info(
            f"Model inference: {model_name}",
            model_name=model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            duration_seconds=duration,
            cost_dollars=cost,
            tokens_per_second=tokens_output / duration if duration > 0 else 0,
        )


class SecurityLogger:
    """Specialized logger for security events"""

    def __init__(self):
        self.logger = StructuredLogger(name="security", category=LogCategory.SECURITY)

    def log_authentication_attempt(
        self,
        user_email: str,
        success: bool,
        method: str,
        ip_address: str,
        user_agent: str,
    ):
        """Log authentication attempts"""
        self.logger.info(
            f"Authentication {'successful' if success else 'failed'}: {user_email}",
            user_email=user_email,
            success=success,
            auth_method=method,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_authorization_check(
        self,
        user_id: str,
        resource: str,
        action: str,
        allowed: bool,
        reason: Optional[str] = None,
    ):
        """Log authorization checks"""
        self.logger.info(
            f"Authorization {'granted' if allowed else 'denied'}: {user_id} -> {action} on {resource}",
            user_id=user_id,
            resource=resource,
            action=action,
            allowed=allowed,
            reason=reason,
        )

    def log_security_violation(
        self,
        violation_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: str = "medium",
    ):
        """Log security violations"""
        self.logger.warning(
            f"Security violation: {violation_type}",
            violation_type=violation_type,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
            severity=severity,
        )


class LoggingConfiguration:
    """Central configuration for logging system"""

    @staticmethod
    def setup_logging(log_level: str = "INFO", log_format: str = "json"):
        """Setup global logging configuration"""
        settings = get_settings()

        # Configure structlog
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        if log_format == "json":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure standard library logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=(
                "%(message)s"
                if log_format == "json"
                else "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
        )

        # Configure file logging if specified
        if hasattr(settings, "LOG_FILE_PATH") and settings.LOG_FILE_PATH:
            log_file = Path(settings.LOG_FILE_PATH)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            if log_format == "json":
                formatter = jsonlogger.JsonFormatter()
                file_handler.setFormatter(formatter)

            logging.getLogger().addHandler(file_handler)


# Global logger instances
system_logger = StructuredLogger("system", LogCategory.SYSTEM)
performance_logger = PerformanceLogger()
security_logger = SecurityLogger()

# Initialize logging
LoggingConfiguration.setup_logging()
