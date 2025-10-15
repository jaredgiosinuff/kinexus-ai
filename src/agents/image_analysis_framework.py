#!/usr/bin/env python3
"""
Image Analysis Framework for Documentation Validation
Provides comprehensive image analysis capabilities for document quality assessment
"""
import asyncio
import base64
import hashlib
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont

from ..config.model_config import ModelCapability, ModelConfigManager
from .multi_agent_supervisor import BedrockAgent, MultiAgentSupervisor

# Import existing components
from .self_corrective_rag import QualityMetric, SelfCorrectiveRAG

logger = logging.getLogger(__name__)


class ImageType(Enum):
    """Types of images that can be analyzed"""

    SCREENSHOT = "screenshot"
    DIAGRAM = "diagram"
    FLOWCHART = "flowchart"
    UI_MOCKUP = "ui_mockup"
    ARCHITECTURE = "architecture"
    CODE_SNIPPET = "code_snippet"
    CHART_GRAPH = "chart_graph"
    DOCUMENTATION_PAGE = "documentation_page"
    ERROR_MESSAGE = "error_message"
    UNKNOWN = "unknown"


class AnalysisTask(Enum):
    """Types of analysis tasks"""

    TEXT_EXTRACTION = "text_extraction"
    CONTENT_VALIDATION = "content_validation"
    QUALITY_ASSESSMENT = "quality_assessment"
    ACCESSIBILITY_CHECK = "accessibility_check"
    CONSISTENCY_VALIDATION = "consistency_validation"
    ERROR_DETECTION = "error_detection"
    COMPLETENESS_CHECK = "completeness_check"
    VISUAL_REGRESSION = "visual_regression"


@dataclass
class ImageAnalysisRequest:
    """Request for image analysis"""

    image_data: Union[str, bytes]  # Base64 string or bytes
    image_type: ImageType
    analysis_tasks: List[AnalysisTask]
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_threshold: float = 0.7


@dataclass
class TextExtractionResult:
    """Result of text extraction from image"""

    extracted_text: str
    confidence: float
    bounding_boxes: List[Dict[str, Any]]
    language: str
    text_blocks: List[Dict[str, Any]]


@dataclass
class QualityAssessmentResult:
    """Result of image quality assessment"""

    overall_score: float
    clarity_score: float
    readability_score: float
    completeness_score: float
    accessibility_score: float
    issues_detected: List[str]
    recommendations: List[str]


@dataclass
class ContentValidationResult:
    """Result of content validation"""

    is_valid: bool
    validation_score: float
    content_matches: List[str]
    content_mismatches: List[str]
    missing_elements: List[str]
    extra_elements: List[str]


@dataclass
class ImageAnalysisResult:
    """Comprehensive result of image analysis"""

    request_id: str
    image_type: ImageType
    analysis_timestamp: datetime
    text_extraction: Optional[TextExtractionResult] = None
    quality_assessment: Optional[QualityAssessmentResult] = None
    content_validation: Optional[ContentValidationResult] = None
    accessibility_results: Optional[Dict[str, Any]] = None
    error_detection: Optional[Dict[str, Any]] = None
    processing_time: float = 0.0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ImagePreprocessor:
    """Preprocesses images for optimal analysis"""

    def __init__(self):
        self.supported_formats = ["PNG", "JPEG", "JPG", "GIF", "BMP", "TIFF"]

    async def preprocess_image(
        self, image_data: Union[str, bytes], enhancement_type: str = "auto"
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """Preprocess image for optimal analysis"""

        # Convert to PIL Image
        if isinstance(image_data, str):
            # Assume base64 encoded
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data

        image = Image.open(io.BytesIO(image_bytes))
        original_size = image.size

        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Apply enhancements based on type
        if enhancement_type == "auto":
            enhancement_type = await self._detect_optimal_enhancement(image)

        enhanced_image = await self._apply_enhancement(image, enhancement_type)

        # Generate metadata
        metadata = {
            "original_size": original_size,
            "processed_size": enhanced_image.size,
            "enhancement_applied": enhancement_type,
            "format": image.format,
            "mode": enhanced_image.mode,
        }

        return enhanced_image, metadata

    async def _detect_optimal_enhancement(self, image: Image.Image) -> str:
        """Detect optimal enhancement strategy for image"""

        # Convert to numpy array for analysis
        img_array = np.array(image)

        # Calculate image statistics
        brightness = np.mean(img_array)
        contrast = np.std(img_array)

        # Determine enhancement strategy
        if brightness < 100:
            return "brighten"
        elif contrast < 30:
            return "enhance_contrast"
        elif self._is_blurry(img_array):
            return "sharpen"
        elif self._has_noise(img_array):
            return "denoise"
        else:
            return "normalize"

    def _is_blurry(self, img_array: np.ndarray) -> bool:
        """Detect if image is blurry using Laplacian variance"""
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        return variance < 100

    def _has_noise(self, img_array: np.ndarray) -> bool:
        """Detect if image has significant noise"""
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        noise_level = np.std(gray)
        return noise_level > 50

    async def _apply_enhancement(
        self, image: Image.Image, enhancement_type: str
    ) -> Image.Image:
        """Apply specific enhancement to image"""

        img_array = np.array(image)

        if enhancement_type == "brighten":
            # Increase brightness
            enhanced = cv2.convertScaleAbs(img_array, alpha=1.0, beta=30)

        elif enhancement_type == "enhance_contrast":
            # Enhance contrast using CLAHE
            lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            lab[:, :, 0] = clahe.apply(lab[:, :, 0])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

        elif enhancement_type == "sharpen":
            # Sharpen image
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            enhanced = cv2.filter2D(img_array, -1, kernel)

        elif enhancement_type == "denoise":
            # Remove noise
            enhanced = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)

        elif enhancement_type == "normalize":
            # Normalize image
            enhanced = cv2.normalize(img_array, None, 0, 255, cv2.NORM_MINMAX)

        else:
            enhanced = img_array

        return Image.fromarray(enhanced)


class TextExtractor:
    """Extracts and analyzes text from images"""

    def __init__(self):
        # Configure Tesseract
        self.tesseract_config = "--oem 3 --psm 6"

    async def extract_text(
        self, image: Image.Image, language: str = "eng"
    ) -> TextExtractionResult:
        """Extract text from image using OCR"""

        try:
            # Convert PIL to opencv format
            img_array = np.array(image)

            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                img_array,
                lang=language,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT,
            )

            # Extract text
            extracted_text = pytesseract.image_to_string(
                img_array, lang=language, config=self.tesseract_config
            ).strip()

            # Calculate confidence
            confidences = [int(conf) for conf in ocr_data["conf"] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Extract bounding boxes
            bounding_boxes = self._extract_bounding_boxes(ocr_data)

            # Group text into blocks
            text_blocks = self._group_text_blocks(ocr_data)

            return TextExtractionResult(
                extracted_text=extracted_text,
                confidence=avg_confidence / 100.0,  # Convert to 0-1 scale
                bounding_boxes=bounding_boxes,
                language=language,
                text_blocks=text_blocks,
            )

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return TextExtractionResult(
                extracted_text="",
                confidence=0.0,
                bounding_boxes=[],
                language=language,
                text_blocks=[],
            )

    def _extract_bounding_boxes(self, ocr_data: Dict) -> List[Dict[str, Any]]:
        """Extract bounding boxes for detected text"""

        boxes = []
        n_boxes = len(ocr_data["level"])

        for i in range(n_boxes):
            if int(ocr_data["conf"][i]) > 0:
                x, y, w, h = (
                    ocr_data["left"][i],
                    ocr_data["top"][i],
                    ocr_data["width"][i],
                    ocr_data["height"][i],
                )

                boxes.append(
                    {
                        "text": ocr_data["text"][i],
                        "confidence": int(ocr_data["conf"][i]),
                        "bbox": {"x": x, "y": y, "width": w, "height": h},
                        "level": ocr_data["level"][i],
                    }
                )

        return boxes

    def _group_text_blocks(self, ocr_data: Dict) -> List[Dict[str, Any]]:
        """Group text into logical blocks"""

        blocks = []
        current_block = None

        n_boxes = len(ocr_data["level"])

        for i in range(n_boxes):
            level = ocr_data["level"][i]
            text = ocr_data["text"][i].strip()

            if level == 2 and text:  # Paragraph level
                if current_block:
                    blocks.append(current_block)

                current_block = {
                    "text": text,
                    "bbox": {
                        "x": ocr_data["left"][i],
                        "y": ocr_data["top"][i],
                        "width": ocr_data["width"][i],
                        "height": ocr_data["height"][i],
                    },
                    "confidence": int(ocr_data["conf"][i]),
                    "words": [],
                }

            elif level == 5 and text and current_block:  # Word level
                current_block["words"].append(
                    {
                        "text": text,
                        "confidence": int(ocr_data["conf"][i]),
                        "bbox": {
                            "x": ocr_data["left"][i],
                            "y": ocr_data["top"][i],
                            "width": ocr_data["width"][i],
                            "height": ocr_data["height"][i],
                        },
                    }
                )

        if current_block:
            blocks.append(current_block)

        return blocks


class VisualQualityAnalyzer:
    """Analyzes visual quality and accessibility of images"""

    def __init__(self, model_config: ModelConfigManager):
        self.model_config = model_config
        self.bedrock = boto3.client("bedrock-runtime")

    async def assess_quality(
        self, image: Image.Image, image_type: ImageType, context: Dict[str, Any] = None
    ) -> QualityAssessmentResult:
        """Assess overall image quality"""

        # Technical quality metrics
        clarity_score = await self._assess_clarity(image)
        readability_score = await self._assess_readability(image)
        completeness_score = await self._assess_completeness(image, image_type)
        accessibility_score = await self._assess_accessibility(image)

        # Calculate overall score
        overall_score = (
            clarity_score * 0.3
            + readability_score * 0.3
            + completeness_score * 0.2
            + accessibility_score * 0.2
        )

        # Identify issues and recommendations
        issues = []
        recommendations = []

        if clarity_score < 0.7:
            issues.append(f"Low image clarity ({clarity_score:.2f})")
            recommendations.append("Improve image resolution or reduce blur")

        if readability_score < 0.7:
            issues.append(f"Poor text readability ({readability_score:.2f})")
            recommendations.append("Increase contrast or font size")

        if completeness_score < 0.7:
            issues.append(f"Incomplete content ({completeness_score:.2f})")
            recommendations.append("Ensure all necessary elements are visible")

        if accessibility_score < 0.7:
            issues.append(f"Accessibility concerns ({accessibility_score:.2f})")
            recommendations.append("Improve color contrast and text size")

        return QualityAssessmentResult(
            overall_score=overall_score,
            clarity_score=clarity_score,
            readability_score=readability_score,
            completeness_score=completeness_score,
            accessibility_score=accessibility_score,
            issues_detected=issues,
            recommendations=recommendations,
        )

    async def _assess_clarity(self, image: Image.Image) -> float:
        """Assess image clarity using Laplacian variance"""

        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Calculate Laplacian variance (blur detection)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Normalize to 0-1 scale
        clarity_score = min(laplacian_var / 500.0, 1.0)

        return clarity_score

    async def _assess_readability(self, image: Image.Image) -> float:
        """Assess text readability in image"""

        img_array = np.array(image)

        # Calculate contrast ratio
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Find text regions using edge detection
        edges = cv2.Canny(gray, 50, 150)

        # Calculate contrast in text regions
        text_regions = edges > 0
        if np.any(text_regions):
            text_pixels = gray[text_regions]
            bg_pixels = gray[~text_regions]

            if len(text_pixels) > 0 and len(bg_pixels) > 0:
                contrast_ratio = abs(np.mean(text_pixels) - np.mean(bg_pixels)) / 255.0
            else:
                contrast_ratio = 0.5
        else:
            contrast_ratio = 0.5

        # Text size assessment (approximate)
        text_size_score = min(image.size[0] * image.size[1] / (800 * 600), 1.0)

        # Combine metrics
        readability_score = contrast_ratio * 0.7 + text_size_score * 0.3

        return readability_score

    async def _assess_completeness(
        self, image: Image.Image, image_type: ImageType
    ) -> float:
        """Assess content completeness based on image type"""

        img_array = np.array(image)

        # Calculate information density
        edges = cv2.Canny(cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY), 50, 150)
        edge_density = np.sum(edges > 0) / edges.size

        # Assess based on image type
        if image_type in [
            ImageType.DIAGRAM,
            ImageType.FLOWCHART,
            ImageType.ARCHITECTURE,
        ]:
            # These should have high edge density (shapes, lines)
            completeness_score = min(edge_density * 5, 1.0)
        elif image_type == ImageType.DOCUMENTATION_PAGE:
            # Should have moderate density (text and some graphics)
            completeness_score = min(edge_density * 3, 1.0)
        elif image_type == ImageType.SCREENSHOT:
            # Variable density acceptable
            completeness_score = 0.8 if edge_density > 0.01 else 0.3
        else:
            # Default assessment
            completeness_score = min(edge_density * 2, 1.0)

        return max(completeness_score, 0.1)  # Minimum score

    async def _assess_accessibility(self, image: Image.Image) -> float:
        """Assess accessibility compliance"""

        img_array = np.array(image)

        # Color contrast assessment
        # Convert to LAB color space for better contrast calculation
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l_channel = lab[:, :, 0]

        # Calculate contrast ratio
        l_std = np.std(l_channel)
        contrast_score = min(l_std / 50.0, 1.0)

        # Color accessibility (check for color-blind friendly patterns)
        # Simplified check for sufficient contrast
        rgb_std = np.std(img_array, axis=(0, 1))
        color_diversity = np.mean(rgb_std) / 255.0

        # Text size estimation (based on connected components)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            avg_contour_area = np.mean([cv2.contourArea(c) for c in contours])
            text_size_score = min(avg_contour_area / 100.0, 1.0)
        else:
            text_size_score = 0.5

        # Combine accessibility metrics
        accessibility_score = (
            contrast_score * 0.5 + color_diversity * 0.3 + text_size_score * 0.2
        )

        return accessibility_score


class ContentValidator:
    """Validates image content against documentation requirements"""

    def __init__(self, model_config: ModelConfigManager):
        self.model_config = model_config
        self.bedrock = boto3.client("bedrock-runtime")

    async def validate_content(
        self,
        image: Image.Image,
        expected_content: Dict[str, Any],
        extracted_text: str = "",
    ) -> ContentValidationResult:
        """Validate image content against expectations"""

        validation_score = 0.0
        content_matches = []
        content_mismatches = []
        missing_elements = []
        extra_elements = []

        # Text content validation
        if extracted_text and expected_content.get("required_text"):
            text_validation = await self._validate_text_content(
                extracted_text, expected_content["required_text"]
            )
            validation_score += text_validation["score"] * 0.4
            content_matches.extend(text_validation["matches"])
            content_mismatches.extend(text_validation["mismatches"])
            missing_elements.extend(text_validation["missing"])

        # Visual element validation
        if expected_content.get("visual_elements"):
            visual_validation = await self._validate_visual_elements(
                image, expected_content["visual_elements"]
            )
            validation_score += visual_validation["score"] * 0.3
            content_matches.extend(visual_validation["matches"])
            missing_elements.extend(visual_validation["missing"])

        # Structure validation
        if expected_content.get("structure"):
            structure_validation = await self._validate_structure(
                image, expected_content["structure"]
            )
            validation_score += structure_validation["score"] * 0.3
            content_matches.extend(structure_validation["matches"])
            missing_elements.extend(structure_validation["missing"])

        is_valid = validation_score >= 0.7

        return ContentValidationResult(
            is_valid=is_valid,
            validation_score=validation_score,
            content_matches=content_matches,
            content_mismatches=content_mismatches,
            missing_elements=missing_elements,
            extra_elements=extra_elements,
        )

    async def _validate_text_content(
        self, extracted_text: str, required_text: List[str]
    ) -> Dict[str, Any]:
        """Validate required text content"""

        extracted_lower = extracted_text.lower()
        matches = []
        mismatches = []
        missing = []

        for required in required_text:
            required_lower = required.lower()
            if required_lower in extracted_lower:
                matches.append(required)
            else:
                missing.append(required)

        score = len(matches) / len(required_text) if required_text else 1.0

        return {
            "score": score,
            "matches": matches,
            "mismatches": mismatches,
            "missing": missing,
        }

    async def _validate_visual_elements(
        self, image: Image.Image, visual_elements: List[str]
    ) -> Dict[str, Any]:
        """Validate presence of visual elements using AI vision"""

        # Convert image to base64 for Bedrock
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        # Use Nova Pro for visual analysis
        prompt = f"""
        Analyze this image and identify which of these visual elements are present:
        {', '.join(visual_elements)}

        Respond with a JSON object containing:
        - "found_elements": list of elements that are clearly visible
        - "missing_elements": list of elements that are not visible
        - "confidence": overall confidence score (0-1)

        Only include elements you are confident about.
        """

        try:
            matches, missing = await self._call_vision_model(
                img_base64, prompt, visual_elements
            )
            score = len(matches) / len(visual_elements) if visual_elements else 1.0

            return {"score": score, "matches": matches, "missing": missing}

        except Exception as e:
            logger.error(f"Visual element validation failed: {e}")
            return {"score": 0.5, "matches": [], "missing": visual_elements}

    async def _validate_structure(
        self, image: Image.Image, structure_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate image structure and layout"""

        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        matches = []
        missing = []

        # Check for layout elements
        if "has_header" in structure_requirements:
            if await self._detect_header(gray):
                matches.append("header")
            else:
                missing.append("header")

        if "has_navigation" in structure_requirements:
            if await self._detect_navigation(gray):
                matches.append("navigation")
            else:
                missing.append("navigation")

        if "has_main_content" in structure_requirements:
            if await self._detect_main_content(gray):
                matches.append("main_content")
            else:
                missing.append("main_content")

        total_requirements = len(structure_requirements)
        score = len(matches) / total_requirements if total_requirements > 0 else 1.0

        return {"score": score, "matches": matches, "missing": missing}

    async def _detect_header(self, gray: np.ndarray) -> bool:
        """Detect if image has a header section"""
        height, width = gray.shape
        header_region = gray[: int(height * 0.15), :]

        # Look for horizontal lines or text in top region
        edges = cv2.Canny(header_region, 50, 150)
        horizontal_lines = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 180,
            threshold=width // 4,
            minLineLength=width // 3,
            maxLineGap=10,
        )

        return horizontal_lines is not None and len(horizontal_lines) > 0

    async def _detect_navigation(self, gray: np.ndarray) -> bool:
        """Detect if image has navigation elements"""
        height, width = gray.shape

        # Check left side for vertical navigation
        left_region = gray[:, : int(width * 0.2)]

        # Check top for horizontal navigation
        top_region = gray[: int(height * 0.2), :]

        # Look for repeated patterns (menu items)
        # This is a simplified detection
        edges = cv2.Canny(top_region, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Navigation typically has multiple similar-sized elements
        if len(contours) >= 3:
            areas = [cv2.contourArea(c) for c in contours]
            avg_area = np.mean(areas)
            similar_areas = sum(
                1 for area in areas if abs(area - avg_area) < avg_area * 0.5
            )
            return similar_areas >= 3

        return False

    async def _detect_main_content(self, gray: np.ndarray) -> bool:
        """Detect if image has substantial main content"""
        height, width = gray.shape

        # Define main content area (excluding likely header/footer/sidebar)
        main_region = gray[
            int(height * 0.2) : int(height * 0.8), int(width * 0.1) : int(width * 0.9)
        ]

        # Check for content density
        edges = cv2.Canny(main_region, 50, 150)
        content_density = np.sum(edges > 0) / edges.size

        return content_density > 0.02  # Threshold for meaningful content

    async def _call_vision_model(
        self, img_base64: str, prompt: str, elements: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Call Bedrock vision model for visual analysis"""

        try:
            # Use Nova Pro for visual analysis
            model_id = "amazon.nova-pro-v1:0"

            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": prompt},
                            {
                                "image": {
                                    "format": "png",
                                    "source": {"bytes": img_base64},
                                }
                            },
                        ],
                    }
                ],
                "inferenceConfig": {"max_new_tokens": 1000, "temperature": 0.1},
            }

            response = self.bedrock.invoke_model(
                modelId=model_id, body=json.dumps(body)
            )

            result = json.loads(response["body"].read())
            response_text = result["output"]["message"]["content"][0]["text"]

            # Parse JSON response
            import re

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                analysis_result = json.loads(json_match.group())
                found = analysis_result.get("found_elements", [])
                missing = analysis_result.get("missing_elements", elements)
                return found, missing
            else:
                # Fallback parsing
                found = [
                    elem for elem in elements if elem.lower() in response_text.lower()
                ]
                missing = [elem for elem in elements if elem not in found]
                return found, missing

        except Exception as e:
            logger.error(f"Vision model call failed: {e}")
            return [], elements


class ImageAnalysisEngine:
    """Main engine that orchestrates all image analysis tasks"""

    def __init__(self, model_config: ModelConfigManager):
        self.model_config = model_config
        self.preprocessor = ImagePreprocessor()
        self.text_extractor = TextExtractor()
        self.quality_analyzer = VisualQualityAnalyzer(model_config)
        self.content_validator = ContentValidator(model_config)

    async def analyze_image(self, request: ImageAnalysisRequest) -> ImageAnalysisResult:
        """Perform comprehensive image analysis"""

        start_time = datetime.utcnow()
        request_id = f"img-analysis-{hashlib.md5(str(request.image_data).encode()).hexdigest()[:8]}"

        try:
            # Preprocess image
            image, preprocessing_metadata = await self.preprocessor.preprocess_image(
                request.image_data
            )

            result = ImageAnalysisResult(
                request_id=request_id,
                image_type=request.image_type,
                analysis_timestamp=start_time,
                metadata={"preprocessing": preprocessing_metadata},
            )

            # Perform requested analysis tasks
            if AnalysisTask.TEXT_EXTRACTION in request.analysis_tasks:
                result.text_extraction = await self.text_extractor.extract_text(image)

            if AnalysisTask.QUALITY_ASSESSMENT in request.analysis_tasks:
                result.quality_assessment = await self.quality_analyzer.assess_quality(
                    image, request.image_type, request.context
                )

            if AnalysisTask.CONTENT_VALIDATION in request.analysis_tasks:
                expected_content = request.context.get("expected_content", {})
                extracted_text = (
                    result.text_extraction.extracted_text
                    if result.text_extraction
                    else ""
                )
                result.content_validation = (
                    await self.content_validator.validate_content(
                        image, expected_content, extracted_text
                    )
                )

            if AnalysisTask.ACCESSIBILITY_CHECK in request.analysis_tasks:
                result.accessibility_results = await self._perform_accessibility_check(
                    image
                )

            if AnalysisTask.ERROR_DETECTION in request.analysis_tasks:
                result.error_detection = await self._detect_errors(
                    image, result.text_extraction
                )

            # Calculate overall confidence
            result.confidence = self._calculate_overall_confidence(result)

            # Calculate processing time
            end_time = datetime.utcnow()
            result.processing_time = (end_time - start_time).total_seconds()

            logger.info(
                f"Image analysis completed: {request_id}, confidence: {result.confidence:.3f}"
            )

            return result

        except Exception as e:
            logger.error(f"Image analysis failed for {request_id}: {e}")

            # Return minimal result with error info
            end_time = datetime.utcnow()
            return ImageAnalysisResult(
                request_id=request_id,
                image_type=request.image_type,
                analysis_timestamp=start_time,
                processing_time=(end_time - start_time).total_seconds(),
                confidence=0.0,
                metadata={"error": str(e)},
            )

    async def _perform_accessibility_check(self, image: Image.Image) -> Dict[str, Any]:
        """Perform accessibility compliance check"""

        img_array = np.array(image)

        # Color contrast check
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l_channel = lab[:, :, 0]
        contrast_ratio = np.std(l_channel) / np.mean(l_channel)

        # Text size estimation
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if contours:
            avg_contour_area = np.mean([cv2.contourArea(c) for c in contours])
            text_size_adequate = avg_contour_area > 50  # Minimum readable size
        else:
            text_size_adequate = False

        # Color blindness check (simplified)
        r_channel = img_array[:, :, 0]
        g_channel = img_array[:, :, 1]
        b_channel = img_array[:, :, 2]

        rg_diff = np.mean(np.abs(r_channel.astype(float) - g_channel.astype(float)))
        colorblind_friendly = (
            rg_diff > 30
        )  # Sufficient difference for red-green colorblind

        return {
            "contrast_ratio": float(contrast_ratio),
            "contrast_adequate": contrast_ratio > 0.15,
            "text_size_adequate": text_size_adequate,
            "colorblind_friendly": colorblind_friendly,
            "overall_accessibility_score": (
                (contrast_ratio > 0.15) * 0.4
                + text_size_adequate * 0.4
                + colorblind_friendly * 0.2
            ),
        }

    async def _detect_errors(
        self, image: Image.Image, text_extraction: Optional[TextExtractionResult]
    ) -> Dict[str, Any]:
        """Detect common errors in documentation images"""

        errors = []
        warnings = []

        # Check for blur/quality issues
        img_array = np.array(image)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

        if blur_score < 100:
            errors.append("Image appears blurry or low quality")

        # Check for text extraction issues
        if text_extraction:
            if text_extraction.confidence < 0.5:
                warnings.append("Low OCR confidence - text may be unclear")

            if len(text_extraction.extracted_text) < 10:
                warnings.append("Very little text detected")

        # Check for truncated content
        height, width = gray.shape
        edges = cv2.Canny(gray, 50, 150)

        # Check edges of image for cut-off content
        edge_regions = [
            edges[:5, :],  # Top edge
            edges[-5:, :],  # Bottom edge
            edges[:, :5],  # Left edge
            edges[:, -5:],  # Right edge
        ]

        for i, region in enumerate(edge_regions):
            if np.sum(region > 0) > region.size * 0.1:
                edge_names = ["top", "bottom", "left", "right"]
                warnings.append(f"Possible content cut-off at {edge_names[i]} edge")

        # Check for resolution issues
        if width < 800 or height < 600:
            warnings.append("Low resolution may affect readability")

        return {
            "errors": errors,
            "warnings": warnings,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "overall_health": (
                "good"
                if not errors and len(warnings) <= 1
                else "poor" if errors else "fair"
            ),
        }

    def _calculate_overall_confidence(self, result: ImageAnalysisResult) -> float:
        """Calculate overall confidence score for analysis"""

        confidences = []

        if result.text_extraction:
            confidences.append(result.text_extraction.confidence)

        if result.quality_assessment:
            confidences.append(result.quality_assessment.overall_score)

        if result.content_validation:
            confidences.append(result.content_validation.validation_score)

        if result.accessibility_results:
            confidences.append(
                result.accessibility_results.get("overall_accessibility_score", 0.5)
            )

        if confidences:
            return sum(confidences) / len(confidences)
        else:
            return 0.5  # Default confidence

    async def batch_analyze_images(
        self, requests: List[ImageAnalysisRequest]
    ) -> List[ImageAnalysisResult]:
        """Analyze multiple images in batch"""

        # Process images concurrently with semaphore for resource control
        semaphore = asyncio.Semaphore(5)  # Limit concurrent processing

        async def process_single(request):
            async with semaphore:
                return await self.analyze_image(request)

        tasks = [process_single(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log them
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch analysis failed for request {i}: {result}")
            else:
                successful_results.append(result)

        logger.info(
            f"Batch analyzed {len(successful_results)}/{len(requests)} images successfully"
        )
        return successful_results


# Integration with existing systems
class DocumentImageAnalyzer:
    """Integrates image analysis with document management"""

    def __init__(
        self,
        analysis_engine: ImageAnalysisEngine,
        crag_system: Optional[SelfCorrectiveRAG] = None,
    ):
        self.analysis_engine = analysis_engine
        self.crag_system = crag_system

    async def analyze_document_images(
        self, document_id: str, image_urls: List[str]
    ) -> List[ImageAnalysisResult]:
        """Analyze all images in a document"""

        results = []

        for url in image_urls:
            try:
                # Download image (simplified - in real implementation, use proper HTTP client)
                image_data = await self._download_image(url)

                # Create analysis request
                request = ImageAnalysisRequest(
                    image_data=image_data,
                    image_type=ImageType.DOCUMENTATION_PAGE,  # Default
                    analysis_tasks=[
                        AnalysisTask.TEXT_EXTRACTION,
                        AnalysisTask.QUALITY_ASSESSMENT,
                        AnalysisTask.ACCESSIBILITY_CHECK,
                    ],
                    context={"document_id": document_id, "image_url": url},
                )

                # Analyze image
                result = await self.analysis_engine.analyze_image(request)
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to analyze image {url}: {e}")

        return results

    async def validate_documentation_screenshots(
        self, screenshots: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate documentation screenshots for quality and accuracy"""

        validation_results = []

        for screenshot in screenshots:
            request = ImageAnalysisRequest(
                image_data=screenshot["data"],
                image_type=ImageType.SCREENSHOT,
                analysis_tasks=[
                    AnalysisTask.QUALITY_ASSESSMENT,
                    AnalysisTask.CONTENT_VALIDATION,
                    AnalysisTask.ERROR_DETECTION,
                ],
                context={
                    "expected_content": screenshot.get("expected_content", {}),
                    "validation_criteria": screenshot.get("criteria", {}),
                },
            )

            result = await self.analysis_engine.analyze_image(request)
            validation_results.append(result)

        # Aggregate results
        overall_quality = sum(
            r.quality_assessment.overall_score
            for r in validation_results
            if r.quality_assessment
        ) / len(validation_results)

        issues = []
        for result in validation_results:
            if result.quality_assessment:
                issues.extend(result.quality_assessment.issues_detected)
            if result.error_detection:
                issues.extend(result.error_detection.get("errors", []))

        return {
            "overall_quality": overall_quality,
            "total_images": len(screenshots),
            "passed_validation": sum(
                1
                for r in validation_results
                if r.quality_assessment and r.quality_assessment.overall_score > 0.7
            ),
            "common_issues": issues,
            "detailed_results": validation_results,
        }

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL (placeholder implementation)"""
        # In real implementation, use aiohttp or similar
        import urllib.request

        with urllib.request.urlopen(url) as response:
            return response.read()


# Example usage and testing
async def main():
    """Example usage of Image Analysis Framework"""

    # Initialize components
    model_config = ModelConfigManager()
    analysis_engine = ImageAnalysisEngine(model_config)

    # Example: Analyze a documentation screenshot
    with open("example_screenshot.png", "rb") as f:
        image_data = f.read()

    request = ImageAnalysisRequest(
        image_data=image_data,
        image_type=ImageType.DOCUMENTATION_PAGE,
        analysis_tasks=[
            AnalysisTask.TEXT_EXTRACTION,
            AnalysisTask.QUALITY_ASSESSMENT,
            AnalysisTask.CONTENT_VALIDATION,
            AnalysisTask.ACCESSIBILITY_CHECK,
        ],
        context={
            "expected_content": {
                "required_text": ["API", "Authentication", "Examples"],
                "visual_elements": ["header", "navigation", "code blocks"],
            }
        },
    )

    # Analyze image
    result = await analysis_engine.analyze_image(request)

    print(f"Image Analysis Results:")
    print(f"- Overall Confidence: {result.confidence:.3f}")
    print(f"- Processing Time: {result.processing_time:.2f}s")

    if result.text_extraction:
        print(f"- Extracted Text: {result.text_extraction.extracted_text[:100]}...")
        print(f"- OCR Confidence: {result.text_extraction.confidence:.3f}")

    if result.quality_assessment:
        print(f"- Quality Score: {result.quality_assessment.overall_score:.3f}")
        print(f"- Issues: {result.quality_assessment.issues_detected}")

    if result.content_validation:
        print(f"- Content Valid: {result.content_validation.is_valid}")
        print(f"- Missing Elements: {result.content_validation.missing_elements}")


if __name__ == "__main__":
    asyncio.run(main())
