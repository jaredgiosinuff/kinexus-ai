#!/usr/bin/env python3
"""
CRAG Integration Layer for Kinexus AI
Integrates Self-Corrective RAG with existing document management and agent systems
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

from ..config.model_config import ModelConfigManager
from ..core.services.document_service import DocumentService
from ..core.services.metrics_service import MetricsService
from .agentic_rag_system import (
    AgenticRAGSystem,
    RAGQuery,
    RAGTaskType,
    RetrievalStrategy,
)
from .multi_agent_supervisor import MultiAgentSupervisor

# Import CRAG system and existing components
from .self_corrective_rag import CRAGResult, SelfCorrectiveRAG

logger = logging.getLogger(__name__)


@dataclass
class CRAGConfiguration:
    """Configuration for CRAG system integration"""

    quality_threshold: float = 0.75
    max_iterations: int = 3
    improvement_threshold: float = 0.05
    enable_metrics_collection: bool = True
    enable_learning_feedback: bool = True
    parallel_processing_limit: int = 5


class CRAGDocumentProcessor:
    """Processes document-related queries using CRAG system"""

    def __init__(
        self,
        crag_system: SelfCorrectiveRAG,
        document_service: DocumentService,
        metrics_service: MetricsService,
        config: CRAGConfiguration,
    ):
        self.crag_system = crag_system
        self.document_service = document_service
        self.metrics_service = metrics_service
        self.config = config

    async def process_document_query(
        self,
        query_text: str,
        document_context: Dict[str, Any],
        task_type: RAGTaskType = RAGTaskType.DOCUMENT_SEARCH,
    ) -> CRAGResult:
        """Process a document-related query with CRAG enhancement"""

        # Create structured query
        query = RAGQuery(
            query_text=query_text,
            task_type=task_type,
            context=document_context,
            max_results=10,
            confidence_threshold=0.7,
            strategy=RetrievalStrategy.HYBRID_RETRIEVAL,
        )

        # Process with CRAG
        start_time = datetime.utcnow()
        result = await self.crag_system.process_query(query)
        end_time = datetime.utcnow()

        # Collect metrics if enabled
        if self.config.enable_metrics_collection:
            await self._collect_metrics(query, result, start_time, end_time)

        # Store learning feedback if enabled
        if self.config.enable_learning_feedback:
            await self._store_learning_feedback(query, result)

        return result

    async def process_document_update_suggestions(
        self, document_id: str, changes: List[Dict[str, Any]]
    ) -> List[CRAGResult]:
        """Generate document update suggestions using CRAG"""

        # Get document context
        document = await self.document_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        results = []

        for change in changes:
            # Create query for each change
            query_text = f"How should I update the documentation for: {change.get('description', '')}"

            context = {
                "document_id": document_id,
                "document_type": document.get("type"),
                "change_type": change.get("type"),
                "affected_sections": change.get("sections", []),
                "current_content": document.get("content", "")[
                    :1000
                ],  # First 1k chars for context
            }

            result = await self.process_document_query(
                query_text, context, RAGTaskType.CONTEXTUAL_SYNTHESIS
            )

            results.append(result)

        return results

    async def validate_document_accuracy(self, document_id: str) -> CRAGResult:
        """Validate document accuracy using CRAG system"""

        document = await self.document_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        query_text = f"Validate the accuracy and completeness of this documentation: {document.get('title', '')}"

        context = {
            "document_id": document_id,
            "validation_mode": True,
            "content": document.get("content", ""),
            "last_updated": document.get("updated_at"),
            "document_type": document.get("type"),
        }

        return await self.process_document_query(
            query_text, context, RAGTaskType.TECHNICAL_CONTEXT
        )

    async def _collect_metrics(
        self,
        query: RAGQuery,
        result: CRAGResult,
        start_time: datetime,
        end_time: datetime,
    ):
        """Collect performance metrics for CRAG processing"""

        metrics_data = {
            "query_type": query.task_type.value,
            "processing_time": result.total_processing_time,
            "correction_iterations": result.correction_iterations,
            "corrections_applied": [c.value for c in result.corrections_applied],
            "improvement_score": result.improvement_score,
            "final_confidence": result.final_result.confidence,
            "quality_scores": {
                metric.value: score
                for metric, score in result.quality_assessment.scores.items()
            },
            "timestamp": start_time.isoformat(),
        }

        await self.metrics_service.record_metric(
            metric_name="crag_processing",
            value=result.improvement_score,
            metadata=metrics_data,
        )

    async def _store_learning_feedback(self, query: RAGQuery, result: CRAGResult):
        """Store learning feedback for continuous improvement"""

        feedback_data = {
            "query_text": query.query_text,
            "task_type": query.task_type.value,
            "final_quality_score": result.quality_assessment.overall_score,
            "corrections_needed": len(result.corrections_applied),
            "effective_corrections": result.corrections_applied,
            "processing_efficiency": (
                result.improvement_score / result.total_processing_time
                if result.total_processing_time > 0
                else 0
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store in DynamoDB for analysis
        try:
            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table("kinexus-crag-feedback")

            table.put_item(
                Item={
                    "feedback_id": f"feedback-{hash(query.query_text)}-{datetime.utcnow().timestamp()}",
                    "query_hash": str(hash(query.query_text)),
                    **feedback_data,
                }
            )

            logger.info("Stored CRAG learning feedback")

        except Exception as e:
            logger.error(f"Failed to store learning feedback: {e}")


class CRAGWebhookProcessor:
    """Processes webhook events using CRAG for improved documentation updates"""

    def __init__(
        self,
        crag_processor: CRAGDocumentProcessor,
        agent_supervisor: MultiAgentSupervisor,
    ):
        self.crag_processor = crag_processor
        self.agent_supervisor = agent_supervisor

    async def process_github_webhook(
        self, webhook_data: Dict[str, Any]
    ) -> List[CRAGResult]:
        """Process GitHub webhook events with CRAG enhancement"""

        if not webhook_data.get("commits"):
            return []

        results = []

        for commit in webhook_data["commits"]:
            # Extract change information
            commit_message = commit.get("message", "")
            modified_files = commit.get("modified", [])
            added_files = commit.get("added", [])

            # Create change context for CRAG processing
            change_context = {
                "repository": webhook_data.get("repository", {}).get("full_name"),
                "commit_id": commit.get("id"),
                "commit_message": commit_message,
                "modified_files": modified_files,
                "added_files": added_files,
                "timestamp": commit.get("timestamp"),
            }

            # Generate documentation update query
            query_text = f"What documentation updates are needed for this commit: {commit_message}"

            result = await self.crag_processor.process_document_query(
                query_text, change_context, RAGTaskType.RELATIONSHIP_MAPPING
            )

            results.append(result)

        return results

    async def process_jira_webhook(self, webhook_data: Dict[str, Any]) -> CRAGResult:
        """Process Jira webhook events with CRAG enhancement"""

        issue = webhook_data.get("issue", {})
        issue_type = issue.get("fields", {}).get("issuetype", {}).get("name", "Unknown")
        summary = issue.get("fields", {}).get("summary", "")
        description = issue.get("fields", {}).get("description", "")

        # Create issue context for CRAG processing
        issue_context = {
            "issue_key": issue.get("key"),
            "issue_type": issue_type,
            "summary": summary,
            "description": description,
            "project": issue.get("fields", {}).get("project", {}).get("key"),
            "status": issue.get("fields", {}).get("status", {}).get("name"),
        }

        # Generate documentation impact query
        query_text = (
            f"What documentation should be updated for this {issue_type}: {summary}"
        )

        return await self.crag_processor.process_document_query(
            query_text, issue_context, RAGTaskType.CONTEXTUAL_SYNTHESIS
        )


class CRAGPerformanceAnalyzer:
    """Analyzes CRAG system performance and provides optimization recommendations"""

    def __init__(self, metrics_service: MetricsService):
        self.metrics_service = metrics_service

    async def analyze_performance(self, time_period_days: int = 7) -> Dict[str, Any]:
        """Analyze CRAG system performance over specified time period"""

        # Get metrics from the specified time period
        end_time = datetime.utcnow()
        start_time = end_time.replace(day=end_time.day - time_period_days)

        try:
            metrics = await self.metrics_service.get_metrics(
                metric_name="crag_processing", start_time=start_time, end_time=end_time
            )

            if not metrics:
                return {"error": "No metrics found for specified period"}

            # Analyze performance patterns
            analysis = self._perform_analysis(metrics)

            # Generate recommendations
            recommendations = self._generate_recommendations(analysis)

            return {
                "period": f"{time_period_days} days",
                "total_queries": len(metrics),
                "analysis": analysis,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {"error": str(e)}

    def _perform_analysis(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform detailed analysis of CRAG metrics"""

        if not metrics:
            return {}

        # Extract key metrics
        processing_times = [m.get("processing_time", 0) for m in metrics]
        improvement_scores = [m.get("improvement_score", 0) for m in metrics]
        iteration_counts = [m.get("correction_iterations", 0) for m in metrics]
        confidence_scores = [m.get("final_confidence", 0) for m in metrics]

        # Calculate statistics
        analysis = {
            "performance_stats": {
                "avg_processing_time": sum(processing_times) / len(processing_times),
                "avg_improvement_score": sum(improvement_scores)
                / len(improvement_scores),
                "avg_iterations": sum(iteration_counts) / len(iteration_counts),
                "avg_confidence": sum(confidence_scores) / len(confidence_scores),
                "success_rate": len([s for s in improvement_scores if s > 0])
                / len(improvement_scores),
            },
            "correction_patterns": self._analyze_correction_patterns(metrics),
            "quality_trends": self._analyze_quality_trends(metrics),
            "efficiency_metrics": self._analyze_efficiency(metrics),
        }

        return analysis

    def _analyze_correction_patterns(
        self, metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze patterns in correction types and effectiveness"""

        correction_frequency = {}
        correction_effectiveness = {}

        for metric in metrics:
            corrections = metric.get("corrections_applied", [])
            improvement = metric.get("improvement_score", 0)

            for correction in corrections:
                correction_frequency[correction] = (
                    correction_frequency.get(correction, 0) + 1
                )

                if correction not in correction_effectiveness:
                    correction_effectiveness[correction] = []
                correction_effectiveness[correction].append(improvement)

        # Calculate average effectiveness for each correction type
        avg_effectiveness = {}
        for correction, improvements in correction_effectiveness.items():
            avg_effectiveness[correction] = sum(improvements) / len(improvements)

        return {
            "most_common_corrections": sorted(
                correction_frequency.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "most_effective_corrections": sorted(
                avg_effectiveness.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "correction_frequency": correction_frequency,
            "correction_effectiveness": avg_effectiveness,
        }

    def _analyze_quality_trends(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quality score trends over time"""

        quality_scores = []
        for metric in metrics:
            scores = metric.get("quality_scores", {})
            if scores:
                avg_score = sum(scores.values()) / len(scores)
                quality_scores.append(
                    {
                        "timestamp": metric.get("timestamp"),
                        "overall_quality": avg_score,
                        "individual_scores": scores,
                    }
                )

        return {
            "quality_trend": quality_scores,
            "average_quality_improvement": sum(
                m.get("improvement_score", 0) for m in metrics
            )
            / len(metrics),
        }

    def _analyze_efficiency(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze system efficiency metrics"""

        efficiency_scores = []
        for metric in metrics:
            processing_time = metric.get("processing_time", 1)
            improvement = metric.get("improvement_score", 0)

            # Calculate efficiency as improvement per second
            efficiency = improvement / processing_time if processing_time > 0 else 0
            efficiency_scores.append(efficiency)

        return {
            "avg_efficiency": sum(efficiency_scores) / len(efficiency_scores),
            "efficiency_distribution": {
                "high_efficiency": len([e for e in efficiency_scores if e > 0.1]),
                "medium_efficiency": len(
                    [e for e in efficiency_scores if 0.05 <= e <= 0.1]
                ),
                "low_efficiency": len([e for e in efficiency_scores if e < 0.05]),
            },
        }

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on analysis"""

        recommendations = []

        performance = analysis.get("performance_stats", {})
        patterns = analysis.get("correction_patterns", {})
        efficiency = analysis.get("efficiency_metrics", {})

        # Processing time recommendations
        avg_time = performance.get("avg_processing_time", 0)
        if avg_time > 10:
            recommendations.append(
                "Consider optimizing retrieval pipeline - average processing time is high"
            )

        # Iteration recommendations
        avg_iterations = performance.get("avg_iterations", 0)
        if avg_iterations > 2:
            recommendations.append(
                "High correction iterations detected - consider improving initial retrieval quality"
            )

        # Success rate recommendations
        success_rate = performance.get("success_rate", 0)
        if success_rate < 0.7:
            recommendations.append(
                "Low success rate - review correction strategies and quality thresholds"
            )

        # Correction pattern recommendations
        most_common = patterns.get("most_common_corrections", [])
        if (
            most_common
            and most_common[0][1]
            > len(analysis.get("quality_trends", {}).get("quality_trend", [])) * 0.5
        ):
            correction_type = most_common[0][0]
            recommendations.append(
                f"Frequent '{correction_type}' corrections suggest systematic issue - investigate root cause"
            )

        # Efficiency recommendations
        avg_efficiency = efficiency.get("avg_efficiency", 0)
        if avg_efficiency < 0.05:
            recommendations.append(
                "Low efficiency detected - consider adjusting quality thresholds or correction strategies"
            )

        return recommendations


# Integration factory
class CRAGIntegrationFactory:
    """Factory for creating CRAG integration components"""

    @staticmethod
    def create_crag_system(
        model_config: ModelConfigManager,
        document_service: DocumentService,
        metrics_service: MetricsService,
        config: Optional[CRAGConfiguration] = None,
    ) -> SelfCorrectiveRAG:
        """Create a fully configured CRAG system"""

        if config is None:
            config = CRAGConfiguration()

        # Create base RAG system (this would use your existing implementation)
        base_rag = AgenticRAGSystem(model_config)

        # Create CRAG system with configuration
        crag_system = SelfCorrectiveRAG(base_rag, model_config)
        crag_system.quality_threshold = config.quality_threshold
        crag_system.max_iterations = config.max_iterations
        crag_system.improvement_threshold = config.improvement_threshold

        return crag_system

    @staticmethod
    def create_document_processor(
        crag_system: SelfCorrectiveRAG,
        document_service: DocumentService,
        metrics_service: MetricsService,
        config: Optional[CRAGConfiguration] = None,
    ) -> CRAGDocumentProcessor:
        """Create a CRAG document processor"""

        if config is None:
            config = CRAGConfiguration()

        return CRAGDocumentProcessor(
            crag_system, document_service, metrics_service, config
        )

    @staticmethod
    def create_webhook_processor(
        crag_processor: CRAGDocumentProcessor, agent_supervisor: MultiAgentSupervisor
    ) -> CRAGWebhookProcessor:
        """Create a CRAG webhook processor"""

        return CRAGWebhookProcessor(crag_processor, agent_supervisor)

    @staticmethod
    def create_performance_analyzer(
        metrics_service: MetricsService,
    ) -> CRAGPerformanceAnalyzer:
        """Create a CRAG performance analyzer"""

        return CRAGPerformanceAnalyzer(metrics_service)


# Example integration usage
async def example_integration():
    """Example of how to integrate CRAG into Kinexus AI"""

    # Initialize services (these would be dependency injected in real system)
    model_config = ModelConfigManager()
    document_service = DocumentService()
    metrics_service = MetricsService()

    # Create CRAG configuration
    config = CRAGConfiguration(
        quality_threshold=0.8, max_iterations=2, enable_metrics_collection=True
    )

    # Create CRAG system and integrations
    crag_system = CRAGIntegrationFactory.create_crag_system(
        model_config, document_service, metrics_service, config
    )

    crag_processor = CRAGIntegrationFactory.create_document_processor(
        crag_system, document_service, metrics_service, config
    )

    # Example: Process a documentation query
    result = await crag_processor.process_document_query(
        "How do I configure the API authentication?",
        {"document_type": "api_docs", "section": "authentication"},
    )

    print("CRAG Processing Results:")
    print(f"- Quality Score: {result.quality_assessment.overall_score:.3f}")
    print(f"- Corrections Applied: {[c.value for c in result.corrections_applied]}")
    print(f"- Final Answer: {result.final_result.answer[:200]}...")


if __name__ == "__main__":
    asyncio.run(example_integration())
