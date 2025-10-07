from sqlalchemy import Column, String, DateTime, Float, Integer, Text, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
import uuid

Base = declarative_base()

class ConversationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ReasoningStep(BaseModel):
    """Individual step in the reasoning process."""
    step_number: int
    thought: str
    confidence: float
    model_used: str
    tokens_used: int
    duration_ms: float
    metadata: Dict[str, Any] = {}

class ModelCall(BaseModel):
    """Details of a call to an AI model."""
    model_name: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    duration_ms: float
    temperature: float
    response_metadata: Dict[str, Any] = {}

class PerformanceMetrics(BaseModel):
    """Performance metrics for the conversation."""
    total_duration_ms: float
    reasoning_time_ms: float
    model_call_time_ms: float
    queue_time_ms: float
    total_tokens_used: int
    total_cost: float
    avg_confidence: float
    memory_usage_mb: float
    cpu_usage_percent: float

class AgentConversation(Base):
    """Database model for agent conversations."""
    __tablename__ = "agent_conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)

    # Task information
    task_description = Column(Text, nullable=False)
    task_type = Column(String, nullable=False)
    priority = Column(String, default="medium")

    # Status and timing
    status = Column(String, nullable=False, default=ConversationStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Reasoning information
    reasoning_pattern = Column(String, nullable=False)
    reasoning_steps = Column(JSON, nullable=True)  # List of ReasoningStep objects
    final_thought = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Model usage
    model_used = Column(String, nullable=True)
    model_calls = Column(JSON, nullable=True)  # List of ModelCall objects
    tokens_used = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # Results
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Performance metrics
    performance_metrics = Column(JSON, nullable=True)  # PerformanceMetrics object

    # Context and metadata
    context = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Relationships
    parent_conversation_id = Column(String, ForeignKey('agent_conversations.id'), nullable=True)
    parent_conversation = relationship("AgentConversation", remote_side=[id])

    # Indexing for common queries
    __table_args__ = (
        {'mysql_engine': 'InnoDB'},
    )

class ConversationSummary(BaseModel):
    """Summary statistics for conversations."""
    total_conversations: int
    active_conversations: int
    completed_conversations: int
    failed_conversations: int
    avg_duration_seconds: float
    avg_confidence: float
    total_cost: float
    total_tokens: int

class ConversationFilter(BaseModel):
    """Filter criteria for conversation queries."""
    agent_type: Optional[str] = None
    status: Optional[ConversationStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_confidence: Optional[float] = None
    max_cost: Optional[float] = None
    reasoning_pattern: Optional[str] = None
    limit: int = 100
    offset: int = 0

class ConversationCreate(BaseModel):
    """Request model for creating a new conversation."""
    agent_type: str
    agent_id: str
    task_description: str
    task_type: str
    reasoning_pattern: str
    priority: str = "medium"
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ConversationUpdate(BaseModel):
    """Request model for updating a conversation."""
    status: Optional[ConversationStatus] = None
    reasoning_steps: Optional[List[ReasoningStep]] = None
    final_thought: Optional[str] = None
    confidence_score: Optional[float] = None
    model_used: Optional[str] = None
    model_calls: Optional[List[ModelCall]] = None
    tokens_used: Optional[int] = None
    total_cost: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    performance_metrics: Optional[PerformanceMetrics] = None

class ConversationResponse(BaseModel):
    """Response model for conversation data."""
    id: str
    agent_type: str
    agent_id: str
    task_description: str
    task_type: str
    priority: str
    status: ConversationStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    reasoning_pattern: str
    final_thought: Optional[str]
    confidence_score: Optional[float]
    model_used: Optional[str]
    tokens_used: int
    total_cost: float
    context: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]

class DetailedConversationResponse(ConversationResponse):
    """Detailed response model including reasoning steps and model calls."""
    reasoning_steps: Optional[List[ReasoningStep]]
    model_calls: Optional[List[ModelCall]]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    performance_metrics: Optional[PerformanceMetrics]
    parent_conversation_id: Optional[str]

class ConversationAnalytics(BaseModel):
    """Analytics data for conversations."""
    time_period: str
    conversation_volume: List[Dict[str, Any]]
    success_rate: float
    avg_response_time: float
    cost_breakdown: Dict[str, float]
    model_usage: Dict[str, int]
    confidence_distribution: Dict[str, int]
    reasoning_pattern_usage: Dict[str, int]
    top_errors: List[Dict[str, Any]]

class ConversationEvent(BaseModel):
    """Event model for conversation state changes."""
    conversation_id: str
    event_type: str
    timestamp: datetime
    details: Dict[str, Any]
    agent_type: str
    agent_id: str

# Real-time conversation tracking models
class LiveConversationStatus(BaseModel):
    """Real-time status of active conversations."""
    conversation_id: str
    agent_type: str
    current_step: str
    progress_percentage: float
    estimated_completion: Optional[datetime]
    current_model: Optional[str]
    current_confidence: Optional[float]
    thoughts_so_far: int
    tokens_used_so_far: int
    cost_so_far: float

class ConversationMetrics(BaseModel):
    """Metrics for conversation monitoring."""
    active_count: int
    queue_length: int
    avg_wait_time: float
    throughput_per_hour: float
    success_rate_24h: float
    cost_per_hour: float
    top_agent_types: List[Dict[str, Any]]
    reasoning_pattern_performance: Dict[str, Dict[str, float]]

# Search and filtering models
class ConversationSearchRequest(BaseModel):
    """Request model for searching conversations."""
    query: str
    filters: ConversationFilter
    sort_by: str = "created_at"
    sort_order: str = "desc"
    include_reasoning: bool = False
    include_performance: bool = False

class ConversationSearchResponse(BaseModel):
    """Response model for conversation search."""
    conversations: List[ConversationResponse]
    total_count: int
    page: int
    page_size: int
    has_more: bool
    search_metadata: Dict[str, Any]

# Conversation templates for common patterns
class ConversationTemplate(BaseModel):
    """Template for creating conversations with predefined patterns."""
    name: str
    description: str
    agent_type: str
    task_type: str
    reasoning_pattern: str
    default_context: Dict[str, Any]
    parameter_schema: Dict[str, Any]
    expected_duration: float
    typical_cost: float

class ConversationWorkflow(BaseModel):
    """Workflow definition for multi-step conversations."""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    conditions: Dict[str, Any]
    timeout_seconds: int
    retry_policy: Dict[str, Any]