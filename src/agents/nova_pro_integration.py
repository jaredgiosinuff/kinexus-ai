#!/usr/bin/env python3
"""
Amazon Nova Pro Integration for Kinexus AI
Provides image analysis capabilities for documentation validation
"""
import asyncio
import base64
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageType(Enum):
    """Types of images we can analyze"""

    DIAGRAM = "diagram"
    CHART = "chart"
    SCREENSHOT = "screenshot"
    FLOWCHART = "flowchart"
    ARCHITECTURE = "architecture"
    UI_MOCKUP = "ui_mockup"
    UNKNOWN = "unknown"


@dataclass
class ImageAnalysisResult:
    """Result of image analysis"""

    image_type: ImageType
    confidence: float
    description: str
    extracted_text: Optional[str] = None
    accuracy_assessment: Optional[Dict[str, Any]] = None
    validation_results: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class NovaProImageAnalyzer:
    """
    Amazon Nova Pro integration for image analysis in documentation
    Focuses on diagram/chart validation and documentation accuracy
    """

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)

        # Nova Pro model configuration
        self.nova_pro_model_id = "amazon.nova-pro-v1:0"
        self.nova_lite_model_id = "amazon.nova-lite-v1:0"  # For faster operations

        # Image processing settings
        self.max_image_size = 4 * 1024 * 1024  # 4MB limit
        self.supported_formats = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]

    async def analyze_documentation_image(
        self, image_data: Union[str, bytes], context: Optional[Dict[str, Any]] = None
    ) -> ImageAnalysisResult:
        """
        Analyze an image from documentation for accuracy and type classification

        Args:
            image_data: Base64 encoded image string or raw bytes
            context: Additional context about the documentation/image
        """
        try:
            logger.info("Starting Nova Pro image analysis for documentation")

            # Prepare image data
            if isinstance(image_data, str):
                # Assume base64 encoded
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data

            # Validate image size
            if len(image_bytes) > self.max_image_size:
                raise ValueError(
                    f"Image size {len(image_bytes)} exceeds limit {self.max_image_size}"
                )

            # Classify image type first
            image_type = await self._classify_image_type(image_bytes, context)

            # Perform detailed analysis based on type
            if image_type in [
                ImageType.DIAGRAM,
                ImageType.CHART,
                ImageType.FLOWCHART,
                ImageType.ARCHITECTURE,
            ]:
                result = await self._analyze_technical_diagram(
                    image_bytes, image_type, context
                )
            elif image_type in [ImageType.SCREENSHOT, ImageType.UI_MOCKUP]:
                result = await self._analyze_ui_documentation(
                    image_bytes, image_type, context
                )
            else:
                result = await self._perform_general_analysis(
                    image_bytes, image_type, context
                )

            logger.info(
                f"Image analysis completed: {image_type.value} with confidence {result.confidence}"
            )
            return result

        except Exception as e:
            logger.error(f"Error in Nova Pro image analysis: {str(e)}")
            return ImageAnalysisResult(
                image_type=ImageType.UNKNOWN,
                confidence=0.0,
                description=f"Analysis failed: {str(e)}",
                metadata={"error": str(e)},
            )

    async def _classify_image_type(
        self, image_bytes: bytes, context: Optional[Dict[str, Any]]
    ) -> ImageType:
        """Classify the type of image using Nova Pro"""
        try:
            # Convert image to base64 for API
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # Build classification prompt
            classification_prompt = """
Analyze this image and classify it into one of these categories:
- diagram: Technical diagrams, system diagrams, network diagrams
- chart: Graphs, charts, data visualizations, plots
- screenshot: Screenshots of applications, websites, or interfaces
- flowchart: Process flows, decision trees, workflow diagrams
- architecture: Software architecture diagrams, system architecture
- ui_mockup: User interface mockups, wireframes, design mockups
- unknown: If none of the above categories fit

Respond with just the category name and a confidence score (0-1).
Format: category_name|confidence_score
"""

            # Call Nova Pro for classification
            response = await self._call_nova_pro(
                prompt=classification_prompt,
                image_base64=image_base64,
                use_lite_model=True,  # Use lite model for quick classification
            )

            # Parse response
            if "|" in response:
                category, confidence_str = response.strip().split("|", 1)
                try:
                    _confidence = float(confidence_str)
                    return ImageType(category.lower())
                except (ValueError, KeyError):
                    logger.warning(f"Invalid classification response: {response}")

            return ImageType.UNKNOWN

        except Exception as e:
            logger.error(f"Error classifying image type: {str(e)}")
            return ImageType.UNKNOWN

    async def _analyze_technical_diagram(
        self,
        image_bytes: bytes,
        image_type: ImageType,
        context: Optional[Dict[str, Any]],
    ) -> ImageAnalysisResult:
        """Analyze technical diagrams for accuracy and completeness"""
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        analysis_prompt = f"""
You are analyzing a {image_type.value} from technical documentation. Please provide:

1. DESCRIPTION: Detailed description of what the diagram shows
2. COMPONENTS: List all visible components, elements, or data points
3. RELATIONSHIPS: Describe connections, flows, or relationships shown
4. TEXT_EXTRACTION: Extract any text labels, titles, or annotations
5. ACCURACY_ASSESSMENT: Rate the diagram's clarity and completeness (1-10)
6. VALIDATION_POINTS: Identify any potential issues or areas for improvement

{f"CONTEXT: {context}" if context else ""}

Respond in JSON format with the following structure:
{{
    "description": "detailed description",
    "components": ["component1", "component2"],
    "relationships": "description of relationships",
    "extracted_text": "all text found in image",
    "accuracy_score": 8,
    "clarity_score": 7,
    "completeness_score": 9,
    "validation_issues": ["issue1", "issue2"],
    "recommendations": ["recommendation1", "recommendation2"]
}}
"""

        try:
            response = await self._call_nova_pro(analysis_prompt, image_base64)
            analysis_data = json.loads(response)

            # Calculate overall confidence
            accuracy = analysis_data.get("accuracy_score", 5) / 10
            clarity = analysis_data.get("clarity_score", 5) / 10
            completeness = analysis_data.get("completeness_score", 5) / 10
            confidence = (accuracy + clarity + completeness) / 3

            return ImageAnalysisResult(
                image_type=image_type,
                confidence=confidence,
                description=analysis_data.get(
                    "description", "Technical diagram analyzed"
                ),
                extracted_text=analysis_data.get("extracted_text"),
                accuracy_assessment={
                    "accuracy_score": analysis_data.get("accuracy_score"),
                    "clarity_score": analysis_data.get("clarity_score"),
                    "completeness_score": analysis_data.get("completeness_score"),
                },
                validation_results={
                    "issues": analysis_data.get("validation_issues", []),
                    "recommendations": analysis_data.get("recommendations", []),
                },
                metadata={
                    "components": analysis_data.get("components", []),
                    "relationships": analysis_data.get("relationships", ""),
                },
            )

        except json.JSONDecodeError:
            logger.error("Failed to parse Nova Pro JSON response")
            return ImageAnalysisResult(
                image_type=image_type,
                confidence=0.5,
                description="Technical diagram analyzed with parsing issues",
                metadata={"parsing_error": True},
            )

    async def _analyze_ui_documentation(
        self,
        image_bytes: bytes,
        image_type: ImageType,
        context: Optional[Dict[str, Any]],
    ) -> ImageAnalysisResult:
        """Analyze UI screenshots and mockups"""
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        ui_prompt = f"""
Analyze this {image_type.value} for UI documentation purposes:

1. UI_ELEMENTS: Identify buttons, forms, menus, navigation elements
2. LAYOUT: Describe the overall layout and structure
3. TEXT_CONTENT: Extract all visible text
4. ACCESSIBILITY: Note any accessibility considerations
5. DOCUMENTATION_QUALITY: How well does this serve documentation purposes?

{f"CONTEXT: {context}" if context else ""}

Respond in JSON format:
{{
    "ui_elements": ["button", "menu", "form"],
    "layout_description": "description",
    "extracted_text": "all text",
    "accessibility_notes": ["note1", "note2"],
    "documentation_quality": 8,
    "missing_elements": ["element1"],
    "clarity_assessment": "assessment"
}}
"""

        try:
            response = await self._call_nova_pro(ui_prompt, image_base64)
            ui_data = json.loads(response)

            confidence = ui_data.get("documentation_quality", 5) / 10

            return ImageAnalysisResult(
                image_type=image_type,
                confidence=confidence,
                description=ui_data.get(
                    "layout_description", "UI documentation analyzed"
                ),
                extracted_text=ui_data.get("extracted_text"),
                validation_results={
                    "accessibility_notes": ui_data.get("accessibility_notes", []),
                    "missing_elements": ui_data.get("missing_elements", []),
                },
                metadata={
                    "ui_elements": ui_data.get("ui_elements", []),
                    "clarity_assessment": ui_data.get("clarity_assessment", ""),
                },
            )

        except json.JSONDecodeError:
            return ImageAnalysisResult(
                image_type=image_type,
                confidence=0.5,
                description="UI documentation analyzed with parsing issues",
            )

    async def _perform_general_analysis(
        self,
        image_bytes: bytes,
        image_type: ImageType,
        context: Optional[Dict[str, Any]],
    ) -> ImageAnalysisResult:
        """Perform general image analysis"""
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        general_prompt = f"""
Analyze this image for documentation purposes:

1. What does this image show?
2. What text can you extract?
3. How relevant is this for technical documentation?
4. Any issues with quality or clarity?

{f"CONTEXT: {context}" if context else ""}

Provide a clear, concise analysis focusing on documentation value.
"""

        try:
            response = await self._call_nova_pro(general_prompt, image_base64)

            return ImageAnalysisResult(
                image_type=image_type,
                confidence=0.7,  # Default confidence for general analysis
                description=response,
                metadata={"analysis_type": "general"},
            )

        except Exception as e:
            return ImageAnalysisResult(
                image_type=image_type,
                confidence=0.3,
                description=f"General analysis completed with issues: {str(e)}",
            )

    async def _call_nova_pro(
        self, prompt: str, image_base64: str, use_lite_model: bool = False
    ) -> str:
        """Call Nova Pro API for image analysis"""
        model_id = self.nova_lite_model_id if use_lite_model else self.nova_pro_model_id

        # Prepare the request body for Nova Pro
        request_body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 4000,
                "temperature": 0.1,
                "topP": 0.9,
            },
            "inferenceConfig": {"max_tokens": 4000, "temperature": 0.1},
        }

        # Add image data
        if image_base64:
            request_body["inputImage"] = {
                "format": "png",  # Nova Pro handles format detection
                "source": {"bytes": image_base64},
            }

        try:
            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                ),
            )

            response_body = json.loads(response["body"].read())

            # Extract text from Nova Pro response
            if "results" in response_body:
                return response_body["results"][0]["outputText"]
            elif "completion" in response_body:
                return response_body["completion"]
            else:
                return response_body.get("outputText", "No response text")

        except Exception as e:
            logger.error(f"Error calling Nova Pro: {str(e)}")
            raise

    async def validate_diagram_accuracy(
        self, image_data: Union[str, bytes], reference_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate diagram accuracy against reference data

        Args:
            image_data: Image to validate
            reference_data: Reference information to validate against
        """
        try:
            # Analyze the image
            analysis = await self.analyze_documentation_image(
                image_data, reference_data
            )

            # Compare with reference data
            validation_results = {
                "overall_accuracy": analysis.confidence,
                "validation_passed": analysis.confidence >= 0.7,
                "image_type": analysis.image_type.value,
                "issues_found": [],
                "recommendations": [],
            }

            # Add specific validation logic based on reference data
            if reference_data.get("expected_components"):
                expected = set(reference_data["expected_components"])
                found = set(analysis.metadata.get("components", []))

                missing = expected - found
                extra = found - expected

                if missing:
                    validation_results["issues_found"].append(
                        f"Missing components: {missing}"
                    )
                if extra:
                    validation_results["issues_found"].append(
                        f"Unexpected components: {extra}"
                    )

            # Add validation results from analysis
            if analysis.validation_results:
                validation_results["issues_found"].extend(
                    analysis.validation_results.get("issues", [])
                )
                validation_results["recommendations"].extend(
                    analysis.validation_results.get("recommendations", [])
                )

            return validation_results

        except Exception as e:
            logger.error(f"Error in diagram validation: {str(e)}")
            return {
                "overall_accuracy": 0.0,
                "validation_passed": False,
                "error": str(e),
            }

    def get_supported_formats(self) -> List[str]:
        """Get list of supported image formats"""
        return self.supported_formats

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about Nova Pro models used"""
        return {
            "primary_model": self.nova_pro_model_id,
            "classification_model": self.nova_lite_model_id,
            "capabilities": [
                "Image classification",
                "Text extraction",
                "Diagram analysis",
                "UI documentation analysis",
                "Accuracy validation",
            ],
            "supported_image_types": [t.value for t in ImageType],
            "max_image_size": self.max_image_size,
        }


# Integration function for existing systems
async def analyze_documentation_image(
    image_path_or_data: Union[str, bytes], context: Optional[Dict[str, Any]] = None
) -> ImageAnalysisResult:
    """
    Standalone function to analyze documentation images

    Args:
        image_path_or_data: File path or image data
        context: Additional context for analysis
    """
    analyzer = NovaProImageAnalyzer()

    if isinstance(image_path_or_data, str) and os.path.exists(image_path_or_data):
        # Load image from file
        with open(image_path_or_data, "rb") as f:
            image_data = f.read()
    else:
        image_data = image_path_or_data

    return await analyzer.analyze_documentation_image(image_data, context)


# Example usage and testing
async def test_nova_pro_integration():
    """Test Nova Pro integration"""
    logger.info("Testing Nova Pro Integration")

    analyzer = NovaProImageAnalyzer()

    # Test model info
    model_info = analyzer.get_model_info()
    logger.info(f"Nova Pro Model Info: {json.dumps(model_info, indent=2)}")

    # In a real scenario, you would test with actual images
    logger.info("Nova Pro integration test setup complete")


if __name__ == "__main__":
    asyncio.run(test_nova_pro_integration())
