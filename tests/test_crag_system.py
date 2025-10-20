#!/usr/bin/env python3
"""
Test suite for Self-Corrective RAG (CRAG) system
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.agentic_rag_system import RAGQuery, RAGResult, RAGTaskType
from src.agents.crag_integration import CRAGConfiguration, CRAGDocumentProcessor

# Import CRAG components
from src.agents.self_corrective_rag import (
    CorrectionAction,
    CorrectionContext,
    CorrectionEngine,
    CRAGResult,
    QualityAssessment,
    QualityAssessor,
    QualityMetric,
    SelfCorrectiveRAG,
)
from src.config.model_config import ModelConfigManager


class TestQualityAssessor:
    """Test cases for quality assessment functionality"""

    @pytest.fixture
    def mock_model_config(self):
        """Mock model configuration"""
        config = Mock(spec=ModelConfigManager)
        config.region = "us-east-1"
        return config

    @pytest.fixture
    def quality_assessor(self, mock_model_config):
        """Create quality assessor instance"""
        return QualityAssessor(mock_model_config)

    @pytest.fixture
    def sample_query(self):
        """Sample RAG query for testing"""
        return RAGQuery(
            query_text="How do I implement error handling in Python?",
            task_type=RAGTaskType.CODE_ANALYSIS,
            context={"language": "python"},
            max_results=5,
        )

    @pytest.fixture
    def sample_result(self):
        """Sample RAG result for testing"""
        return RAGResult(
            query_id="test-query-123",
            answer="Use try-except blocks to handle errors in Python.",
            sources=[
                {"title": "Python Error Handling", "content": "Try-except blocks..."},
                {"title": "Exception Guide", "content": "Python exceptions..."},
            ],
            confidence=0.7,
            processing_time=2.5,
            metadata={},
        )

    @pytest.mark.asyncio
    async def test_assess_quality(self, quality_assessor, sample_query, sample_result):
        """Test basic quality assessment"""

        # Mock Bedrock responses
        with patch.object(quality_assessor, "_call_bedrock") as mock_bedrock:
            mock_bedrock.return_value = "0.8"  # Mock assessment score

            assessment = await quality_assessor.assess_quality(
                sample_query, sample_result
            )

            assert isinstance(assessment, QualityAssessment)
            assert assessment.query_id == sample_result.query_id
            assert 0.0 <= assessment.overall_score <= 1.0
            assert QualityMetric.RELEVANCE in assessment.scores
            assert QualityMetric.ACCURACY in assessment.scores

    @pytest.mark.asyncio
    async def test_relevance_assessment(
        self, quality_assessor, sample_query, sample_result
    ):
        """Test relevance assessment specifically"""

        with patch.object(quality_assessor, "_call_bedrock") as mock_bedrock:
            mock_bedrock.return_value = "0.9"

            score = await quality_assessor._assess_relevance(
                sample_query, sample_result
            )

            assert 0.0 <= score <= 1.0
            assert score == 0.9

    @pytest.mark.asyncio
    async def test_assessment_with_low_scores(
        self, quality_assessor, sample_query, sample_result
    ):
        """Test assessment when quality scores are low"""

        with patch.object(quality_assessor, "_call_bedrock") as mock_bedrock:
            mock_bedrock.return_value = "0.5"  # Low score

            assessment = await quality_assessor.assess_quality(
                sample_query, sample_result
            )

            assert assessment.needs_correction(threshold=0.7)
            assert len(assessment.suggested_corrections) > 0

    def test_source_reliability_assessment(self, quality_assessor, sample_result):
        """Test source reliability assessment"""

        # Test with reliable sources
        reliable_result = RAGResult(
            query_id="test",
            answer="Test answer",
            sources=[
                {"title": "Official Documentation", "path": "/docs/official.md"},
                {"title": "API Guide", "path": "/guides/api.md"},
            ],
            confidence=0.8,
            processing_time=1.0,
            metadata={},
        )

        score = asyncio.run(
            quality_assessor._assess_source_reliability(reliable_result)
        )
        assert score > 0.5  # Should be higher for reliable sources


class TestCorrectionEngine:
    """Test cases for correction engine functionality"""

    @pytest.fixture
    def mock_rag_system(self):
        """Mock RAG system"""
        rag = Mock()
        rag.process_query = AsyncMock()
        return rag

    @pytest.fixture
    def mock_model_config(self):
        """Mock model configuration"""
        config = Mock(spec=ModelConfigManager)
        config.region = "us-east-1"
        return config

    @pytest.fixture
    def correction_engine(self, mock_rag_system, mock_model_config):
        """Create correction engine instance"""
        return CorrectionEngine(mock_rag_system, mock_model_config)

    @pytest.fixture
    def correction_context(self, sample_query, sample_result):
        """Sample correction context"""
        assessment = QualityAssessment(
            query_id="test",
            timestamp=datetime.utcnow(),
            scores={QualityMetric.RELEVANCE: 0.6},
            overall_score=0.6,
            confidence=0.7,
            issues_identified=["Low relevance"],
            suggested_corrections=[CorrectionAction.RETRIEVE_MORE],
            reasoning="Test assessment",
        )

        return CorrectionContext(
            original_query=sample_query,
            original_result=sample_result,
            assessment=assessment,
        )

    @pytest.mark.asyncio
    async def test_apply_corrections(self, correction_engine, correction_context):
        """Test applying corrections"""

        with patch.object(correction_engine, "_call_bedrock") as mock_bedrock:
            mock_bedrock.return_value = "Improved answer"

            with patch.object(
                correction_engine, "_retrieve_more_sources"
            ) as mock_retrieve:
                mock_retrieve.return_value = correction_context.original_result

                result = await correction_engine.apply_corrections(correction_context)

                assert isinstance(result, RAGResult)
                assert (
                    CorrectionAction.RETRIEVE_MORE
                    in correction_context.correction_history
                )

    @pytest.mark.asyncio
    async def test_retrieve_more_sources(self, correction_engine, correction_context):
        """Test retrieving more sources correction"""

        # Mock additional sources
        additional_result = RAGResult(
            query_id="additional",
            answer="Additional answer",
            sources=[{"title": "Extra Source", "content": "Extra content"}],
            confidence=0.8,
            processing_time=1.0,
            metadata={},
        )

        correction_engine.rag_system.process_query.return_value = additional_result

        with patch.object(
            correction_engine, "_synthesize_with_sources"
        ) as mock_synthesize:
            mock_synthesize.return_value = "Combined answer"

            result = await correction_engine._retrieve_more_sources(
                correction_context, correction_context.original_result
            )

            assert len(result.sources) >= len(
                correction_context.original_result.sources
            )
            assert result.metadata.get("correction") == "retrieve_more"


class TestSelfCorrectiveRAG:
    """Test cases for the main CRAG system"""

    @pytest.fixture
    def mock_rag_system(self):
        """Mock base RAG system"""
        rag = Mock()
        rag.process_query = AsyncMock()
        return rag

    @pytest.fixture
    def mock_model_config(self):
        """Mock model configuration"""
        config = Mock(spec=ModelConfigManager)
        config.region = "us-east-1"
        return config

    @pytest.fixture
    def crag_system(self, mock_rag_system, mock_model_config):
        """Create CRAG system instance"""
        return SelfCorrectiveRAG(mock_rag_system, mock_model_config)

    @pytest.fixture
    def sample_query(self):
        """Sample query for testing"""
        return RAGQuery(
            query_text="Test query",
            task_type=RAGTaskType.DOCUMENT_SEARCH,
            context={},
            max_results=5,
        )

    @pytest.mark.asyncio
    async def test_process_query_no_correction_needed(self, crag_system, sample_query):
        """Test processing when no correction is needed"""

        # Mock high-quality initial result
        high_quality_result = RAGResult(
            query_id="test",
            answer="High quality answer",
            sources=[{"title": "Good Source", "content": "Relevant content"}],
            confidence=0.9,
            processing_time=1.0,
            metadata={},
        )

        crag_system.rag_system.process_query.return_value = high_quality_result

        # Mock high-quality assessment
        with patch.object(
            crag_system.quality_assessor, "assess_quality"
        ) as mock_assess:
            mock_assess.return_value = QualityAssessment(
                query_id="test",
                timestamp=datetime.utcnow(),
                scores={metric: 0.9 for metric in QualityMetric},
                overall_score=0.9,
                confidence=0.9,
                issues_identified=[],
                suggested_corrections=[],
                reasoning="High quality response",
            )

            result = await crag_system.process_query(sample_query)

            assert isinstance(result, CRAGResult)
            assert result.correction_iterations == 0
            assert len(result.corrections_applied) == 0
            assert result.final_result == high_quality_result

    @pytest.mark.asyncio
    async def test_process_query_with_corrections(self, crag_system, sample_query):
        """Test processing when corrections are needed"""

        # Mock low-quality initial result
        low_quality_result = RAGResult(
            query_id="test",
            answer="Poor quality answer",
            sources=[{"title": "Weak Source", "content": "Irrelevant content"}],
            confidence=0.5,
            processing_time=1.0,
            metadata={},
        )

        # Mock improved result after correction
        improved_result = RAGResult(
            query_id="test",
            answer="Improved answer",
            sources=[{"title": "Better Source", "content": "More relevant content"}],
            confidence=0.8,
            processing_time=1.5,
            metadata={"correction": "applied"},
        )

        crag_system.rag_system.process_query.return_value = low_quality_result

        # Mock assessments
        initial_assessment = QualityAssessment(
            query_id="test",
            timestamp=datetime.utcnow(),
            scores={metric: 0.5 for metric in QualityMetric},
            overall_score=0.5,
            confidence=0.5,
            issues_identified=["Low quality"],
            suggested_corrections=[CorrectionAction.RETRIEVE_MORE],
            reasoning="Poor quality response",
        )

        improved_assessment = QualityAssessment(
            query_id="test",
            timestamp=datetime.utcnow(),
            scores={metric: 0.8 for metric in QualityMetric},
            overall_score=0.8,
            confidence=0.8,
            issues_identified=[],
            suggested_corrections=[],
            reasoning="Improved response",
        )

        with patch.object(
            crag_system.quality_assessor, "assess_quality"
        ) as mock_assess:
            mock_assess.side_effect = [initial_assessment, improved_assessment]

            with patch.object(
                crag_system.correction_engine, "apply_corrections"
            ) as mock_correct:
                mock_correct.return_value = improved_result

                result = await crag_system.process_query(sample_query)

                assert isinstance(result, CRAGResult)
                assert result.correction_iterations > 0
                assert len(result.corrections_applied) > 0
                assert result.improvement_score > 0

    @pytest.mark.asyncio
    async def test_batch_processing(self, crag_system):
        """Test batch processing of multiple queries"""

        queries = [
            RAGQuery(
                query_text=f"Query {i}",
                task_type=RAGTaskType.DOCUMENT_SEARCH,
                context={},
            )
            for i in range(3)
        ]

        # Mock single query processing
        with patch.object(crag_system, "process_query") as mock_process:
            mock_process.return_value = CRAGResult(
                final_result=RAGResult("test", "answer", [], 0.8, 1.0, {}),
                quality_assessment=Mock(),
                correction_iterations=1,
                corrections_applied=[],
                improvement_score=0.1,
                total_processing_time=2.0,
                confidence_evolution=[0.7, 0.8],
            )

            results = await crag_system.batch_process(queries)

            assert len(results) == 3
            assert all(isinstance(r, CRAGResult) for r in results)

    def test_performance_metrics(self, crag_system):
        """Test performance metrics calculation"""

        mock_results = [
            CRAGResult(
                final_result=Mock(),
                quality_assessment=Mock(),
                correction_iterations=i,
                corrections_applied=[CorrectionAction.RETRIEVE_MORE],
                improvement_score=0.1 * i,
                total_processing_time=2.0 + i,
                confidence_evolution=[0.7, 0.8],
            )
            for i in range(1, 4)
        ]

        metrics = crag_system.get_performance_metrics(mock_results)

        assert "total_queries" in metrics
        assert "average_improvement_score" in metrics
        assert "average_iterations" in metrics
        assert "correction_frequency" in metrics
        assert metrics["total_queries"] == 3


class TestCRAGIntegration:
    """Test cases for CRAG integration components"""

    @pytest.fixture
    def mock_crag_system(self):
        """Mock CRAG system"""
        crag = Mock()
        crag.process_query = AsyncMock()
        return crag

    @pytest.fixture
    def mock_document_service(self):
        """Mock document service"""
        service = Mock()
        service.get_document = AsyncMock()
        return service

    @pytest.fixture
    def mock_metrics_service(self):
        """Mock metrics service"""
        service = Mock()
        service.record_metric = AsyncMock()
        service.get_metrics = AsyncMock()
        return service

    @pytest.fixture
    def crag_processor(
        self, mock_crag_system, mock_document_service, mock_metrics_service
    ):
        """Create CRAG document processor"""
        config = CRAGConfiguration()
        return CRAGDocumentProcessor(
            mock_crag_system, mock_document_service, mock_metrics_service, config
        )

    @pytest.mark.asyncio
    async def test_process_document_query(self, crag_processor):
        """Test document query processing"""

        mock_result = CRAGResult(
            final_result=RAGResult("test", "answer", [], 0.8, 1.0, {}),
            quality_assessment=Mock(),
            correction_iterations=1,
            corrections_applied=[],
            improvement_score=0.1,
            total_processing_time=2.0,
            confidence_evolution=[0.7, 0.8],
        )

        crag_processor.crag_system.process_query.return_value = mock_result

        result = await crag_processor.process_document_query(
            "Test query", {"document_type": "api_docs"}
        )

        assert isinstance(result, CRAGResult)
        crag_processor.crag_system.process_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_document_accuracy(self, crag_processor):
        """Test document accuracy validation"""

        # Mock document
        mock_document = {
            "id": "doc-123",
            "title": "Test Document",
            "content": "Document content",
            "type": "guide",
            "updated_at": datetime.utcnow(),
        }

        crag_processor.document_service.get_document.return_value = mock_document

        mock_result = CRAGResult(
            final_result=RAGResult("test", "validation result", [], 0.8, 1.0, {}),
            quality_assessment=Mock(),
            correction_iterations=0,
            corrections_applied=[],
            improvement_score=0.0,
            total_processing_time=1.0,
            confidence_evolution=[0.8],
        )

        crag_processor.crag_system.process_query.return_value = mock_result

        result = await crag_processor.validate_document_accuracy("doc-123")

        assert isinstance(result, CRAGResult)
        crag_processor.document_service.get_document.assert_called_once_with("doc-123")


# Performance benchmarks
class TestCRAGPerformance:
    """Performance tests for CRAG system"""

    @pytest.mark.asyncio
    async def test_processing_time_benchmark(self):
        """Benchmark CRAG processing time"""

        # Mock components for performance testing
        mock_rag = Mock()
        mock_rag.process_query = AsyncMock()
        mock_rag.process_query.return_value = RAGResult(
            "test", "answer", [], 0.8, 0.1, {}  # Fast mock response
        )

        mock_config = Mock()
        crag = SelfCorrectiveRAG(mock_rag, mock_config)

        # Mock high-quality assessment to avoid corrections
        with patch.object(crag.quality_assessor, "assess_quality") as mock_assess:
            mock_assess.return_value = QualityAssessment(
                query_id="test",
                timestamp=datetime.utcnow(),
                scores={metric: 0.9 for metric in QualityMetric},
                overall_score=0.9,
                confidence=0.9,
                issues_identified=[],
                suggested_corrections=[],
                reasoning="High quality",
            )

            start_time = datetime.utcnow()

            query = RAGQuery(
                query_text="Benchmark query",
                task_type=RAGTaskType.DOCUMENT_SEARCH,
                context={},
            )

            result = await crag.process_query(query)

            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()

            # Should process quickly without corrections
            assert processing_time < 1.0
            assert isinstance(result, CRAGResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
