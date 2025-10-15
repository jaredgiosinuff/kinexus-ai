#!/usr/bin/env python3
"""
Image Analysis Integration for Kinexus AI
Integrates image analysis with document management, CRAG, and webhook processing
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

from ..config.model_config import ModelConfigManager
from ..core.services.document_service import DocumentService
from ..core.services.metrics_service import MetricsService

# Import image analysis components
from .image_analysis_framework import (
    AnalysisTask,
    ImageAnalysisEngine,
    ImageAnalysisRequest,
    ImageAnalysisResult,
    ImageType,
)

# Import existing systems
from .self_corrective_rag import RAGQuery, SelfCorrectiveRAG

logger = logging.getLogger(__name__)


@dataclass
class ImageDocumentationContext:
    """Context for image-based documentation analysis"""

    document_id: str
    section_id: Optional[str] = None
    image_purpose: str = "documentation"  # documentation, example, diagram, etc.
    related_content: Optional[str] = None
    validation_requirements: Dict[str, Any] = field(default_factory=dict)
    quality_standards: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageAnalysisReport:
    """Comprehensive report of image analysis for documentation"""

    document_id: str
    total_images_analyzed: int
    overall_quality_score: float
    accessibility_compliance: float
    content_accuracy: float
    recommendations: List[str]
    issues_found: List[Dict[str, Any]]
    processing_time: float
    analysis_timestamp: datetime


class CRAGImageEnhancer:
    """Enhances CRAG system with image analysis capabilities"""

    def __init__(
        self, crag_system: SelfCorrectiveRAG, image_analyzer: ImageAnalysisEngine
    ):
        self.crag_system = crag_system
        self.image_analyzer = image_analyzer

    async def process_query_with_images(
        self, query: RAGQuery, image_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process RAG query enhanced with image analysis"""

        # First, get standard CRAG response
        crag_result = await self.crag_system.process_query(query)

        # Analyze relevant images
        image_results = []
        if image_context:
            image_analysis_requests = []

            for img_ctx in image_context:
                request = ImageAnalysisRequest(
                    image_data=img_ctx["data"],
                    image_type=ImageType(img_ctx.get("type", "documentation_page")),
                    analysis_tasks=[
                        AnalysisTask.TEXT_EXTRACTION,
                        AnalysisTask.CONTENT_VALIDATION,
                        AnalysisTask.QUALITY_ASSESSMENT,
                    ],
                    context={
                        "query_text": query.query_text,
                        "expected_content": img_ctx.get("expected_content", {}),
                        "validation_criteria": img_ctx.get("validation_criteria", {}),
                    },
                )
                image_analysis_requests.append(request)

            # Batch analyze images
            image_results = await self.image_analyzer.batch_analyze_images(
                image_analysis_requests
            )

        # Enhance CRAG result with image insights
        enhanced_result = await self._enhance_with_image_insights(
            crag_result, image_results
        )

        return {
            "crag_result": crag_result,
            "image_analysis": image_results,
            "enhanced_response": enhanced_result,
            "combined_confidence": self._calculate_combined_confidence(
                crag_result, image_results
            ),
        }

    async def _enhance_with_image_insights(self, crag_result, image_results) -> str:
        """Enhance CRAG response with insights from image analysis"""

        if not image_results:
            return crag_result.final_result.answer

        # Extract key insights from images
        image_insights = []
        for result in image_results:
            insights = []

            if result.text_extraction and result.text_extraction.extracted_text:
                insights.append(
                    f"Image contains text: {result.text_extraction.extracted_text[:100]}..."
                )

            if result.quality_assessment:
                if result.quality_assessment.overall_score < 0.7:
                    insights.append(
                        f"Image quality issues detected: {', '.join(result.quality_assessment.issues_detected)}"
                    )

            if result.content_validation and not result.content_validation.is_valid:
                insights.append(
                    f"Content validation failed: {', '.join(result.content_validation.missing_elements)}"
                )

            if insights:
                image_insights.extend(insights)

        # Generate enhanced response using Claude
        if image_insights:
            enhancement_prompt = f"""
            Original response: {crag_result.final_result.answer}

            Additional insights from image analysis:
            {chr(10).join(f"- {insight}" for insight in image_insights)}

            Please enhance the original response by incorporating relevant insights from the image analysis.
            Maintain the accuracy and structure of the original response while adding valuable visual context.
            """

            try:
                enhanced_response = await self._call_bedrock_for_enhancement(
                    enhancement_prompt
                )
                return enhanced_response
            except Exception as e:
                logger.error(f"Failed to enhance response with image insights: {e}")
                return crag_result.final_result.answer
        else:
            return crag_result.final_result.answer

    def _calculate_combined_confidence(self, crag_result, image_results) -> float:
        """Calculate combined confidence from CRAG and image analysis"""

        crag_confidence = crag_result.final_result.confidence

        if image_results:
            image_confidences = [
                r.confidence for r in image_results if r.confidence > 0
            ]
            avg_image_confidence = (
                sum(image_confidences) / len(image_confidences)
                if image_confidences
                else 0.5
            )

            # Weight CRAG higher as it's the primary response
            combined_confidence = crag_confidence * 0.7 + avg_image_confidence * 0.3
        else:
            combined_confidence = crag_confidence

        return combined_confidence

    async def _call_bedrock_for_enhancement(self, prompt: str) -> str:
        """Call Bedrock to enhance response with image insights"""

        bedrock = boto3.client("bedrock-runtime")
        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = bedrock.invoke_model(modelId=model_id, body=json.dumps(body))

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]


class DocumentationImageValidator:
    """Validates documentation images for quality and compliance"""

    def __init__(
        self,
        image_analyzer: ImageAnalysisEngine,
        document_service: DocumentService,
        metrics_service: MetricsService,
    ):
        self.image_analyzer = image_analyzer
        self.document_service = document_service
        self.metrics_service = metrics_service

    async def validate_document_images(
        self, document_id: str, validation_config: Dict[str, Any] = None
    ) -> ImageAnalysisReport:
        """Validate all images in a document"""

        start_time = datetime.utcnow()

        # Get document and extract image references
        document = await self.document_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        image_references = self._extract_image_references(document)

        if not image_references:
            return ImageAnalysisReport(
                document_id=document_id,
                total_images_analyzed=0,
                overall_quality_score=1.0,
                accessibility_compliance=1.0,
                content_accuracy=1.0,
                recommendations=[],
                issues_found=[],
                processing_time=0.0,
                analysis_timestamp=start_time,
            )

        # Create validation requests
        validation_requests = []
        for img_ref in image_references:
            request = ImageAnalysisRequest(
                image_data=await self._load_image_data(img_ref["url"]),
                image_type=self._determine_image_type(img_ref),
                analysis_tasks=[
                    AnalysisTask.QUALITY_ASSESSMENT,
                    AnalysisTask.ACCESSIBILITY_CHECK,
                    AnalysisTask.CONTENT_VALIDATION,
                    AnalysisTask.ERROR_DETECTION,
                ],
                context={
                    "document_id": document_id,
                    "image_context": img_ref.get("context", ""),
                    "validation_config": validation_config or {},
                    "expected_content": self._extract_expected_content(
                        img_ref, document
                    ),
                },
            )
            validation_requests.append(request)

        # Perform batch analysis
        analysis_results = await self.image_analyzer.batch_analyze_images(
            validation_requests
        )

        # Generate comprehensive report
        report = await self._generate_validation_report(
            document_id, analysis_results, start_time
        )

        # Record metrics
        await self._record_validation_metrics(document_id, report)

        return report

    def _extract_image_references(
        self, document: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract image references from document content"""

        content = document.get("content", "")
        images = []

        # Simple markdown image extraction (![alt](url))
        import re

        markdown_images = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", content)

        for alt_text, url in markdown_images:
            images.append(
                {
                    "url": url,
                    "alt_text": alt_text,
                    "context": self._extract_surrounding_context(content, url),
                    "type": self._classify_image_from_context(alt_text, content),
                }
            )

        # HTML image extraction
        html_images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', content)
        for url in html_images:
            if not any(img["url"] == url for img in images):
                images.append(
                    {
                        "url": url,
                        "alt_text": "",
                        "context": self._extract_surrounding_context(content, url),
                        "type": "unknown",
                    }
                )

        return images

    def _extract_surrounding_context(self, content: str, image_url: str) -> str:
        """Extract text context around image reference"""

        # Find image position and extract surrounding text
        import re

        pattern = re.escape(image_url)
        match = re.search(pattern, content)

        if match:
            start = max(0, match.start() - 200)
            end = min(len(content), match.end() + 200)
            context = content[start:end]

            # Clean up context
            context = re.sub(r"!\[[^\]]*\]\([^)]+\)", "[IMAGE]", context)
            context = re.sub(r"<[^>]+>", "", context)
            return context.strip()

        return ""

    def _classify_image_from_context(self, alt_text: str, context: str) -> str:
        """Classify image type from alt text and context"""

        alt_lower = alt_text.lower()
        _context_lower = context.lower()

        if any(word in alt_lower for word in ["screenshot", "screen shot", "capture"]):
            return "screenshot"
        elif any(word in alt_lower for word in ["diagram", "flowchart", "flow chart"]):
            return "diagram"
        elif any(word in alt_lower for word in ["architecture", "system design"]):
            return "architecture"
        elif any(word in alt_lower for word in ["code", "snippet", "example"]):
            return "code_snippet"
        elif any(word in alt_lower for word in ["chart", "graph", "plot"]):
            return "chart_graph"
        elif any(
            word in alt_lower for word in ["mockup", "wireframe", "ui", "interface"]
        ):
            return "ui_mockup"
        else:
            return "documentation_page"

    def _determine_image_type(self, img_ref: Dict[str, Any]) -> ImageType:
        """Determine ImageType enum from image reference"""

        type_mapping = {
            "screenshot": ImageType.SCREENSHOT,
            "diagram": ImageType.DIAGRAM,
            "flowchart": ImageType.FLOWCHART,
            "architecture": ImageType.ARCHITECTURE,
            "code_snippet": ImageType.CODE_SNIPPET,
            "chart_graph": ImageType.CHART_GRAPH,
            "ui_mockup": ImageType.UI_MOCKUP,
            "documentation_page": ImageType.DOCUMENTATION_PAGE,
            "unknown": ImageType.UNKNOWN,
        }

        return type_mapping.get(img_ref.get("type", "unknown"), ImageType.UNKNOWN)

    def _extract_expected_content(
        self, img_ref: Dict[str, Any], document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract expected content criteria from image context"""

        expected_content = {}

        # Extract from alt text and context
        _alt_text = img_ref.get("alt_text", "")
        context = img_ref.get("context", "")

        # Look for specific terms that indicate expected content
        if "api" in context.lower():
            expected_content["required_text"] = [
                "API",
                "endpoint",
                "request",
                "response",
            ]

        if "authentication" in context.lower():
            expected_content["required_text"] = ["auth", "token", "login", "credential"]

        if "installation" in context.lower():
            expected_content["required_text"] = ["install", "setup", "configure"]

        # Visual elements based on image type
        img_type = img_ref.get("type", "unknown")
        if img_type == "screenshot":
            expected_content["visual_elements"] = ["window", "button", "interface"]
        elif img_type == "diagram":
            expected_content["visual_elements"] = ["shapes", "arrows", "labels"]
        elif img_type == "code_snippet":
            expected_content["visual_elements"] = ["code", "syntax highlighting"]

        return expected_content

    async def _load_image_data(self, image_url: str) -> bytes:
        """Load image data from URL"""

        # Handle different URL types
        if image_url.startswith("data:"):
            # Data URL
            import base64

            header, data = image_url.split(",", 1)
            return base64.b64decode(data)

        elif image_url.startswith("http"):
            # HTTP URL
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    return await response.read()

        elif image_url.startswith("/") or "://" not in image_url:
            # Local file path
            try:
                with open(image_url, "rb") as f:
                    return f.read()
            except FileNotFoundError:
                logger.warning(f"Image file not found: {image_url}")
                # Return placeholder image data
                return b""

        else:
            logger.warning(f"Unsupported image URL format: {image_url}")
            return b""

    async def _generate_validation_report(
        self,
        document_id: str,
        analysis_results: List[ImageAnalysisResult],
        start_time: datetime,
    ) -> ImageAnalysisReport:
        """Generate comprehensive validation report"""

        total_images = len(analysis_results)
        quality_scores = []
        accessibility_scores = []
        content_scores = []
        all_issues = []
        recommendations = set()

        for result in analysis_results:
            # Quality assessment
            if result.quality_assessment:
                quality_scores.append(result.quality_assessment.overall_score)
                all_issues.extend(
                    [
                        {
                            "type": "quality",
                            "issue": issue,
                            "image_id": result.request_id,
                        }
                        for issue in result.quality_assessment.issues_detected
                    ]
                )
                recommendations.update(result.quality_assessment.recommendations)

            # Accessibility
            if result.accessibility_results:
                accessibility_scores.append(
                    result.accessibility_results.get("overall_accessibility_score", 0.5)
                )

            # Content validation
            if result.content_validation:
                content_scores.append(result.content_validation.validation_score)
                if not result.content_validation.is_valid:
                    all_issues.append(
                        {
                            "type": "content",
                            "issue": f"Missing elements: {', '.join(result.content_validation.missing_elements)}",
                            "image_id": result.request_id,
                        }
                    )

            # Error detection
            if result.error_detection:
                errors = result.error_detection.get("errors", [])
                warnings = result.error_detection.get("warnings", [])

                for error in errors:
                    all_issues.append(
                        {"type": "error", "issue": error, "image_id": result.request_id}
                    )

                for warning in warnings:
                    all_issues.append(
                        {
                            "type": "warning",
                            "issue": warning,
                            "image_id": result.request_id,
                        }
                    )

        # Calculate aggregate scores
        overall_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 1.0
        )
        accessibility_compliance = (
            sum(accessibility_scores) / len(accessibility_scores)
            if accessibility_scores
            else 1.0
        )
        content_accuracy = (
            sum(content_scores) / len(content_scores) if content_scores else 1.0
        )

        # Generate recommendations based on common issues
        if overall_quality < 0.7:
            recommendations.add("Consider improving image resolution and clarity")

        if accessibility_compliance < 0.8:
            recommendations.add(
                "Enhance accessibility by improving color contrast and text size"
            )

        if content_accuracy < 0.8:
            recommendations.add(
                "Verify that images contain all necessary documentation elements"
            )

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        return ImageAnalysisReport(
            document_id=document_id,
            total_images_analyzed=total_images,
            overall_quality_score=overall_quality,
            accessibility_compliance=accessibility_compliance,
            content_accuracy=content_accuracy,
            recommendations=list(recommendations),
            issues_found=all_issues,
            processing_time=processing_time,
            analysis_timestamp=start_time,
        )

    async def _record_validation_metrics(
        self, document_id: str, report: ImageAnalysisReport
    ):
        """Record validation metrics for monitoring"""

        metrics_data = {
            "document_id": document_id,
            "total_images": report.total_images_analyzed,
            "quality_score": report.overall_quality_score,
            "accessibility_score": report.accessibility_compliance,
            "content_accuracy": report.content_accuracy,
            "issues_count": len(report.issues_found),
            "processing_time": report.processing_time,
            "timestamp": report.analysis_timestamp.isoformat(),
        }

        await self.metrics_service.record_metric(
            metric_name="image_validation",
            value=report.overall_quality_score,
            metadata=metrics_data,
        )


class WebhookImageProcessor:
    """Processes webhook events that involve image analysis"""

    def __init__(
        self,
        image_validator: DocumentationImageValidator,
        crag_enhancer: CRAGImageEnhancer,
    ):
        self.image_validator = image_validator
        self.crag_enhancer = crag_enhancer

    async def process_documentation_update(
        self, webhook_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process documentation updates that may involve image changes"""

        results = {
            "webhook_processed": True,
            "image_analysis_performed": False,
            "validation_report": None,
            "recommendations": [],
        }

        # Check if update involves images
        modified_files = webhook_data.get("commits", [{}])[0].get("modified", [])
        image_files = [
            f
            for f in modified_files
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg"))
        ]

        if image_files:
            logger.info(f"Image files modified: {image_files}")

            # Determine affected documents
            affected_docs = await self._find_affected_documents(image_files)

            # Validate images in affected documents
            validation_reports = []
            for doc_id in affected_docs:
                try:
                    report = await self.image_validator.validate_document_images(doc_id)
                    validation_reports.append(report)
                except Exception as e:
                    logger.error(f"Failed to validate images in document {doc_id}: {e}")

            if validation_reports:
                results["image_analysis_performed"] = True
                results["validation_report"] = validation_reports

                # Generate overall recommendations
                all_recommendations = []
                for report in validation_reports:
                    all_recommendations.extend(report.recommendations)

                results["recommendations"] = list(set(all_recommendations))

        return results

    async def _find_affected_documents(self, image_files: List[str]) -> List[str]:
        """Find documents that reference the modified image files"""

        # This would typically query the document service
        # For now, return a placeholder
        affected_docs = []

        # In real implementation:
        # 1. Search document content for image references
        # 2. Check document metadata for image associations
        # 3. Use document relationships to find dependent docs

        return affected_docs


class ImageAnalysisIntegrationManager:
    """Main integration manager for image analysis capabilities"""

    def __init__(
        self,
        model_config: ModelConfigManager,
        document_service: DocumentService,
        metrics_service: MetricsService,
        crag_system: Optional[SelfCorrectiveRAG] = None,
    ):

        self.model_config = model_config
        self.document_service = document_service
        self.metrics_service = metrics_service

        # Initialize core components
        self.image_analyzer = ImageAnalysisEngine(model_config)
        self.image_validator = DocumentationImageValidator(
            self.image_analyzer, document_service, metrics_service
        )

        # Optional CRAG integration
        if crag_system:
            self.crag_enhancer = CRAGImageEnhancer(crag_system, self.image_analyzer)
        else:
            self.crag_enhancer = None

        # Webhook processor
        self.webhook_processor = WebhookImageProcessor(
            self.image_validator, self.crag_enhancer
        )

    async def validate_all_documentation_images(self) -> Dict[str, Any]:
        """Validate images across all documentation"""

        # Get all documents
        documents = await self.document_service.list_documents()

        validation_reports = []
        for doc in documents:
            try:
                report = await self.image_validator.validate_document_images(doc["id"])
                validation_reports.append(report)
            except Exception as e:
                logger.error(f"Failed to validate document {doc['id']}: {e}")

        # Aggregate results
        total_images = sum(r.total_images_analyzed for r in validation_reports)
        avg_quality = (
            sum(r.overall_quality_score for r in validation_reports)
            / len(validation_reports)
            if validation_reports
            else 1.0
        )
        avg_accessibility = (
            sum(r.accessibility_compliance for r in validation_reports)
            / len(validation_reports)
            if validation_reports
            else 1.0
        )

        all_issues = []
        for report in validation_reports:
            all_issues.extend(report.issues_found)

        return {
            "total_documents": len(documents),
            "total_images_analyzed": total_images,
            "average_quality_score": avg_quality,
            "average_accessibility_score": avg_accessibility,
            "total_issues_found": len(all_issues),
            "validation_reports": validation_reports,
            "recommendations": self._generate_global_recommendations(
                validation_reports
            ),
        }

    def _generate_global_recommendations(
        self, reports: List[ImageAnalysisReport]
    ) -> List[str]:
        """Generate global recommendations based on all validation reports"""

        recommendations = set()

        # Analyze common issues across all reports
        quality_scores = [r.overall_quality_score for r in reports]
        accessibility_scores = [r.accessibility_compliance for r in reports]

        if sum(quality_scores) / len(quality_scores) < 0.75:
            recommendations.add("Implement organization-wide image quality standards")

        if sum(accessibility_scores) / len(accessibility_scores) < 0.8:
            recommendations.add(
                "Establish accessibility guidelines for documentation images"
            )

        # Count issue types
        issue_types = {}
        for report in reports:
            for issue in report.issues_found:
                issue_type = issue.get("type", "unknown")
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        # Recommend solutions for common issues
        if issue_types.get("quality", 0) > len(reports) * 0.3:
            recommendations.add(
                "Provide training on documentation image quality standards"
            )

        if issue_types.get("accessibility", 0) > len(reports) * 0.2:
            recommendations.add(
                "Implement automated accessibility checks in documentation workflow"
            )

        return list(recommendations)

    async def get_image_analysis_health_check(self) -> Dict[str, Any]:
        """Perform health check of image analysis system"""

        try:
            # Test basic image analysis
            test_image = self._create_test_image()
            test_request = ImageAnalysisRequest(
                image_data=test_image,
                image_type=ImageType.DOCUMENTATION_PAGE,
                analysis_tasks=[AnalysisTask.QUALITY_ASSESSMENT],
            )

            start_time = datetime.utcnow()
            result = await self.image_analyzer.analyze_image(test_request)
            end_time = datetime.utcnow()

            processing_time = (end_time - start_time).total_seconds()

            return {
                "status": "healthy",
                "image_analysis_working": True,
                "test_processing_time": processing_time,
                "test_confidence": result.confidence,
                "components": {
                    "image_analyzer": "operational",
                    "image_validator": "operational",
                    "crag_enhancer": (
                        "operational" if self.crag_enhancer else "not_configured"
                    ),
                    "webhook_processor": "operational",
                },
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "image_analysis_working": False,
            }

    def _create_test_image(self) -> bytes:
        """Create a simple test image for health checks"""

        import io

        from PIL import Image, ImageDraw

        # Create simple test image
        img = Image.new("RGB", (200, 100), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test Image", fill="black")

        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


# Example usage
async def main():
    """Example usage of Image Analysis Integration"""

    # Initialize components
    model_config = ModelConfigManager()
    document_service = DocumentService()
    metrics_service = MetricsService()

    # Initialize integration manager
    integration_manager = ImageAnalysisIntegrationManager(
        model_config, document_service, metrics_service
    )

    # Health check
    health = await integration_manager.get_image_analysis_health_check()
    print(f"Image Analysis Health: {health['status']}")

    # Validate specific document
    try:
        report = await integration_manager.image_validator.validate_document_images(
            "doc-123"
        )
        print("Validation Report:")
        print(f"- Total Images: {report.total_images_analyzed}")
        print(f"- Quality Score: {report.overall_quality_score:.3f}")
        print(f"- Issues Found: {len(report.issues_found)}")
    except Exception as e:
        print(f"Validation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
