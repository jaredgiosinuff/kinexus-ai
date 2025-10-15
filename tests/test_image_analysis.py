#!/usr/bin/env python3
"""
Test suite for Image Analysis Framework
"""
import asyncio
import base64
import io
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
from PIL import Image, ImageDraw

# Import image analysis components
from src.agents.image_analysis_framework import (
    AnalysisTask,
    ContentValidator,
    ImageAnalysisEngine,
    ImageAnalysisRequest,
    ImageAnalysisResult,
    ImagePreprocessor,
    ImageType,
    TextExtractor,
    VisualQualityAnalyzer,
)
from src.agents.image_analysis_integration import (
    CRAGImageEnhancer,
    DocumentationImageValidator,
    ImageAnalysisIntegrationManager,
)
from src.config.model_config import ModelConfigManager


class TestImagePreprocessor:
    """Test cases for image preprocessing"""

    @pytest.fixture
    def preprocessor(self):
        """Create image preprocessor instance"""
        return ImagePreprocessor()

    @pytest.fixture
    def sample_image_data(self):
        """Create sample image data"""
        img = Image.new("RGB", (100, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test", fill="black")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    @pytest.fixture
    def sample_image_base64(self, sample_image_data):
        """Create base64 encoded image"""
        return base64.b64encode(sample_image_data).decode()

    @pytest.mark.asyncio
    async def test_preprocess_image_bytes(self, preprocessor, sample_image_data):
        """Test preprocessing image from bytes"""

        image, metadata = await preprocessor.preprocess_image(sample_image_data)

        assert isinstance(image, Image.Image)
        assert image.mode == "RGB"
        assert "original_size" in metadata
        assert "processed_size" in metadata
        assert "enhancement_applied" in metadata

    @pytest.mark.asyncio
    async def test_preprocess_image_base64(self, preprocessor, sample_image_base64):
        """Test preprocessing image from base64"""

        image, metadata = await preprocessor.preprocess_image(sample_image_base64)

        assert isinstance(image, Image.Image)
        assert image.mode == "RGB"
        assert metadata["original_size"] == (100, 100)

    @pytest.mark.asyncio
    async def test_detect_optimal_enhancement(self, preprocessor):
        """Test optimal enhancement detection"""

        # Create different types of test images

        # Dark image (should brighten)
        dark_img = Image.new("RGB", (100, 100), color=(20, 20, 20))
        enhancement = await preprocessor._detect_optimal_enhancement(dark_img)
        assert enhancement == "brighten"

        # Low contrast image
        low_contrast_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        enhancement = await preprocessor._detect_optimal_enhancement(low_contrast_img)
        assert enhancement == "enhance_contrast"

    def test_blur_detection(self, preprocessor):
        """Test blur detection"""

        # Create sharp image
        sharp_img = Image.new("RGB", (100, 100), color="white")
        draw = ImageDraw.Draw(sharp_img)
        draw.rectangle([10, 10, 90, 90], outline="black", width=2)

        is_blurry = preprocessor._is_blurry(np.array(sharp_img))
        assert not is_blurry  # Sharp image should not be detected as blurry

    def test_noise_detection(self, preprocessor):
        """Test noise detection"""

        # Create clean image
        clean_img = Image.new("RGB", (100, 100), color="white")
        has_noise = preprocessor._has_noise(np.array(clean_img))
        assert not has_noise  # Clean image should not have noise


class TestTextExtractor:
    """Test cases for text extraction"""

    @pytest.fixture
    def text_extractor(self):
        """Create text extractor instance"""
        return TextExtractor()

    @pytest.fixture
    def text_image(self):
        """Create image with text"""
        img = Image.new("RGB", (200, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "Hello World", fill="black")
        return img

    @pytest.mark.asyncio
    async def test_extract_text_basic(self, text_extractor, text_image):
        """Test basic text extraction"""

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = "Hello World"

            with patch("pytesseract.image_to_data") as mock_data:
                mock_data.return_value = {
                    "conf": ["85"],
                    "text": ["Hello", "World"],
                    "left": [10, 50],
                    "top": [30, 30],
                    "width": [35, 40],
                    "height": [15, 15],
                    "level": [5, 5],
                }

                result = await text_extractor.extract_text(text_image)

                assert result.extracted_text == "Hello World"
                assert result.confidence > 0
                assert result.language == "eng"
                assert len(result.bounding_boxes) > 0

    @pytest.mark.asyncio
    async def test_extract_text_empty_image(self, text_extractor):
        """Test text extraction from empty image"""

        empty_img = Image.new("RGB", (100, 100), color="white")

        with patch("pytesseract.image_to_string") as mock_ocr:
            mock_ocr.return_value = ""

            with patch("pytesseract.image_to_data") as mock_data:
                mock_data.return_value = {
                    "conf": [],
                    "text": [],
                    "left": [],
                    "top": [],
                    "width": [],
                    "height": [],
                    "level": [],
                }

                result = await text_extractor.extract_text(empty_img)

                assert result.extracted_text == ""
                assert result.confidence == 0.0

    def test_extract_bounding_boxes(self, text_extractor):
        """Test bounding box extraction"""

        ocr_data = {
            "conf": ["85", "90"],
            "text": ["Hello", "World"],
            "left": [10, 50],
            "top": [30, 30],
            "width": [35, 40],
            "height": [15, 15],
            "level": [5, 5],
        }

        boxes = text_extractor._extract_bounding_boxes(ocr_data)

        assert len(boxes) == 2
        assert boxes[0]["text"] == "Hello"
        assert boxes[0]["confidence"] == 85
        assert boxes[0]["bbox"]["x"] == 10


class TestVisualQualityAnalyzer:
    """Test cases for visual quality analysis"""

    @pytest.fixture
    def mock_model_config(self):
        """Mock model configuration"""
        return Mock(spec=ModelConfigManager)

    @pytest.fixture
    def quality_analyzer(self, mock_model_config):
        """Create quality analyzer instance"""
        return VisualQualityAnalyzer(mock_model_config)

    @pytest.fixture
    def high_quality_image(self):
        """Create high quality test image"""
        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)

        # Add high contrast text
        draw.text((50, 50), "High Quality Text", fill="black")

        # Add some shapes for content
        draw.rectangle([100, 100, 200, 200], outline="black", width=2)
        draw.ellipse([250, 100, 350, 200], outline="blue", width=2)

        return img

    @pytest.fixture
    def low_quality_image(self):
        """Create low quality test image"""
        img = Image.new("RGB", (200, 150), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)

        # Add low contrast text
        draw.text((10, 10), "Low Quality", fill=(180, 180, 180))

        return img

    @pytest.mark.asyncio
    async def test_assess_quality_high_quality(
        self, quality_analyzer, high_quality_image
    ):
        """Test quality assessment of high quality image"""

        result = await quality_analyzer.assess_quality(
            high_quality_image, ImageType.DOCUMENTATION_PAGE
        )

        assert isinstance(result.overall_score, float)
        assert 0.0 <= result.overall_score <= 1.0
        assert result.clarity_score > 0
        assert result.readability_score > 0
        assert result.completeness_score > 0
        assert result.accessibility_score > 0

    @pytest.mark.asyncio
    async def test_assess_clarity(self, quality_analyzer, high_quality_image):
        """Test clarity assessment"""

        clarity_score = await quality_analyzer._assess_clarity(high_quality_image)

        assert isinstance(clarity_score, float)
        assert 0.0 <= clarity_score <= 1.0

    @pytest.mark.asyncio
    async def test_assess_readability(self, quality_analyzer, high_quality_image):
        """Test readability assessment"""

        readability_score = await quality_analyzer._assess_readability(
            high_quality_image
        )

        assert isinstance(readability_score, float)
        assert 0.0 <= readability_score <= 1.0

    @pytest.mark.asyncio
    async def test_assess_accessibility(self, quality_analyzer, high_quality_image):
        """Test accessibility assessment"""

        accessibility_score = await quality_analyzer._assess_accessibility(
            high_quality_image
        )

        assert isinstance(accessibility_score, float)
        assert 0.0 <= accessibility_score <= 1.0


class TestContentValidator:
    """Test cases for content validation"""

    @pytest.fixture
    def mock_model_config(self):
        """Mock model configuration"""
        return Mock(spec=ModelConfigManager)

    @pytest.fixture
    def content_validator(self, mock_model_config):
        """Create content validator instance"""
        return ContentValidator(mock_model_config)

    @pytest.fixture
    def test_image(self):
        """Create test image with specific content"""
        img = Image.new("RGB", (300, 200), color="white")
        draw = ImageDraw.Draw(img)

        # Add text content
        draw.text((10, 10), "API Documentation", fill="black")
        draw.text((10, 40), "Authentication Required", fill="black")

        # Add visual elements
        draw.rectangle([10, 70, 100, 120], outline="black", width=2)

        return img

    @pytest.mark.asyncio
    async def test_validate_content_basic(self, content_validator, test_image):
        """Test basic content validation"""

        expected_content = {
            "required_text": ["API", "Authentication"],
            "visual_elements": ["rectangle", "text"],
        }

        extracted_text = "API Documentation Authentication Required"

        with patch.object(content_validator, "_call_vision_model") as mock_vision:
            mock_vision.return_value = (["rectangle"], [])

            result = await content_validator.validate_content(
                test_image, expected_content, extracted_text
            )

            assert isinstance(result.is_valid, bool)
            assert isinstance(result.validation_score, float)
            assert isinstance(result.content_matches, list)

    @pytest.mark.asyncio
    async def test_validate_text_content(self, content_validator):
        """Test text content validation"""

        extracted_text = "This is API documentation with authentication examples"
        required_text = ["API", "authentication", "documentation"]

        result = await content_validator._validate_text_content(
            extracted_text, required_text
        )

        assert result["score"] == 1.0  # All required text found
        assert len(result["matches"]) == 3
        assert len(result["missing"]) == 0


class TestImageAnalysisEngine:
    """Test cases for the main image analysis engine"""

    @pytest.fixture
    def mock_model_config(self):
        """Mock model configuration"""
        return Mock(spec=ModelConfigManager)

    @pytest.fixture
    def analysis_engine(self, mock_model_config):
        """Create analysis engine instance"""
        return ImageAnalysisEngine(mock_model_config)

    @pytest.fixture
    def sample_request(self):
        """Create sample analysis request"""
        img = Image.new("RGB", (200, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), "Test Image", fill="black")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_data = buffer.getvalue()

        return ImageAnalysisRequest(
            image_data=image_data,
            image_type=ImageType.DOCUMENTATION_PAGE,
            analysis_tasks=[
                AnalysisTask.TEXT_EXTRACTION,
                AnalysisTask.QUALITY_ASSESSMENT,
            ],
            context={"test": True},
        )

    @pytest.mark.asyncio
    async def test_analyze_image_basic(self, analysis_engine, sample_request):
        """Test basic image analysis"""

        with patch.object(analysis_engine.text_extractor, "extract_text") as mock_text:
            mock_text.return_value = Mock(
                extracted_text="Test Image",
                confidence=0.8,
                bounding_boxes=[],
                language="eng",
                text_blocks=[],
            )

            with patch.object(
                analysis_engine.quality_analyzer, "assess_quality"
            ) as mock_quality:
                mock_quality.return_value = Mock(
                    overall_score=0.8,
                    clarity_score=0.8,
                    readability_score=0.8,
                    completeness_score=0.8,
                    accessibility_score=0.8,
                    issues_detected=[],
                    recommendations=[],
                )

                result = await analysis_engine.analyze_image(sample_request)

                assert isinstance(result, ImageAnalysisResult)
                assert result.image_type == ImageType.DOCUMENTATION_PAGE
                assert result.text_extraction is not None
                assert result.quality_assessment is not None
                assert result.processing_time > 0
                assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_image_error_handling(self, analysis_engine, sample_request):
        """Test error handling in image analysis"""

        with patch.object(
            analysis_engine.preprocessor, "preprocess_image"
        ) as mock_preprocess:
            mock_preprocess.side_effect = Exception("Processing failed")

            result = await analysis_engine.analyze_image(sample_request)

            assert isinstance(result, ImageAnalysisResult)
            assert result.confidence == 0.0
            assert "error" in result.metadata

    @pytest.mark.asyncio
    async def test_batch_analyze_images(self, analysis_engine):
        """Test batch image analysis"""

        # Create multiple sample requests
        requests = []
        for i in range(3):
            img = Image.new("RGB", (100, 100), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")

            request = ImageAnalysisRequest(
                image_data=buffer.getvalue(),
                image_type=ImageType.DOCUMENTATION_PAGE,
                analysis_tasks=[AnalysisTask.QUALITY_ASSESSMENT],
            )
            requests.append(request)

        with patch.object(analysis_engine, "analyze_image") as mock_analyze:
            mock_analyze.return_value = Mock(
                spec=ImageAnalysisResult, confidence=0.8, processing_time=1.0
            )

            results = await analysis_engine.batch_analyze_images(requests)

            assert len(results) == 3
            assert mock_analyze.call_count == 3


class TestImageAnalysisIntegration:
    """Test cases for integration components"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all dependencies"""
        return {
            "model_config": Mock(spec=ModelConfigManager),
            "document_service": Mock(),
            "metrics_service": Mock(),
            "crag_system": Mock(),
        }

    @pytest.fixture
    def integration_manager(self, mock_dependencies):
        """Create integration manager instance"""
        return ImageAnalysisIntegrationManager(
            mock_dependencies["model_config"],
            mock_dependencies["document_service"],
            mock_dependencies["metrics_service"],
            mock_dependencies["crag_system"],
        )

    @pytest.mark.asyncio
    async def test_health_check(self, integration_manager):
        """Test image analysis health check"""

        with patch.object(
            integration_manager.image_analyzer, "analyze_image"
        ) as mock_analyze:
            mock_analyze.return_value = Mock(confidence=0.8, processing_time=1.0)

            health = await integration_manager.get_image_analysis_health_check()

            assert health["status"] == "healthy"
            assert health["image_analysis_working"] is True
            assert "test_processing_time" in health

    @pytest.mark.asyncio
    async def test_health_check_failure(self, integration_manager):
        """Test health check failure handling"""

        with patch.object(
            integration_manager.image_analyzer, "analyze_image"
        ) as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")

            health = await integration_manager.get_image_analysis_health_check()

            assert health["status"] == "unhealthy"
            assert health["image_analysis_working"] is False
            assert "error" in health


class TestDocumentationImageValidator:
    """Test cases for documentation image validation"""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock dependencies for validator"""
        return {
            "image_analyzer": Mock(),
            "document_service": Mock(),
            "metrics_service": Mock(),
        }

    @pytest.fixture
    def image_validator(self, mock_dependencies):
        """Create image validator instance"""
        return DocumentationImageValidator(
            mock_dependencies["image_analyzer"],
            mock_dependencies["document_service"],
            mock_dependencies["metrics_service"],
        )

    def test_extract_image_references(self, image_validator):
        """Test extraction of image references from document"""

        document = {
            "content": """
            This is documentation with images:
            ![Screenshot](path/to/screenshot.png)
            ![Diagram](https://example.com/diagram.jpg)
            <img src="local/image.gif" alt="Example">
            """
        }

        images = image_validator._extract_image_references(document)

        assert len(images) == 3
        assert images[0]["url"] == "path/to/screenshot.png"
        assert images[0]["alt_text"] == "Screenshot"
        assert images[1]["url"] == "https://example.com/diagram.jpg"

    def test_classify_image_from_context(self, image_validator):
        """Test image type classification"""

        # Test screenshot classification
        img_type = image_validator._classify_image_from_context(
            "Screenshot of login", ""
        )
        assert img_type == "screenshot"

        # Test diagram classification
        img_type = image_validator._classify_image_from_context("Flow diagram", "")
        assert img_type == "diagram"

        # Test architecture classification
        img_type = image_validator._classify_image_from_context(
            "System architecture", ""
        )
        assert img_type == "architecture"


class TestCRAGImageEnhancer:
    """Test cases for CRAG image enhancement"""

    @pytest.fixture
    def mock_crag_system(self):
        """Mock CRAG system"""
        return Mock()

    @pytest.fixture
    def mock_image_analyzer(self):
        """Mock image analyzer"""
        return Mock()

    @pytest.fixture
    def crag_enhancer(self, mock_crag_system, mock_image_analyzer):
        """Create CRAG image enhancer"""
        return CRAGImageEnhancer(mock_crag_system, mock_image_analyzer)

    @pytest.mark.asyncio
    async def test_process_query_with_images(self, crag_enhancer):
        """Test processing query with image enhancement"""

        # Mock CRAG result
        mock_crag_result = Mock()
        mock_crag_result.final_result.answer = "Original answer"
        mock_crag_result.final_result.confidence = 0.8
        crag_enhancer.crag_system.process_query.return_value = mock_crag_result

        # Mock image analysis results
        mock_image_result = Mock()
        mock_image_result.confidence = 0.7
        mock_image_result.text_extraction.extracted_text = "Image text content"
        crag_enhancer.image_analyzer.batch_analyze_images.return_value = [
            mock_image_result
        ]

        # Mock enhanced response generation
        with patch.object(
            crag_enhancer, "_enhance_with_image_insights"
        ) as mock_enhance:
            mock_enhance.return_value = "Enhanced answer with image insights"

            from src.agents.agentic_rag_system import RAGQuery, RAGTaskType

            query = RAGQuery(
                query_text="Test query",
                task_type=RAGTaskType.DOCUMENT_SEARCH,
                context={},
            )

            image_context = [{"data": b"fake_image_data", "type": "screenshot"}]

            result = await crag_enhancer.process_query_with_images(query, image_context)

            assert "crag_result" in result
            assert "image_analysis" in result
            assert "enhanced_response" in result
            assert "combined_confidence" in result


# Performance and stress tests
class TestImageAnalysisPerformance:
    """Performance tests for image analysis system"""

    @pytest.fixture
    def mock_model_config(self):
        """Mock model configuration"""
        return Mock(spec=ModelConfigManager)

    @pytest.fixture
    def analysis_engine(self, mock_model_config):
        """Create analysis engine for performance testing"""
        return ImageAnalysisEngine(mock_model_config)

    @pytest.mark.asyncio
    async def test_performance_single_image(self, analysis_engine):
        """Test performance of single image analysis"""

        # Create test image
        img = Image.new("RGB", (800, 600), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((100, 100), "Performance Test Image", fill="black")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        request = ImageAnalysisRequest(
            image_data=buffer.getvalue(),
            image_type=ImageType.DOCUMENTATION_PAGE,
            analysis_tasks=[AnalysisTask.QUALITY_ASSESSMENT],
        )

        # Mock fast processing
        with patch.object(
            analysis_engine, "_calculate_overall_confidence", return_value=0.8
        ):
            with patch.object(
                analysis_engine.quality_analyzer, "assess_quality"
            ) as mock_quality:
                mock_quality.return_value = Mock(overall_score=0.8)

                start_time = datetime.utcnow()
                result = await analysis_engine.analyze_image(request)
                end_time = datetime.utcnow()

                processing_time = (end_time - start_time).total_seconds()

                # Should process quickly with mocked components
                assert processing_time < 5.0
                assert isinstance(result, ImageAnalysisResult)

    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, analysis_engine):
        """Test concurrent analysis of multiple images"""

        # Create multiple requests
        requests = []
        for i in range(5):
            img = Image.new("RGB", (200, 200), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")

            request = ImageAnalysisRequest(
                image_data=buffer.getvalue(),
                image_type=ImageType.DOCUMENTATION_PAGE,
                analysis_tasks=[AnalysisTask.QUALITY_ASSESSMENT],
            )
            requests.append(request)

        # Mock analysis for performance
        with patch.object(analysis_engine, "analyze_image") as mock_analyze:
            mock_analyze.return_value = Mock(confidence=0.8, processing_time=0.1)

            start_time = datetime.utcnow()
            results = await analysis_engine.batch_analyze_images(requests)
            end_time = datetime.utcnow()

            total_time = (end_time - start_time).total_seconds()

            assert len(results) == 5
            # Concurrent processing should be faster than sequential
            assert total_time < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
