import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from ...core.models.auth import AuthConfig, AuthProvider, User
from ...core.models.conversations import AgentConversation
from ...core.models.integrations import Integration, IntegrationConfig
from ...core.repositories.conversation_repository import ConversationRepository
from ...core.services.auth_service import AuthService
from ...core.services.integration_service import IntegrationService
from ...core.services.logging_service import StructuredLogger
from ...core.services.metrics_service import MetricsService

logger = StructuredLogger("api.admin")
router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBearer()


# Pydantic models for request/response
class SystemMetrics(BaseModel):
    active_agents: int
    reasoning_chains: int
    request_rate: float
    error_rate: float
    response_time: float
    total_cost: float
    tokens_processed: int


class AgentConversationResponse(BaseModel):
    id: str
    agent_type: str
    task: str
    status: str
    start_time: datetime
    duration: Optional[float]
    thoughts: int
    confidence: float
    model_used: str
    cost: float
    reasoning_pattern: str
    tokens_used: int


class IntegrationResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    last_sync: datetime
    config: Dict[str, Any]
    error_message: Optional[str]


class AuthConfigRequest(BaseModel):
    type: str  # 'cognito' or 'local'
    enabled: bool
    config: Dict[str, Any]


class IntegrationToggleRequest(BaseModel):
    enabled: bool


class IntegrationCreateRequest(BaseModel):
    name: str
    type: str
    integration_type: str
    config: Dict[str, Any]


# Dependency to verify admin access
async def verify_admin_access(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Verify that the user has admin access."""
    try:
        auth_service = AuthService()
        user = await auth_service.verify_token(credentials.credentials)

        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
            )

        return user
    except Exception as e:
        logger.error("Admin auth verification failed", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


@router.get("/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    admin_user: User = Depends(verify_admin_access),
) -> SystemMetrics:
    """Get current system metrics and performance data."""
    try:
        metrics_service = MetricsService()

        # Get metrics from the last hour
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        # Gather metrics from Prometheus
        active_agents = await metrics_service.get_active_agent_count()
        reasoning_chains = await metrics_service.get_active_reasoning_chains()
        request_rate = await metrics_service.get_request_rate(start_time, end_time)
        error_rate = await metrics_service.get_error_rate(start_time, end_time)
        response_time = await metrics_service.get_avg_response_time(
            start_time, end_time
        )
        total_cost = await metrics_service.get_total_cost(start_time, end_time)
        tokens_processed = await metrics_service.get_tokens_processed(
            start_time, end_time
        )

        logger.info(
            "System metrics retrieved",
            {
                "admin_user": admin_user.email,
                "active_agents": active_agents,
                "reasoning_chains": reasoning_chains,
            },
        )

        return SystemMetrics(
            active_agents=active_agents,
            reasoning_chains=reasoning_chains,
            request_rate=request_rate,
            error_rate=error_rate,
            response_time=response_time,
            total_cost=total_cost,
            tokens_processed=tokens_processed,
        )

    except Exception as e:
        logger.error("Failed to get system metrics", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics",
        )


@router.get("/conversations", response_model=List[AgentConversationResponse])
async def get_agent_conversations(
    limit: int = 100,
    status_filter: Optional[str] = None,
    admin_user: User = Depends(verify_admin_access),
) -> List[AgentConversationResponse]:
    """Get recent agent conversations with filtering options."""
    try:
        conversation_repo = ConversationRepository()

        conversations = await conversation_repo.get_recent_conversations(
            limit=limit, status_filter=status_filter
        )

        response_data = []
        for conv in conversations:
            response_data.append(
                AgentConversationResponse(
                    id=conv.id,
                    agent_type=conv.agent_type,
                    task=conv.task_description,
                    status=conv.status,
                    start_time=conv.created_at,
                    duration=conv.duration_seconds,
                    thoughts=len(conv.reasoning_steps),
                    confidence=conv.confidence_score,
                    model_used=conv.model_used,
                    cost=conv.total_cost,
                    reasoning_pattern=conv.reasoning_pattern,
                    tokens_used=conv.tokens_used,
                )
            )

        logger.info(
            "Agent conversations retrieved",
            {
                "admin_user": admin_user.email,
                "conversation_count": len(response_data),
                "status_filter": status_filter,
            },
        )

        return response_data

    except Exception as e:
        logger.error("Failed to get agent conversations", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent conversations",
        )


@router.get("/conversations/{conversation_id}")
async def get_conversation_details(
    conversation_id: str, admin_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """Get detailed information about a specific conversation."""
    try:
        conversation_repo = ConversationRepository()
        conversation = await conversation_repo.get_by_id(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

        # Get detailed reasoning steps and thoughts
        detailed_data = {
            "conversation": conversation,
            "reasoning_steps": conversation.reasoning_steps,
            "model_calls": conversation.model_calls,
            "performance_metrics": conversation.performance_metrics,
        }

        logger.info(
            "Conversation details retrieved",
            {"admin_user": admin_user.email, "conversation_id": conversation_id},
        )

        return detailed_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get conversation details",
            {"conversation_id": conversation_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation details",
        )


@router.get("/auth/config")
async def get_auth_config(
    admin_user: User = Depends(verify_admin_access),
) -> Dict[str, Any]:
    """Get current authentication configuration."""
    try:
        auth_service = AuthService()
        config = await auth_service.get_current_config()

        logger.info("Auth config retrieved", {"admin_user": admin_user.email})

        return {
            "type": config.provider_type,
            "enabled": config.enabled,
            "config": config.config,
        }

    except Exception as e:
        logger.error("Failed to get auth config", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authentication configuration",
        )


@router.put("/auth/config")
async def update_auth_config(
    config_request: AuthConfigRequest, admin_user: User = Depends(verify_admin_access)
) -> Dict[str, str]:
    """Update authentication configuration."""
    try:
        auth_service = AuthService()

        # Validate the configuration
        if config_request.type not in ["cognito", "local"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid authentication type",
            )

        # Update the configuration
        await auth_service.update_config(
            provider_type=config_request.type,
            enabled=config_request.enabled,
            config=config_request.config,
        )

        logger.info(
            "Auth config updated",
            {
                "admin_user": admin_user.email,
                "new_type": config_request.type,
                "enabled": config_request.enabled,
            },
        )

        return {"status": "success", "message": "Authentication configuration updated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update auth config", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update authentication configuration",
        )


@router.get("/integrations", response_model=List[IntegrationResponse])
async def get_integrations(
    admin_user: User = Depends(verify_admin_access),
) -> List[IntegrationResponse]:
    """Get all configured integrations."""
    try:
        integration_service = IntegrationService()
        integrations = await integration_service.get_all_integrations()

        response_data = []
        for integration in integrations:
            response_data.append(
                IntegrationResponse(
                    id=integration.id,
                    name=integration.name,
                    type=integration.integration_type,
                    status=integration.status,
                    last_sync=integration.last_sync,
                    config=integration.config,
                    error_message=integration.error_message,
                )
            )

        logger.info(
            "Integrations retrieved",
            {"admin_user": admin_user.email, "integration_count": len(response_data)},
        )

        return response_data

    except Exception as e:
        logger.error("Failed to get integrations", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve integrations",
        )


@router.put("/integrations/{integration_id}/toggle")
async def toggle_integration(
    integration_id: str,
    toggle_request: IntegrationToggleRequest,
    admin_user: User = Depends(verify_admin_access),
) -> Dict[str, str]:
    """Enable or disable an integration."""
    try:
        integration_service = IntegrationService()

        await integration_service.toggle_integration(
            integration_id=integration_id, enabled=toggle_request.enabled
        )

        logger.info(
            "Integration toggled",
            {
                "admin_user": admin_user.email,
                "integration_id": integration_id,
                "enabled": toggle_request.enabled,
            },
        )

        return {
            "status": "success",
            "message": f"Integration {'enabled' if toggle_request.enabled else 'disabled'}",
        }

    except Exception as e:
        logger.error(
            "Failed to toggle integration",
            {"integration_id": integration_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle integration",
        )


@router.post("/integrations", response_model=IntegrationResponse)
async def create_integration(
    integration_request: IntegrationCreateRequest,
    admin_user: User = Depends(verify_admin_access),
) -> IntegrationResponse:
    """Create a new integration."""
    try:
        integration_service = IntegrationService()

        integration = await integration_service.create_integration(
            name=integration_request.name,
            integration_type=integration_request.integration_type,
            config=integration_request.config,
        )

        logger.info(
            "Integration created",
            {
                "admin_user": admin_user.email,
                "integration_id": integration.id,
                "integration_type": integration_request.integration_type,
            },
        )

        return IntegrationResponse(
            id=integration.id,
            name=integration.name,
            type=integration.integration_type,
            status=integration.status,
            last_sync=integration.last_sync,
            config=integration.config,
            error_message=integration.error_message,
        )

    except Exception as e:
        logger.error("Failed to create integration", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create integration",
        )


@router.delete("/integrations/{integration_id}")
async def delete_integration(
    integration_id: str, admin_user: User = Depends(verify_admin_access)
) -> Dict[str, str]:
    """Delete an integration."""
    try:
        integration_service = IntegrationService()

        await integration_service.delete_integration(integration_id)

        logger.info(
            "Integration deleted",
            {"admin_user": admin_user.email, "integration_id": integration_id},
        )

        return {"status": "success", "message": "Integration deleted"}

    except Exception as e:
        logger.error(
            "Failed to delete integration",
            {"integration_id": integration_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete integration",
        )


@router.get("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str, admin_user: User = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """Test an integration connection."""
    try:
        integration_service = IntegrationService()

        test_result = await integration_service.test_integration(integration_id)

        logger.info(
            "Integration tested",
            {
                "admin_user": admin_user.email,
                "integration_id": integration_id,
                "test_passed": test_result["success"],
            },
        )

        return test_result

    except Exception as e:
        logger.error(
            "Failed to test integration",
            {"integration_id": integration_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test integration",
        )


@router.get("/system/health")
async def get_system_health(
    admin_user: User = Depends(verify_admin_access),
) -> Dict[str, Any]:
    """Get comprehensive system health information."""
    try:
        metrics_service = MetricsService()

        health_data = await metrics_service.get_system_health()

        logger.info("System health retrieved", {"admin_user": admin_user.email})

        return health_data

    except Exception as e:
        logger.error("Failed to get system health", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health",
        )


@router.get("/logs")
async def get_system_logs(
    level: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 1000,
    admin_user: User = Depends(verify_admin_access),
) -> List[Dict[str, Any]]:
    """Get system logs with filtering options."""
    try:
        # This would integrate with your logging system
        # For now, returning a placeholder
        logs = []

        logger.info(
            "System logs retrieved",
            {
                "admin_user": admin_user.email,
                "level": level,
                "category": category,
                "limit": limit,
            },
        )

        return logs

    except Exception as e:
        logger.error("Failed to get system logs", {"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system logs",
        )
