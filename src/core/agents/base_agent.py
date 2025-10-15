"""
Enhanced Base Agent with Multi-Model Support and Advanced Reasoning
Supports Claude 4, Nova models, and configurable reasoning patterns
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..config import get_settings
from ..models.ai_models import AIModelType, ModelCapability, ModelProvider
from ..services.logging_service import StructuredLogger
from ..services.metrics_service import MetricsService


class ReasoningPattern(Enum):
    """Different reasoning patterns for agent thinking"""

    LINEAR = "linear"
    TREE_OF_THOUGHT = "tree_of_thought"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    MULTI_PERSPECTIVE = "multi_perspective"
    CRITIQUE_AND_REFINE = "critique_and_refine"
    ENSEMBLE = "ensemble"


class ThoughtType(Enum):
    """Types of thoughts in the reasoning chain"""

    OBSERVATION = "observation"
    HYPOTHESIS = "hypothesis"
    ANALYSIS = "analysis"
    CRITIQUE = "critique"
    SYNTHESIS = "synthesis"
    DECISION = "decision"
    REFLECTION = "reflection"


@dataclass
class Thought:
    """Represents a single thought in the reasoning chain"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ThoughtType = ThoughtType.OBSERVATION
    content: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    model_used: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_thought_id: Optional[str] = None
    children_thought_ids: List[str] = field(default_factory=list)


@dataclass
class ReasoningChain:
    """Complete reasoning chain for a task"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    task_id: str = ""
    pattern: ReasoningPattern = ReasoningPattern.LINEAR
    thoughts: List[Thought] = field(default_factory=list)
    final_decision: Optional[str] = None
    confidence_score: float = 0.0
    total_reasoning_time: float = 0.0
    models_used: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class ModelConfig(BaseModel):
    """Configuration for AI model usage"""

    model_type: AIModelType
    provider: ModelProvider
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, gt=0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    capabilities: List[ModelCapability] = Field(default_factory=list)
    cost_per_token: float = Field(default=0.0, ge=0.0)


class AgentConfig(BaseModel):
    """Configuration for agent behavior"""

    name: str
    description: str
    reasoning_pattern: ReasoningPattern = ReasoningPattern.CHAIN_OF_THOUGHT
    primary_model: ModelConfig
    secondary_models: List[ModelConfig] = Field(default_factory=list)
    max_reasoning_depth: int = Field(default=5, gt=0)
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    enable_critique: bool = True
    enable_reflection: bool = True
    timeout_seconds: int = Field(default=300, gt=0)
    retry_attempts: int = Field(default=3, ge=0)


class BaseAgent(ABC):
    """
    Enhanced base class for all AI agents with advanced reasoning capabilities
    """

    def __init__(
        self,
        config: AgentConfig,
        metrics_service: Optional[MetricsService] = None,
        logger: Optional[StructuredLogger] = None,
    ):
        self.config = config
        self.agent_id = str(uuid.uuid4())
        self.settings = get_settings()

        # Initialize services
        self.metrics = metrics_service or MetricsService()
        self.logger = logger or StructuredLogger(name=self.__class__.__name__)

        # Reasoning state
        self.current_reasoning_chain: Optional[ReasoningChain] = None
        self.active_tasks: Dict[str, ReasoningChain] = {}

        # Performance tracking
        self.total_tasks_processed = 0
        self.average_reasoning_time = 0.0
        self.success_rate = 0.0

        self.logger.info(
            "Agent initialized",
            agent_id=self.agent_id,
            agent_type=self.__class__.__name__,
            config=config.dict(),
        )

    @abstractmethod
    async def process_task(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a task using the agent's reasoning capabilities

        Args:
            task: The task to process
            context: Additional context for the task

        Returns:
            Dict containing the result and reasoning chain
        """
        pass

    async def reason_about_task(
        self, task: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> ReasoningChain:
        """
        Execute the reasoning process for a given task
        """
        start_time = time.time()

        # Create reasoning chain
        reasoning_chain = ReasoningChain(
            agent_id=self.agent_id,
            task_id=task.get("id", str(uuid.uuid4())),
            pattern=self.config.reasoning_pattern,
        )

        self.current_reasoning_chain = reasoning_chain
        self.active_tasks[reasoning_chain.task_id] = reasoning_chain

        try:
            # Execute reasoning based on pattern
            if self.config.reasoning_pattern == ReasoningPattern.CHAIN_OF_THOUGHT:
                await self._chain_of_thought_reasoning(task, context, reasoning_chain)
            elif self.config.reasoning_pattern == ReasoningPattern.TREE_OF_THOUGHT:
                await self._tree_of_thought_reasoning(task, context, reasoning_chain)
            elif self.config.reasoning_pattern == ReasoningPattern.MULTI_PERSPECTIVE:
                await self._multi_perspective_reasoning(task, context, reasoning_chain)
            elif self.config.reasoning_pattern == ReasoningPattern.CRITIQUE_AND_REFINE:
                await self._critique_and_refine_reasoning(
                    task, context, reasoning_chain
                )
            elif self.config.reasoning_pattern == ReasoningPattern.ENSEMBLE:
                await self._ensemble_reasoning(task, context, reasoning_chain)
            else:
                await self._linear_reasoning(task, context, reasoning_chain)

            # Final confidence calculation
            reasoning_chain.confidence_score = self._calculate_confidence(
                reasoning_chain
            )
            reasoning_chain.completed_at = datetime.now(timezone.utc)
            reasoning_chain.total_reasoning_time = time.time() - start_time

            # Log completion
            self.logger.info(
                "Reasoning completed",
                reasoning_chain_id=reasoning_chain.id,
                pattern=reasoning_chain.pattern.value,
                confidence=reasoning_chain.confidence_score,
                duration=reasoning_chain.total_reasoning_time,
                thoughts_count=len(reasoning_chain.thoughts),
            )

            # Update metrics
            await self._update_metrics(reasoning_chain)

            return reasoning_chain

        except Exception as e:
            self.logger.error(
                "Reasoning failed",
                reasoning_chain_id=reasoning_chain.id,
                error=str(e),
                duration=time.time() - start_time,
            )
            raise
        finally:
            # Cleanup
            if reasoning_chain.task_id in self.active_tasks:
                del self.active_tasks[reasoning_chain.task_id]
            self.current_reasoning_chain = None

    async def _chain_of_thought_reasoning(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        reasoning_chain: ReasoningChain,
    ):
        """Implement chain-of-thought reasoning"""
        # Initial observation
        observation = await self._generate_thought(
            ThoughtType.OBSERVATION,
            f"Analyzing task: {task.get('description', 'No description')}",
            task,
            context,
            self.config.primary_model,
        )
        reasoning_chain.thoughts.append(observation)

        # Generate hypothesis
        hypothesis = await self._generate_thought(
            ThoughtType.HYPOTHESIS,
            "Generating initial hypothesis based on observation",
            task,
            context,
            self.config.primary_model,
            parent_thought=observation,
        )
        reasoning_chain.thoughts.append(hypothesis)

        # Analyze hypothesis
        analysis = await self._generate_thought(
            ThoughtType.ANALYSIS,
            "Analyzing hypothesis validity and implications",
            task,
            context,
            self.config.primary_model,
            parent_thought=hypothesis,
        )
        reasoning_chain.thoughts.append(analysis)

        # Critique if enabled
        if self.config.enable_critique:
            critique = await self._generate_thought(
                ThoughtType.CRITIQUE,
                "Critiquing analysis and identifying potential issues",
                task,
                context,
                self._get_critique_model(),
                parent_thought=analysis,
            )
            reasoning_chain.thoughts.append(critique)

        # Final synthesis
        synthesis = await self._generate_thought(
            ThoughtType.SYNTHESIS,
            "Synthesizing findings into final decision",
            task,
            context,
            self.config.primary_model,
            parent_thought=reasoning_chain.thoughts[-1],
        )
        reasoning_chain.thoughts.append(synthesis)
        reasoning_chain.final_decision = synthesis.content

    async def _tree_of_thought_reasoning(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        reasoning_chain: ReasoningChain,
    ):
        """Implement tree-of-thought reasoning with multiple branches"""
        # Initial observation
        root_observation = await self._generate_thought(
            ThoughtType.OBSERVATION,
            f"Root analysis of task: {task.get('description', 'No description')}",
            task,
            context,
            self.config.primary_model,
        )
        reasoning_chain.thoughts.append(root_observation)

        # Generate multiple hypotheses (branches)
        hypotheses = []
        for i in range(3):  # Generate 3 different hypotheses
            hypothesis = await self._generate_thought(
                ThoughtType.HYPOTHESIS,
                f"Alternative hypothesis {i+1}",
                task,
                context,
                self.config.primary_model,
                parent_thought=root_observation,
            )
            reasoning_chain.thoughts.append(hypothesis)
            hypotheses.append(hypothesis)

        # Analyze each hypothesis
        analyses = []
        for hypothesis in hypotheses:
            analysis = await self._generate_thought(
                ThoughtType.ANALYSIS,
                f"Detailed analysis of hypothesis: {hypothesis.content[:100]}...",
                task,
                context,
                self.config.primary_model,
                parent_thought=hypothesis,
            )
            reasoning_chain.thoughts.append(analysis)
            analyses.append(analysis)

        # Select best path based on confidence
        best_analysis = max(analyses, key=lambda x: x.confidence)

        # Final synthesis based on best path
        synthesis = await self._generate_thought(
            ThoughtType.SYNTHESIS,
            "Synthesizing best analysis into final decision",
            task,
            context,
            self.config.primary_model,
            parent_thought=best_analysis,
        )
        reasoning_chain.thoughts.append(synthesis)
        reasoning_chain.final_decision = synthesis.content

    async def _multi_perspective_reasoning(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        reasoning_chain: ReasoningChain,
    ):
        """Implement multi-perspective reasoning using different models"""
        perspectives = []

        # Get perspectives from different models
        models_to_use = [self.config.primary_model] + self.config.secondary_models[:2]

        for i, model in enumerate(models_to_use):
            perspective = await self._generate_thought(
                ThoughtType.ANALYSIS,
                f"Perspective {i+1}: {model.model_type.value} analysis",
                task,
                context,
                model,
            )
            reasoning_chain.thoughts.append(perspective)
            perspectives.append(perspective)

        # Synthesize perspectives
        synthesis_prompt = f"Synthesize the following perspectives: {[p.content for p in perspectives]}"
        synthesis = await self._generate_thought(
            ThoughtType.SYNTHESIS,
            synthesis_prompt,
            task,
            context,
            self.config.primary_model,
        )
        reasoning_chain.thoughts.append(synthesis)
        reasoning_chain.final_decision = synthesis.content

    async def _critique_and_refine_reasoning(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        reasoning_chain: ReasoningChain,
    ):
        """Implement critique and refine reasoning pattern"""
        # Initial analysis
        initial_analysis = await self._generate_thought(
            ThoughtType.ANALYSIS,
            "Initial analysis of the task",
            task,
            context,
            self.config.primary_model,
        )
        reasoning_chain.thoughts.append(initial_analysis)

        current_analysis = initial_analysis

        # Iterative refinement
        for iteration in range(3):
            # Critique current analysis
            critique = await self._generate_thought(
                ThoughtType.CRITIQUE,
                f"Critique iteration {iteration + 1}: Identify flaws and improvements",
                task,
                context,
                self._get_critique_model(),
                parent_thought=current_analysis,
            )
            reasoning_chain.thoughts.append(critique)

            # Refine based on critique
            refined_analysis = await self._generate_thought(
                ThoughtType.ANALYSIS,
                f"Refined analysis addressing critique: {critique.content}",
                task,
                context,
                self.config.primary_model,
                parent_thought=critique,
            )
            reasoning_chain.thoughts.append(refined_analysis)
            current_analysis = refined_analysis

            # Check if confident enough to stop
            if current_analysis.confidence > self.config.confidence_threshold:
                break

        reasoning_chain.final_decision = current_analysis.content

    async def _ensemble_reasoning(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        reasoning_chain: ReasoningChain,
    ):
        """Implement ensemble reasoning combining multiple models and patterns"""
        _ensemble_results = []

        # Run different reasoning patterns in parallel
        patterns = [
            ReasoningPattern.CHAIN_OF_THOUGHT,
            ReasoningPattern.MULTI_PERSPECTIVE,
        ]

        tasks_to_run = []
        for pattern in patterns:
            # Create temporary sub-chain
            sub_chain = ReasoningChain(
                agent_id=self.agent_id,
                task_id=f"{reasoning_chain.task_id}_sub_{pattern.value}",
                pattern=pattern,
            )

            if pattern == ReasoningPattern.CHAIN_OF_THOUGHT:
                tasks_to_run.append(
                    self._chain_of_thought_reasoning(task, context, sub_chain)
                )
            elif pattern == ReasoningPattern.MULTI_PERSPECTIVE:
                tasks_to_run.append(
                    self._multi_perspective_reasoning(task, context, sub_chain)
                )

        # Execute in parallel
        await asyncio.gather(*tasks_to_run)

        # Combine results
        ensemble_synthesis = await self._generate_thought(
            ThoughtType.SYNTHESIS,
            "Ensemble synthesis combining multiple reasoning approaches",
            task,
            context,
            self.config.primary_model,
        )
        reasoning_chain.thoughts.append(ensemble_synthesis)
        reasoning_chain.final_decision = ensemble_synthesis.content

    async def _linear_reasoning(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        reasoning_chain: ReasoningChain,
    ):
        """Simple linear reasoning for basic tasks"""
        analysis = await self._generate_thought(
            ThoughtType.ANALYSIS,
            f"Direct analysis of task: {task.get('description', 'No description')}",
            task,
            context,
            self.config.primary_model,
        )
        reasoning_chain.thoughts.append(analysis)
        reasoning_chain.final_decision = analysis.content

    async def _generate_thought(
        self,
        thought_type: ThoughtType,
        prompt: str,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        model_config: ModelConfig,
        parent_thought: Optional[Thought] = None,
    ) -> Thought:
        """Generate a single thought using the specified model"""
        try:
            # Build context for the thought
            thought_context = {
                "task": task,
                "context": context or {},
                "prompt": prompt,
                "thought_type": thought_type.value,
            }

            if parent_thought:
                thought_context["parent_thought"] = parent_thought.content

            # Generate thought content using AI model
            response = await self._call_ai_model(model_config, thought_context)

            # Extract confidence if available
            confidence = self._extract_confidence(response)

            # Create thought
            thought = Thought(
                type=thought_type,
                content=response.get("content", ""),
                confidence=confidence,
                reasoning=response.get("reasoning", ""),
                model_used=f"{model_config.provider.value}:{model_config.model_type.value}",
                metadata={
                    "model_config": model_config.dict(),
                    "response_metadata": response.get("metadata", {}),
                },
                parent_thought_id=parent_thought.id if parent_thought else None,
            )

            # Update parent-child relationships
            if parent_thought:
                parent_thought.children_thought_ids.append(thought.id)

            self.logger.debug(
                "Thought generated",
                thought_id=thought.id,
                thought_type=thought_type.value,
                confidence=confidence,
                model=thought.model_used,
            )

            return thought

        except Exception as e:
            self.logger.error(
                "Failed to generate thought",
                thought_type=thought_type.value,
                model=f"{model_config.provider.value}:{model_config.model_type.value}",
                error=str(e),
            )

            # Return error thought
            return Thought(
                type=thought_type,
                content=f"Error generating thought: {str(e)}",
                confidence=0.0,
                model_used=f"{model_config.provider.value}:{model_config.model_type.value}",
                metadata={"error": str(e)},
            )

    async def _call_ai_model(
        self, model_config: ModelConfig, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call the AI model with the given configuration and context"""
        # This will be implemented by connecting to actual AI services
        # For now, return a mock response

        model_name = f"{model_config.provider.value}:{model_config.model_type.value}"

        # Mock different model responses based on type
        if model_config.model_type == AIModelType.CLAUDE_4_OPUS:
            content = f"Claude 4 Opus analysis: {context['prompt']}"
            confidence = 0.9
        elif model_config.model_type == AIModelType.NOVA_PRO:
            content = f"Nova Pro multimodal analysis: {context['prompt']}"
            confidence = 0.85
        else:
            content = f"AI analysis: {context['prompt']}"
            confidence = 0.8

        return {
            "content": content,
            "reasoning": f"Reasoning process for {model_name}",
            "confidence": confidence,
            "metadata": {"model": model_name, "tokens_used": 150, "response_time": 1.2},
        }

    def _get_critique_model(self) -> ModelConfig:
        """Get the best model for critique tasks"""
        # Prefer a different model for critique to get diverse perspectives
        if self.config.secondary_models:
            return self.config.secondary_models[0]
        return self.config.primary_model

    def _extract_confidence(self, response: Dict[str, Any]) -> float:
        """Extract confidence score from model response"""
        return response.get("confidence", 0.5)

    def _calculate_confidence(self, reasoning_chain: ReasoningChain) -> float:
        """Calculate overall confidence for the reasoning chain"""
        if not reasoning_chain.thoughts:
            return 0.0

        # Weight recent thoughts more heavily
        total_confidence = 0.0
        total_weight = 0.0

        for i, thought in enumerate(reasoning_chain.thoughts):
            weight = 1.0 + (i * 0.1)  # Later thoughts have more weight
            total_confidence += thought.confidence * weight
            total_weight += weight

        return total_confidence / total_weight if total_weight > 0 else 0.0

    async def _update_metrics(self, reasoning_chain: ReasoningChain):
        """Update performance metrics"""
        self.total_tasks_processed += 1

        # Update average reasoning time
        self.average_reasoning_time = (
            self.average_reasoning_time * (self.total_tasks_processed - 1)
            + reasoning_chain.total_reasoning_time
        ) / self.total_tasks_processed

        # Update success rate (based on confidence)
        success = reasoning_chain.confidence_score > self.config.confidence_threshold
        self.success_rate = (
            self.success_rate * (self.total_tasks_processed - 1)
            + (1.0 if success else 0.0)
        ) / self.total_tasks_processed

        # Send metrics to service
        await self.metrics.record_agent_performance(
            agent_id=self.agent_id,
            reasoning_time=reasoning_chain.total_reasoning_time,
            confidence_score=reasoning_chain.confidence_score,
            thoughts_count=len(reasoning_chain.thoughts),
            models_used=len(set(t.model_used for t in reasoning_chain.thoughts)),
            success=success,
        )

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        return {
            "agent_id": self.agent_id,
            "total_tasks_processed": self.total_tasks_processed,
            "average_reasoning_time": self.average_reasoning_time,
            "success_rate": self.success_rate,
            "active_tasks": len(self.active_tasks),
            "config": self.config.dict(),
        }
