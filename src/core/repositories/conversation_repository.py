import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, case, desc, func, or_
from sqlalchemy.orm import Session, sessionmaker

from ..database import get_database_session
from ..models.conversations import (
    AgentConversation,
    ConversationAnalytics,
    ConversationCreate,
    ConversationFilter,
    ConversationMetrics,
    ConversationStatus,
    ConversationSummary,
    ConversationUpdate,
    LiveConversationStatus,
    ModelCall,
    PerformanceMetrics,
    ReasoningStep,
)
from ..services.logging_service import StructuredLogger

logger = StructuredLogger("repository.conversation")


class ConversationRepository:
    """Repository for managing agent conversation data."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_database_session()

    async def create_conversation(
        self, conversation_data: ConversationCreate
    ) -> AgentConversation:
        """Create a new conversation record."""
        try:
            conversation = AgentConversation(
                id=str(uuid.uuid4()),
                agent_type=conversation_data.agent_type,
                agent_id=conversation_data.agent_id,
                task_description=conversation_data.task_description,
                task_type=conversation_data.task_type,
                reasoning_pattern=conversation_data.reasoning_pattern,
                priority=conversation_data.priority,
                status=ConversationStatus.PENDING,
                context=conversation_data.context,
                metadata=conversation_data.metadata,
                created_at=datetime.utcnow(),
            )

            self.db.add(conversation)
            self.db.commit()
            self.db.refresh(conversation)

            logger.info(
                "Conversation created",
                {
                    "conversation_id": conversation.id,
                    "agent_type": conversation.agent_type,
                    "task_type": conversation.task_type,
                },
            )

            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error("Failed to create conversation", {"error": str(e)})
            raise

    async def get_by_id(self, conversation_id: str) -> Optional[AgentConversation]:
        """Get a conversation by ID."""
        try:
            conversation = (
                self.db.query(AgentConversation)
                .filter(AgentConversation.id == conversation_id)
                .first()
            )

            if conversation:
                logger.debug(
                    "Conversation retrieved", {"conversation_id": conversation_id}
                )

            return conversation

        except Exception as e:
            logger.error(
                "Failed to get conversation",
                {"conversation_id": conversation_id, "error": str(e)},
            )
            raise

    async def update_conversation(
        self, conversation_id: str, update_data: ConversationUpdate
    ) -> Optional[AgentConversation]:
        """Update a conversation with new data."""
        try:
            conversation = await self.get_by_id(conversation_id)
            if not conversation:
                return None

            # Update fields that are provided
            update_dict = update_data.dict(exclude_unset=True)

            for field, value in update_dict.items():
                if hasattr(conversation, field):
                    if field == "reasoning_steps" and value:
                        # Convert Pydantic models to dicts for JSON storage
                        setattr(
                            conversation,
                            field,
                            [
                                step.dict() if hasattr(step, "dict") else step
                                for step in value
                            ],
                        )
                    elif field == "model_calls" and value:
                        setattr(
                            conversation,
                            field,
                            [
                                call.dict() if hasattr(call, "dict") else call
                                for call in value
                            ],
                        )
                    elif field == "performance_metrics" and value:
                        setattr(
                            conversation,
                            field,
                            value.dict() if hasattr(value, "dict") else value,
                        )
                    else:
                        setattr(conversation, field, value)

            # Update timestamps based on status changes
            if update_data.status:
                if (
                    update_data.status == ConversationStatus.RUNNING
                    and not conversation.started_at
                ):
                    conversation.started_at = datetime.utcnow()
                elif update_data.status in [
                    ConversationStatus.COMPLETED,
                    ConversationStatus.FAILED,
                    ConversationStatus.CANCELLED,
                ]:
                    if not conversation.completed_at:
                        conversation.completed_at = datetime.utcnow()
                    if conversation.started_at:
                        conversation.duration_seconds = (
                            conversation.completed_at - conversation.started_at
                        ).total_seconds()

            self.db.commit()
            self.db.refresh(conversation)

            logger.info(
                "Conversation updated",
                {
                    "conversation_id": conversation_id,
                    "status": conversation.status,
                    "duration": conversation.duration_seconds,
                },
            )

            return conversation

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to update conversation",
                {"conversation_id": conversation_id, "error": str(e)},
            )
            raise

    async def get_recent_conversations(
        self,
        limit: int = 100,
        status_filter: Optional[str] = None,
        agent_type_filter: Optional[str] = None,
    ) -> List[AgentConversation]:
        """Get recent conversations with optional filtering."""
        try:
            query = self.db.query(AgentConversation)

            # Apply filters
            if status_filter:
                query = query.filter(AgentConversation.status == status_filter)

            if agent_type_filter:
                query = query.filter(AgentConversation.agent_type == agent_type_filter)

            # Order by creation time (most recent first)
            query = query.order_by(desc(AgentConversation.created_at))

            # Apply limit
            conversations = query.limit(limit).all()

            logger.debug(
                "Recent conversations retrieved",
                {
                    "count": len(conversations),
                    "status_filter": status_filter,
                    "agent_type_filter": agent_type_filter,
                },
            )

            return conversations

        except Exception as e:
            logger.error("Failed to get recent conversations", {"error": str(e)})
            raise

    async def get_active_conversations(self) -> List[AgentConversation]:
        """Get all currently active (running) conversations."""
        try:
            conversations = (
                self.db.query(AgentConversation)
                .filter(AgentConversation.status == ConversationStatus.RUNNING)
                .order_by(desc(AgentConversation.started_at))
                .all()
            )

            logger.debug(
                "Active conversations retrieved", {"count": len(conversations)}
            )

            return conversations

        except Exception as e:
            logger.error("Failed to get active conversations", {"error": str(e)})
            raise

    async def get_conversation_summary(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> ConversationSummary:
        """Get summary statistics for conversations."""
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=1)  # Last 24 hours

            # Base query with date filter
            base_query = self.db.query(AgentConversation).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                )
            )

            # Get basic counts
            total_conversations = base_query.count()
            active_conversations = base_query.filter(
                AgentConversation.status == ConversationStatus.RUNNING
            ).count()
            completed_conversations = base_query.filter(
                AgentConversation.status == ConversationStatus.COMPLETED
            ).count()
            failed_conversations = base_query.filter(
                AgentConversation.status == ConversationStatus.FAILED
            ).count()

            # Get aggregate metrics
            completed_query = base_query.filter(
                AgentConversation.status == ConversationStatus.COMPLETED
            )

            aggregates = (
                self.db.query(
                    func.avg(AgentConversation.duration_seconds).label("avg_duration"),
                    func.avg(AgentConversation.confidence_score).label(
                        "avg_confidence"
                    ),
                    func.sum(AgentConversation.total_cost).label("total_cost"),
                    func.sum(AgentConversation.tokens_used).label("total_tokens"),
                )
                .filter(
                    and_(
                        AgentConversation.created_at >= start_date,
                        AgentConversation.created_at <= end_date,
                        AgentConversation.status == ConversationStatus.COMPLETED,
                    )
                )
                .first()
            )

            summary = ConversationSummary(
                total_conversations=total_conversations,
                active_conversations=active_conversations,
                completed_conversations=completed_conversations,
                failed_conversations=failed_conversations,
                avg_duration_seconds=float(aggregates.avg_duration or 0),
                avg_confidence=float(aggregates.avg_confidence or 0),
                total_cost=float(aggregates.total_cost or 0),
                total_tokens=int(aggregates.total_tokens or 0),
            )

            logger.info(
                "Conversation summary generated",
                {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_conversations": total_conversations,
                },
            )

            return summary

        except Exception as e:
            logger.error("Failed to get conversation summary", {"error": str(e)})
            raise

    async def get_conversations_by_filter(
        self, filter_criteria: ConversationFilter
    ) -> List[AgentConversation]:
        """Get conversations based on filter criteria."""
        try:
            query = self.db.query(AgentConversation)

            # Apply filters
            if filter_criteria.agent_type:
                query = query.filter(
                    AgentConversation.agent_type == filter_criteria.agent_type
                )

            if filter_criteria.status:
                query = query.filter(AgentConversation.status == filter_criteria.status)

            if filter_criteria.start_date:
                query = query.filter(
                    AgentConversation.created_at >= filter_criteria.start_date
                )

            if filter_criteria.end_date:
                query = query.filter(
                    AgentConversation.created_at <= filter_criteria.end_date
                )

            if filter_criteria.min_confidence:
                query = query.filter(
                    AgentConversation.confidence_score >= filter_criteria.min_confidence
                )

            if filter_criteria.max_cost:
                query = query.filter(
                    AgentConversation.total_cost <= filter_criteria.max_cost
                )

            if filter_criteria.reasoning_pattern:
                query = query.filter(
                    AgentConversation.reasoning_pattern
                    == filter_criteria.reasoning_pattern
                )

            # Apply ordering and pagination
            query = query.order_by(desc(AgentConversation.created_at))
            query = query.offset(filter_criteria.offset).limit(filter_criteria.limit)

            conversations = query.all()

            logger.debug(
                "Filtered conversations retrieved",
                {
                    "count": len(conversations),
                    "agent_type": filter_criteria.agent_type,
                    "status": filter_criteria.status,
                },
            )

            return conversations

        except Exception as e:
            logger.error("Failed to get filtered conversations", {"error": str(e)})
            raise

    async def get_conversation_analytics(
        self, time_period: str = "24h", agent_type: Optional[str] = None
    ) -> ConversationAnalytics:
        """Get detailed analytics for conversations."""
        try:
            # Parse time period
            if time_period == "1h":
                start_date = datetime.utcnow() - timedelta(hours=1)
            elif time_period == "24h":
                start_date = datetime.utcnow() - timedelta(days=1)
            elif time_period == "7d":
                start_date = datetime.utcnow() - timedelta(days=7)
            elif time_period == "30d":
                start_date = datetime.utcnow() - timedelta(days=30)
            else:
                start_date = datetime.utcnow() - timedelta(days=1)

            end_date = datetime.utcnow()

            # Base query
            base_query = self.db.query(AgentConversation).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                )
            )

            if agent_type:
                base_query = base_query.filter(
                    AgentConversation.agent_type == agent_type
                )

            # Get conversation volume over time (hourly buckets)
            volume_query = self.db.query(
                func.date_trunc("hour", AgentConversation.created_at).label("hour"),
                func.count(AgentConversation.id).label("count"),
            ).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                )
            )
            if agent_type:
                volume_query = volume_query.filter(
                    AgentConversation.agent_type == agent_type
                )

            volume_data = volume_query.group_by("hour").order_by("hour").all()
            conversation_volume = [
                {"timestamp": row.hour.isoformat(), "count": row.count}
                for row in volume_data
            ]

            # Calculate success rate
            total_completed = base_query.filter(
                AgentConversation.status.in_(
                    [ConversationStatus.COMPLETED, ConversationStatus.FAILED]
                )
            ).count()
            successful = base_query.filter(
                AgentConversation.status == ConversationStatus.COMPLETED
            ).count()
            success_rate = (successful / total_completed) if total_completed > 0 else 0

            # Average response time
            avg_response_time_result = self.db.query(
                func.avg(AgentConversation.duration_seconds)
            ).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                    AgentConversation.status == ConversationStatus.COMPLETED,
                )
            )
            if agent_type:
                avg_response_time_result = avg_response_time_result.filter(
                    AgentConversation.agent_type == agent_type
                )
            avg_response_time = float(avg_response_time_result.scalar() or 0)

            # Cost breakdown by model
            cost_query = self.db.query(
                AgentConversation.model_used,
                func.sum(AgentConversation.total_cost).label("total_cost"),
            ).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                    AgentConversation.model_used.isnot(None),
                )
            )
            if agent_type:
                cost_query = cost_query.filter(
                    AgentConversation.agent_type == agent_type
                )

            cost_data = cost_query.group_by(AgentConversation.model_used).all()
            cost_breakdown = {
                row.model_used: float(row.total_cost) for row in cost_data
            }

            # Model usage
            model_query = self.db.query(
                AgentConversation.model_used,
                func.count(AgentConversation.id).label("usage_count"),
            ).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                    AgentConversation.model_used.isnot(None),
                )
            )
            if agent_type:
                model_query = model_query.filter(
                    AgentConversation.agent_type == agent_type
                )

            model_data = model_query.group_by(AgentConversation.model_used).all()
            model_usage = {row.model_used: row.usage_count for row in model_data}

            # Confidence distribution
            confidence_ranges = [
                ("0.0-0.2", 0.0, 0.2),
                ("0.2-0.4", 0.2, 0.4),
                ("0.4-0.6", 0.4, 0.6),
                ("0.6-0.8", 0.6, 0.8),
                ("0.8-1.0", 0.8, 1.0),
            ]

            confidence_distribution = {}
            for label, min_conf, max_conf in confidence_ranges:
                count = base_query.filter(
                    and_(
                        AgentConversation.confidence_score >= min_conf,
                        AgentConversation.confidence_score < max_conf,
                        AgentConversation.confidence_score.isnot(None),
                    )
                ).count()
                confidence_distribution[label] = count

            # Reasoning pattern usage
            pattern_query = self.db.query(
                AgentConversation.reasoning_pattern,
                func.count(AgentConversation.id).label("usage_count"),
            ).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                )
            )
            if agent_type:
                pattern_query = pattern_query.filter(
                    AgentConversation.agent_type == agent_type
                )

            pattern_data = pattern_query.group_by(
                AgentConversation.reasoning_pattern
            ).all()
            reasoning_pattern_usage = {
                row.reasoning_pattern: row.usage_count for row in pattern_data
            }

            # Top errors
            error_query = self.db.query(
                AgentConversation.error_message,
                func.count(AgentConversation.id).label("error_count"),
            ).filter(
                and_(
                    AgentConversation.created_at >= start_date,
                    AgentConversation.created_at <= end_date,
                    AgentConversation.status == ConversationStatus.FAILED,
                    AgentConversation.error_message.isnot(None),
                )
            )
            if agent_type:
                error_query = error_query.filter(
                    AgentConversation.agent_type == agent_type
                )

            error_data = (
                error_query.group_by(AgentConversation.error_message)
                .order_by(desc("error_count"))
                .limit(10)
                .all()
            )

            top_errors = [
                {"error": row.error_message, "count": row.error_count}
                for row in error_data
            ]

            analytics = ConversationAnalytics(
                time_period=time_period,
                conversation_volume=conversation_volume,
                success_rate=success_rate,
                avg_response_time=avg_response_time,
                cost_breakdown=cost_breakdown,
                model_usage=model_usage,
                confidence_distribution=confidence_distribution,
                reasoning_pattern_usage=reasoning_pattern_usage,
                top_errors=top_errors,
            )

            logger.info(
                "Conversation analytics generated",
                {
                    "time_period": time_period,
                    "agent_type": agent_type,
                    "total_conversations": len(conversation_volume),
                },
            )

            return analytics

        except Exception as e:
            logger.error("Failed to get conversation analytics", {"error": str(e)})
            raise

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation record."""
        try:
            conversation = await self.get_by_id(conversation_id)
            if not conversation:
                return False

            self.db.delete(conversation)
            self.db.commit()

            logger.info("Conversation deleted", {"conversation_id": conversation_id})
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to delete conversation",
                {"conversation_id": conversation_id, "error": str(e)},
            )
            raise

    async def get_live_conversation_status(
        self, conversation_id: str
    ) -> Optional[LiveConversationStatus]:
        """Get real-time status of an active conversation."""
        try:
            conversation = await self.get_by_id(conversation_id)
            if not conversation or conversation.status != ConversationStatus.RUNNING:
                return None

            # Calculate progress based on reasoning steps and estimated completion
            reasoning_steps = conversation.reasoning_steps or []
            current_step = (
                reasoning_steps[-1]["thought"] if reasoning_steps else "Starting..."
            )

            # Estimate progress (this is a simplified calculation)
            estimated_total_steps = 10  # Default estimate
            current_steps = len(reasoning_steps)
            progress_percentage = min(
                (current_steps / estimated_total_steps) * 100, 95
            )  # Cap at 95% until complete

            # Estimate completion time based on average step duration
            if len(reasoning_steps) > 1:
                avg_step_duration = sum(
                    step.get("duration_ms", 0) for step in reasoning_steps
                ) / len(reasoning_steps)
                remaining_steps = max(estimated_total_steps - current_steps, 1)
                estimated_completion = datetime.utcnow() + timedelta(
                    milliseconds=avg_step_duration * remaining_steps
                )
            else:
                estimated_completion = None

            live_status = LiveConversationStatus(
                conversation_id=conversation_id,
                agent_type=conversation.agent_type,
                current_step=current_step,
                progress_percentage=progress_percentage,
                estimated_completion=estimated_completion,
                current_model=conversation.model_used,
                current_confidence=conversation.confidence_score,
                thoughts_so_far=len(reasoning_steps),
                tokens_used_so_far=conversation.tokens_used or 0,
                cost_so_far=conversation.total_cost or 0,
            )

            return live_status

        except Exception as e:
            logger.error(
                "Failed to get live conversation status",
                {"conversation_id": conversation_id, "error": str(e)},
            )
            raise

    async def get_conversation_metrics(self) -> ConversationMetrics:
        """Get real-time conversation metrics."""
        try:
            # Active conversations
            active_count = (
                self.db.query(AgentConversation)
                .filter(AgentConversation.status == ConversationStatus.RUNNING)
                .count()
            )

            # Queue length (pending conversations)
            queue_length = (
                self.db.query(AgentConversation)
                .filter(AgentConversation.status == ConversationStatus.PENDING)
                .count()
            )

            # Average wait time (time between creation and start)
            wait_time_result = (
                self.db.query(
                    func.avg(
                        func.extract("epoch", AgentConversation.started_at)
                        - func.extract("epoch", AgentConversation.created_at)
                    )
                )
                .filter(
                    and_(
                        AgentConversation.started_at.isnot(None),
                        AgentConversation.created_at
                        >= datetime.utcnow() - timedelta(hours=24),
                    )
                )
                .scalar()
            )
            avg_wait_time = float(wait_time_result or 0)

            # Throughput (conversations completed in last hour)
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            throughput_per_hour = (
                self.db.query(AgentConversation)
                .filter(
                    and_(
                        AgentConversation.status == ConversationStatus.COMPLETED,
                        AgentConversation.completed_at >= one_hour_ago,
                    )
                )
                .count()
            )

            # Success rate in last 24 hours
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            total_completed_24h = (
                self.db.query(AgentConversation)
                .filter(
                    and_(
                        AgentConversation.completed_at >= twenty_four_hours_ago,
                        AgentConversation.status.in_(
                            [ConversationStatus.COMPLETED, ConversationStatus.FAILED]
                        ),
                    )
                )
                .count()
            )
            successful_24h = (
                self.db.query(AgentConversation)
                .filter(
                    and_(
                        AgentConversation.completed_at >= twenty_four_hours_ago,
                        AgentConversation.status == ConversationStatus.COMPLETED,
                    )
                )
                .count()
            )
            success_rate_24h = (
                (successful_24h / total_completed_24h) if total_completed_24h > 0 else 0
            )

            # Cost per hour
            cost_per_hour_result = (
                self.db.query(func.sum(AgentConversation.total_cost))
                .filter(
                    and_(
                        AgentConversation.completed_at >= one_hour_ago,
                        AgentConversation.status == ConversationStatus.COMPLETED,
                    )
                )
                .scalar()
            )
            cost_per_hour = float(cost_per_hour_result or 0)

            # Top agent types by volume
            top_agents_result = (
                self.db.query(
                    AgentConversation.agent_type,
                    func.count(AgentConversation.id).label("count"),
                )
                .filter(AgentConversation.created_at >= twenty_four_hours_ago)
                .group_by(AgentConversation.agent_type)
                .order_by(desc("count"))
                .limit(5)
                .all()
            )

            top_agent_types = [
                {"agent_type": row.agent_type, "count": row.count}
                for row in top_agents_result
            ]

            # Reasoning pattern performance
            pattern_performance_result = (
                self.db.query(
                    AgentConversation.reasoning_pattern,
                    func.avg(AgentConversation.duration_seconds).label("avg_duration"),
                    func.avg(AgentConversation.confidence_score).label(
                        "avg_confidence"
                    ),
                    func.avg(AgentConversation.total_cost).label("avg_cost"),
                )
                .filter(
                    and_(
                        AgentConversation.completed_at >= twenty_four_hours_ago,
                        AgentConversation.status == ConversationStatus.COMPLETED,
                    )
                )
                .group_by(AgentConversation.reasoning_pattern)
                .all()
            )

            reasoning_pattern_performance = {}
            for row in pattern_performance_result:
                reasoning_pattern_performance[row.reasoning_pattern] = {
                    "avg_duration": float(row.avg_duration or 0),
                    "avg_confidence": float(row.avg_confidence or 0),
                    "avg_cost": float(row.avg_cost or 0),
                }

            metrics = ConversationMetrics(
                active_count=active_count,
                queue_length=queue_length,
                avg_wait_time=avg_wait_time,
                throughput_per_hour=throughput_per_hour,
                success_rate_24h=success_rate_24h,
                cost_per_hour=cost_per_hour,
                top_agent_types=top_agent_types,
                reasoning_pattern_performance=reasoning_pattern_performance,
            )

            logger.debug(
                "Conversation metrics calculated",
                {
                    "active_count": active_count,
                    "queue_length": queue_length,
                    "success_rate_24h": success_rate_24h,
                },
            )

            return metrics

        except Exception as e:
            logger.error("Failed to get conversation metrics", {"error": str(e)})
            raise
