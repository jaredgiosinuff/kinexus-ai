# Image Analysis Framework for Documentation Validation

> **⚠️ Local Development Environment Only**
>
> The Image Analysis Framework is currently **not deployed to production AWS**. It is available only in the local FastAPI development stack for testing and experimentation.
>
> **Production Environment**: Uses Amazon Nova Lite for text-based documentation generation only. No image analysis, OCR, or visual content validation is performed in production Lambda functions.
>
> See [Production Architecture](../architecture.md) for the actual deployed AWS serverless system.

## Overview

The Image Analysis Framework provides comprehensive visual content analysis capabilities for Kinexus AI's **local development environment**. It uses advanced computer vision, OCR, and AI-powered analysis to validate, assess, and enhance documentation images during development and testing.

## Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Image Input    │───▶│  Preprocessing   │───▶│  Multi-Modal    │
│  (PNG/JPG/SVG) │    │  & Enhancement   │    │  Analysis       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Text           │    │  Quality         │    │  Content        │
│  Extraction     │    │  Assessment      │    │  Validation     │
│  (OCR)          │    │  (7 Metrics)     │    │  (AI Vision)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 1. Image Preprocessing Engine

**Enhancement Strategies:**
- **Auto-Detection**: Analyzes image characteristics to determine optimal enhancement
- **Brightness Adjustment**: Corrects under/over-exposed images
- **Contrast Enhancement**: Uses CLAHE (Contrast Limited Adaptive Histogram Equalization)
- **Sharpening**: Reduces blur using convolution kernels
- **Denoising**: Removes visual noise while preserving content
- **Normalization**: Standardizes color and intensity distributions

### 2. Text Extraction System

**OCR Capabilities:**
- **Tesseract Integration**: High-accuracy text recognition
- **Multi-Language Support**: Configurable language detection
- **Bounding Box Detection**: Precise text location identification
- **Confidence Scoring**: Per-character and per-word accuracy metrics
- **Text Block Organization**: Logical grouping of text elements

### 3. Visual Quality Analysis

**Quality Metrics:**
- **Clarity Score**: Laplacian variance-based blur detection
- **Readability Score**: Text contrast and size assessment
- **Completeness Score**: Content density analysis by image type
- **Accessibility Score**: Color contrast and accessibility compliance

### 4. Content Validation Engine

**Validation Types:**
- **Text Content**: Required terms and phrases verification
- **Visual Elements**: AI-powered element detection using Amazon Nova Pro
- **Structure Validation**: Layout and organization assessment
- **Error Detection**: Common documentation image issues

## Implementation

### Core Classes

#### `ImageAnalysisEngine`
Main orchestrator for comprehensive image analysis.

```python
from src.agents.image_analysis_framework import (
    ImageAnalysisEngine, ImageAnalysisRequest,
    ImageType, AnalysisTask
)

# Initialize engine
engine = ImageAnalysisEngine(model_config)

# Create analysis request
request = ImageAnalysisRequest(
    image_data=image_bytes,
    image_type=ImageType.DOCUMENTATION_PAGE,
    analysis_tasks=[
        AnalysisTask.TEXT_EXTRACTION,
        AnalysisTask.QUALITY_ASSESSMENT,
        AnalysisTask.ACCESSIBILITY_CHECK
    ],
    context={'expected_content': {'required_text': ['API', 'Authentication']}}
)

# Analyze image
result = await engine.analyze_image(request)
```

#### `ImagePreprocessor`
Optimizes images for analysis through intelligent enhancement.

```python
from src.agents.image_analysis_framework import ImagePreprocessor

preprocessor = ImagePreprocessor()

# Automatic enhancement
enhanced_image, metadata = await preprocessor.preprocess_image(
    image_data, enhancement_type="auto"
)

# Specific enhancement
enhanced_image, metadata = await preprocessor.preprocess_image(
    image_data, enhancement_type="enhance_contrast"
)
```

#### `TextExtractor`
Extracts and analyzes text content from images.

```python
from src.agents.image_analysis_framework import TextExtractor

extractor = TextExtractor()

# Extract text with bounding boxes
result = await extractor.extract_text(image, language='eng')

print(f"Extracted: {result.extracted_text}")
print(f"Confidence: {result.confidence:.3f}")
print(f"Text Blocks: {len(result.text_blocks)}")
```

#### `VisualQualityAnalyzer`
Assesses visual quality across multiple dimensions.

```python
from src.agents.image_analysis_framework import VisualQualityAnalyzer

analyzer = VisualQualityAnalyzer(model_config)

# Assess quality
assessment = await analyzer.assess_quality(image, ImageType.SCREENSHOT)

print(f"Overall Score: {assessment.overall_score:.3f}")
print(f"Clarity: {assessment.clarity_score:.3f}")
print(f"Readability: {assessment.readability_score:.3f}")
print(f"Issues: {assessment.issues_detected}")
```

### Integration Components

#### `DocumentationImageValidator`
Validates images within documentation context.

```python
from src.agents.image_analysis_integration import DocumentationImageValidator

validator = DocumentationImageValidator(engine, doc_service, metrics_service)

# Validate all images in document
report = await validator.validate_document_images("doc-123")

print(f"Total Images: {report.total_images_analyzed}")
print(f"Quality Score: {report.overall_quality_score:.3f}")
print(f"Accessibility: {report.accessibility_compliance:.3f}")
```

#### `CRAGImageEnhancer`
Integrates image analysis with CRAG system for enhanced responses.

```python
from src.agents.image_analysis_integration import CRAGImageEnhancer

enhancer = CRAGImageEnhancer(crag_system, image_analyzer)

# Process query with image context
image_context = [
    {'data': screenshot_bytes, 'type': 'screenshot'},
    {'data': diagram_bytes, 'type': 'diagram'}
]

result = await enhancer.process_query_with_images(query, image_context)

print(f"Enhanced Response: {result['enhanced_response']}")
print(f"Combined Confidence: {result['combined_confidence']:.3f}")
```

## Supported Image Types

### Image Format Support

| Format | Read | Write | Notes |
|--------|------|-------|-------|
| PNG | ✅ | ✅ | Preferred for screenshots |
| JPEG | ✅ | ✅ | Good for photographs |
| GIF | ✅ | ❌ | Animation not supported |
| BMP | ✅ | ❌ | Basic support |
| TIFF | ✅ | ❌ | Multi-page not supported |
| SVG | ⚠️ | ❌ | Rasterized for analysis |

### Image Type Classification

```python
class ImageType(Enum):
    SCREENSHOT = "screenshot"           # UI screenshots
    DIAGRAM = "diagram"                 # Technical diagrams
    FLOWCHART = "flowchart"            # Process flows
    UI_MOCKUP = "ui_mockup"            # Interface designs
    ARCHITECTURE = "architecture"       # System architecture
    CODE_SNIPPET = "code_snippet"      # Code examples
    CHART_GRAPH = "chart_graph"        # Data visualizations
    DOCUMENTATION_PAGE = "documentation_page"  # Full pages
    ERROR_MESSAGE = "error_message"     # Error screenshots
```

## Analysis Tasks

### Available Analysis Types

```python
class AnalysisTask(Enum):
    TEXT_EXTRACTION = "text_extraction"
    CONTENT_VALIDATION = "content_validation"
    QUALITY_ASSESSMENT = "quality_assessment"
    ACCESSIBILITY_CHECK = "accessibility_check"
    CONSISTENCY_VALIDATION = "consistency_validation"
    ERROR_DETECTION = "error_detection"
    COMPLETENESS_CHECK = "completeness_check"
    VISUAL_REGRESSION = "visual_regression"
```

### Task-Specific Analysis

#### Text Extraction
```python
# Basic text extraction
request = ImageAnalysisRequest(
    image_data=image_bytes,
    image_type=ImageType.DOCUMENTATION_PAGE,
    analysis_tasks=[AnalysisTask.TEXT_EXTRACTION]
)

result = await engine.analyze_image(request)
extracted_text = result.text_extraction.extracted_text
```

#### Quality Assessment
```python
# Comprehensive quality analysis
request = ImageAnalysisRequest(
    image_data=image_bytes,
    image_type=ImageType.SCREENSHOT,
    analysis_tasks=[AnalysisTask.QUALITY_ASSESSMENT],
    quality_threshold=0.8
)

result = await engine.analyze_image(request)
quality = result.quality_assessment
```

#### Content Validation
```python
# Validate specific content
request = ImageAnalysisRequest(
    image_data=image_bytes,
    image_type=ImageType.UI_MOCKUP,
    analysis_tasks=[AnalysisTask.CONTENT_VALIDATION],
    context={
        'expected_content': {
            'required_text': ['Login', 'Password', 'Submit'],
            'visual_elements': ['button', 'input field', 'logo']
        }
    }
)

result = await engine.analyze_image(request)
validation = result.content_validation
```

#### Accessibility Check
```python
# Accessibility compliance analysis
request = ImageAnalysisRequest(
    image_data=image_bytes,
    image_type=ImageType.DOCUMENTATION_PAGE,
    analysis_tasks=[AnalysisTask.ACCESSIBILITY_CHECK]
)

result = await engine.analyze_image(request)
accessibility = result.accessibility_results
```

## Quality Metrics

### Scoring System

All quality metrics use a 0.0 to 1.0 scale:
- **0.9-1.0**: Excellent quality
- **0.8-0.9**: Good quality
- **0.7-0.8**: Acceptable quality
- **0.6-0.7**: Poor quality (needs improvement)
- **0.0-0.6**: Unacceptable quality

### Quality Assessment Breakdown

#### Clarity Score
- **Method**: Laplacian variance calculation
- **Threshold**: > 100 for sharp images
- **Factors**: Edge definition, focus quality, resolution

#### Readability Score
- **Method**: Text contrast and size analysis
- **Factors**: Color contrast ratio, text size, background clarity
- **Accessibility**: WCAG compliance consideration

#### Completeness Score
- **Method**: Content density analysis
- **Varies by Type**: Different expectations for screenshots vs diagrams
- **Factors**: Information density, edge detection, content coverage

#### Accessibility Score
- **Method**: Multi-factor accessibility assessment
- **Factors**: Color contrast (50%), text size (40%), color diversity (10%)
- **Standards**: WCAG 2.1 AA compliance

## Usage Examples

### Basic Image Analysis

```python
async def analyze_documentation_image():
    """Analyze a documentation image for quality and content"""

    # Load image
    with open('docs/screenshot.png', 'rb') as f:
        image_data = f.read()

    # Create analysis request
    request = ImageAnalysisRequest(
        image_data=image_data,
        image_type=ImageType.SCREENSHOT,
        analysis_tasks=[
            AnalysisTask.TEXT_EXTRACTION,
            AnalysisTask.QUALITY_ASSESSMENT,
            AnalysisTask.ACCESSIBILITY_CHECK
        ]
    )

    # Analyze
    result = await engine.analyze_image(request)

    # Review results
    print(f"🔍 Analysis Results:")
    print(f"  Overall Confidence: {result.confidence:.3f}")
    print(f"  Processing Time: {result.processing_time:.2f}s")

    if result.text_extraction:
        print(f"  📝 Text Found: {len(result.text_extraction.extracted_text)} chars")
        print(f"  📊 OCR Confidence: {result.text_extraction.confidence:.3f}")

    if result.quality_assessment:
        qa = result.quality_assessment
        print(f"  🎯 Quality Score: {qa.overall_score:.3f}")
        print(f"    - Clarity: {qa.clarity_score:.3f}")
        print(f"    - Readability: {qa.readability_score:.3f}")
        print(f"    - Accessibility: {qa.accessibility_score:.3f}")

        if qa.issues_detected:
            print(f"  ⚠️ Issues: {', '.join(qa.issues_detected)}")

    return result
```

### Batch Image Validation

```python
async def validate_documentation_images():
    """Validate all images in documentation directory"""

    image_files = [
        'docs/api-overview.png',
        'docs/auth-flow.png',
        'docs/dashboard-screenshot.png'
    ]

    requests = []
    for file_path in image_files:
        with open(file_path, 'rb') as f:
            image_data = f.read()

        # Determine image type from filename
        if 'screenshot' in file_path:
            img_type = ImageType.SCREENSHOT
        elif 'flow' in file_path:
            img_type = ImageType.FLOWCHART
        else:
            img_type = ImageType.DOCUMENTATION_PAGE

        request = ImageAnalysisRequest(
            image_data=image_data,
            image_type=img_type,
            analysis_tasks=[
                AnalysisTask.QUALITY_ASSESSMENT,
                AnalysisTask.ACCESSIBILITY_CHECK,
                AnalysisTask.ERROR_DETECTION
            ],
            metadata={'file_path': file_path}
        )
        requests.append(request)

    # Batch analyze
    results = await engine.batch_analyze_images(requests)

    # Generate report
    total_images = len(results)
    passed_quality = sum(1 for r in results
                        if r.quality_assessment and r.quality_assessment.overall_score > 0.7)

    print(f"📊 Batch Validation Results:")
    print(f"  Total Images: {total_images}")
    print(f"  Passed Quality: {passed_quality}/{total_images}")
    print(f"  Success Rate: {passed_quality/total_images:.1%}")

    # Detailed issues
    for result in results:
        file_path = result.metadata.get('file_path', 'unknown')
        if result.quality_assessment and result.quality_assessment.issues_detected:
            print(f"  ⚠️ {file_path}: {', '.join(result.quality_assessment.issues_detected)}")
```

### Integration with Document Validation

```python
async def validate_document_with_images():
    """Validate a complete document including its images"""

    # Initialize validator
    validator = DocumentationImageValidator(engine, doc_service, metrics_service)

    # Validate specific document
    report = await validator.validate_document_images('api-guide-v2')

    print(f"📋 Document Image Validation Report:")
    print(f"  Document: api-guide-v2")
    print(f"  Images Analyzed: {report.total_images_analyzed}")
    print(f"  Overall Quality: {report.overall_quality_score:.3f}")
    print(f"  Accessibility: {report.accessibility_compliance:.3f}")
    print(f"  Content Accuracy: {report.content_accuracy:.3f}")
    print(f"  Processing Time: {report.processing_time:.1f}s")

    if report.issues_found:
        print(f"  🔍 Issues Found ({len(report.issues_found)}):")
        for issue in report.issues_found[:5]:  # Show first 5
            print(f"    - {issue['type']}: {issue['issue']}")

    if report.recommendations:
        print(f"  💡 Recommendations:")
        for rec in report.recommendations:
            print(f"    - {rec}")

    return report
```

### CRAG Enhancement with Images

```python
async def enhanced_query_with_images():
    """Process a query enhanced with image analysis"""

    # Setup CRAG with image enhancement
    enhancer = CRAGImageEnhancer(crag_system, engine)

    # Create query
    from src.agents.agentic_rag_system import RAGQuery, RAGTaskType
    query = RAGQuery(
        query_text="How do I configure SSL certificates in the dashboard?",
        task_type=RAGTaskType.TECHNICAL_CONTEXT,
        context={'domain': 'security', 'interface': 'dashboard'}
    )

    # Include relevant screenshots
    image_context = [
        {
            'data': load_image('docs/ssl-config-screen.png'),
            'type': 'screenshot',
            'expected_content': {
                'required_text': ['SSL', 'Certificate', 'Configure'],
                'visual_elements': ['form', 'button', 'input fields']
            }
        }
    ]

    # Process with image enhancement
    result = await enhancer.process_query_with_images(query, image_context)

    print(f"🧠 Enhanced Query Results:")
    print(f"  CRAG Confidence: {result['crag_result'].final_result.confidence:.3f}")
    print(f"  Image Analysis: {len(result['image_analysis'])} images")
    print(f"  Combined Confidence: {result['combined_confidence']:.3f}")
    print(f"  Enhanced Response: {result['enhanced_response'][:200]}...")

    return result
```

## Configuration

### Environment Setup

```bash
# Core image analysis settings
export IMAGE_ANALYSIS_ENABLED=true
export IMAGE_MAX_SIZE=10485760  # 10MB
export IMAGE_QUALITY_THRESHOLD=0.7

# OCR configuration
export TESSERACT_CONFIG="--oem 3 --psm 6"
export DEFAULT_OCR_LANGUAGE=eng

# Processing limits
export MAX_CONCURRENT_IMAGES=5
export IMAGE_PROCESSING_TIMEOUT=300

# AI model configuration
export VISION_MODEL="amazon.nova-pro-v1:0"
export ASSESSMENT_MODEL="anthropic.claude-3-5-sonnet-20241022-v2:0"
```

### Quality Thresholds Configuration

```python
# Configure quality thresholds for different image types
QUALITY_THRESHOLDS = {
    ImageType.SCREENSHOT: {
        'clarity_min': 0.6,
        'readability_min': 0.8,
        'accessibility_min': 0.8
    },
    ImageType.DIAGRAM: {
        'clarity_min': 0.8,
        'readability_min': 0.7,
        'accessibility_min': 0.7
    },
    ImageType.DOCUMENTATION_PAGE: {
        'clarity_min': 0.7,
        'readability_min': 0.8,
        'accessibility_min': 0.8
    }
}
```

## Testing

### Unit Tests

```bash
# Run image analysis tests
pytest tests/test_image_analysis.py -v

# Test with coverage
pytest tests/test_image_analysis.py --cov=src.agents.image_analysis_framework

# Performance tests
pytest tests/test_image_analysis.py::TestImageAnalysisPerformance
```

### Integration Tests

```bash
# Test full integration
pytest tests/test_image_analysis.py::TestImageAnalysisIntegration -v

# Test with real images (requires test data)
pytest tests/test_image_analysis.py --integration --test-images=tests/data/images/
```

### Performance Benchmarks

```bash
# Benchmark single image processing
pytest tests/test_image_analysis.py::test_performance_single_image --benchmark-only

# Benchmark batch processing
pytest tests/test_image_analysis.py::test_concurrent_analysis --benchmark-only
```

## Monitoring and Metrics

### Performance Metrics

The framework automatically collects metrics when integrated:

```python
# Metrics collected:
- Processing time per image
- Quality scores distribution
- OCR accuracy rates
- Error detection frequency
- Accessibility compliance rates
- Enhancement effectiveness
```

### Health Monitoring

```python
async def image_analysis_health_check():
    """Check image analysis system health"""

    health = await integration_manager.get_image_analysis_health_check()

    return {
        'status': health['status'],
        'components': health['components'],
        'test_processing_time': health.get('test_processing_time', 0),
        'last_check': datetime.utcnow().isoformat()
    }
```

### Error Tracking

```python
# Common error patterns tracked:
- Image loading failures
- OCR processing errors
- AI model timeout issues
- Memory usage spikes
- Quality assessment failures
```

## Best Practices

### Image Preparation

1. **Optimal Resolution**: 800x600 minimum for text-heavy images
2. **File Format**: PNG for screenshots, JPEG for photos
3. **Compression**: Balance file size with quality (< 10MB recommended)
4. **Color Mode**: RGB for consistent analysis

### Content Validation

1. **Clear Requirements**: Define expected content explicitly
2. **Context Awareness**: Provide relevant context for AI analysis
3. **Threshold Tuning**: Adjust quality thresholds based on use case
4. **Regular Validation**: Implement automated validation in CI/CD

### Performance Optimization

1. **Batch Processing**: Use batch analysis for multiple images
2. **Async Processing**: Leverage async capabilities for I/O operations
3. **Resource Limits**: Configure memory and processing limits
4. **Caching**: Implement caching for repeated analyses

### Accessibility Compliance

1. **Color Contrast**: Ensure minimum 4.5:1 contrast ratio
2. **Text Size**: Maintain readable font sizes (12pt minimum)
3. **Alt Text**: Provide meaningful alternative text
4. **Color Independence**: Don't rely solely on color for information

## Troubleshooting

### Common Issues

#### Low OCR Accuracy
```python
# Check image quality first
if result.text_extraction.confidence < 0.5:
    # Try preprocessing
    enhanced_image, _ = await preprocessor.preprocess_image(
        image_data, enhancement_type="enhance_contrast"
    )
    # Re-analyze with enhanced image
```

#### Poor Quality Scores
```python
# Identify specific issues
if result.quality_assessment.clarity_score < 0.7:
    print("Image is blurry - consider higher resolution")
if result.quality_assessment.readability_score < 0.7:
    print("Text contrast is poor - adjust colors")
```

#### High Processing Times
```python
# Optimize for performance
request.analysis_tasks = [AnalysisTask.QUALITY_ASSESSMENT]  # Reduce tasks
# Use smaller images or batch processing
```

### Debug Mode

```python
import logging
logging.getLogger('src.agents.image_analysis_framework').setLevel(logging.DEBUG)

# Enable detailed analysis logging
request.metadata['debug'] = True
result = await engine.analyze_image(request)
```

## Future Enhancements

### Planned Features

1. **Video Analysis**: Support for animated GIFs and video content
2. **3D Visualization**: Analysis of 3D diagrams and models
3. **Custom Models**: Domain-specific vision models
4. **Real-time Processing**: Streaming image analysis
5. **Advanced OCR**: Handwriting and mathematical notation support

### Extensibility

```python
# Custom quality analyzers
class DomainSpecificAnalyzer(VisualQualityAnalyzer):
    async def assess_domain_quality(self, image):
        # Custom domain logic
        pass

# Custom content validators
class APIDocumentationValidator(ContentValidator):
    async def validate_api_content(self, image, api_spec):
        # API-specific validation
        pass
```

## API Reference

See the complete API documentation:
- `src/agents/image_analysis_framework.py` - Core framework implementation
- `src/agents/image_analysis_integration.py` - Integration components
- `tests/test_image_analysis.py` - Test examples and usage patterns
- `docs/api-reference.md` - Complete API documentation