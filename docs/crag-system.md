# Self-Corrective RAG (CRAG) System

## Overview

The Self-Corrective RAG (CRAG) system enhances Kinexus AI's retrieval-augmented generation capabilities with iterative quality assessment and automatic correction mechanisms. CRAG continuously improves response quality through intelligent feedback loops and multi-layered validation.

## Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   RAG Query     │───▶│  Quality         │───▶│  Correction     │
│   Processing    │    │  Assessment      │    │  Engine         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Base RAG       │    │  7 Quality       │    │  7 Correction   │
│  System         │    │  Metrics         │    │  Strategies     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 1. Quality Assessment Engine

**Quality Metrics Evaluated:**
- **Relevance** (25%): How well the response addresses the query
- **Accuracy** (20%): Factual correctness of the information
- **Completeness** (15%): Coverage of all query aspects
- **Coherence** (15%): Logical flow and clarity
- **Factual Consistency** (15%): Agreement across sources
- **Source Reliability** (5%): Trustworthiness of sources
- **Temporal Validity** (5%): Currency of information

### 2. Correction Engine

**Correction Strategies:**
- **Retrieve More**: Expand source collection for completeness
- **Refine Query**: Improve query specificity for relevance
- **Validate Sources**: Filter unreliable information sources
- **Cross Reference**: Reconcile information across sources
- **Fact Check**: Verify claims against available sources
- **Synthesize Better**: Improve response coherence and flow
- **Temporal Update**: Ensure information currency

### 3. Iterative Improvement Loop

```python
while quality_score < threshold and iterations < max_iterations:
    1. Assess response quality across 7 metrics
    2. Identify specific improvement areas
    3. Apply targeted correction strategies
    4. Re-evaluate improved response
    5. Continue if meaningful improvement detected
```

## Implementation

### Core Classes

#### `SelfCorrectiveRAG`
Main orchestrator that coordinates quality assessment and correction.

```python
from src.agents.self_corrective_rag import SelfCorrectiveRAG
from src.agents.agentic_rag_system import RAGQuery, RAGTaskType

# Initialize CRAG system
crag = SelfCorrectiveRAG(base_rag_system, model_config)

# Process query with automatic correction
query = RAGQuery(
    query_text="How do I implement error handling in Python?",
    task_type=RAGTaskType.CODE_ANALYSIS,
    context={"language": "python"}
)

result = await crag.process_query(query)
```

#### `QualityAssessor`
Evaluates response quality across multiple dimensions.

```python
# Quality assessment breakdown
assessment = await quality_assessor.assess_quality(query, result)

print(f"Overall Score: {assessment.overall_score:.3f}")
print(f"Relevance: {assessment.scores[QualityMetric.RELEVANCE]:.3f}")
print(f"Accuracy: {assessment.scores[QualityMetric.ACCURACY]:.3f}")
print(f"Issues: {assessment.issues_identified}")
print(f"Suggested Corrections: {assessment.suggested_corrections}")
```

#### `CorrectionEngine`
Applies targeted improvements based on quality assessment.

```python
# Apply corrections iteratively
corrected_result = await correction_engine.apply_corrections(context)

# Track applied corrections
print(f"Corrections Applied: {context.correction_history}")
print(f"Improvement: {corrected_result.confidence - original_result.confidence}")
```

### Integration Components

#### `CRAGDocumentProcessor`
Integrates CRAG with document management workflows.

```python
from src.agents.crag_integration import CRAGDocumentProcessor

processor = CRAGDocumentProcessor(crag_system, document_service, metrics_service)

# Process document queries with CRAG enhancement
result = await processor.process_document_query(
    "What's the authentication process?",
    {"document_type": "api_docs", "section": "auth"}
)

# Validate document accuracy
validation = await processor.validate_document_accuracy("doc-123")
```

#### `CRAGWebhookProcessor`
Enhances webhook processing with CRAG quality assurance.

```python
# Process GitHub webhook with CRAG
webhook_processor = CRAGWebhookProcessor(crag_processor, agent_supervisor)

results = await webhook_processor.process_github_webhook({
    "repository": {"full_name": "org/repo"},
    "commits": [{"message": "Add new feature", "modified": ["src/auth.py"]}]
})
```

## Configuration

### Environment Setup

```bash
# Core CRAG settings
export CRAG_QUALITY_THRESHOLD=0.75
export CRAG_MAX_ITERATIONS=3
export CRAG_ENABLE_METRICS=true

# Model configuration
export CRAG_PRIMARY_MODEL="anthropic.claude-3-5-sonnet-20241022-v2:0"
export CRAG_ASSESSMENT_MODEL="anthropic.claude-3-5-sonnet-20241022-v2:0"

# AWS configuration
export AWS_DEFAULT_REGION=us-east-1
```

### Configuration Profiles

```python
from src.config.crag_config import CRAGConfigFactory, QualityProfile

# Development: Fast processing, lower quality thresholds
dev_config = CRAGConfigFactory.create_development_config()

# Staging: Balanced speed and quality
staging_config = CRAGConfigFactory.create_staging_config()

# Production: Highest quality, comprehensive validation
prod_config = CRAGConfigFactory.create_production_config()
```

### Quality Profiles

| Profile | Quality Threshold | Max Iterations | Processing Time | Use Case |
|---------|------------------|----------------|-----------------|----------|
| Fast | 0.65 | 1 | ~60s | Development, quick responses |
| Balanced | 0.75 | 2 | ~180s | Staging, general use |
| Thorough | 0.85 | 4 | ~600s | Production, critical docs |

## Performance Metrics

### Key Performance Indicators

```python
# Get performance metrics
metrics = crag_system.get_performance_metrics(results)

print(f"Success Rate: {metrics['success_rate']:.1%}")
print(f"Average Improvement: {metrics['average_improvement_score']:.3f}")
print(f"Average Processing Time: {metrics['average_processing_time']:.1f}s")
print(f"Most Effective Corrections: {metrics['correction_frequency']}")
```

### Performance Analysis

```python
from src.agents.crag_integration import CRAGPerformanceAnalyzer

analyzer = CRAGPerformanceAnalyzer(metrics_service)
analysis = await analyzer.analyze_performance(time_period_days=7)

# Optimization recommendations
for recommendation in analysis['recommendations']:
    print(f"💡 {recommendation}")
```

## Usage Examples

### Basic Document Query

```python
async def process_documentation_query():
    # Initialize CRAG system
    crag = SelfCorrectiveRAG(base_rag, model_config)

    # Create query
    query = RAGQuery(
        query_text="How do I configure SSL certificates?",
        task_type=RAGTaskType.TECHNICAL_CONTEXT,
        context={"domain": "security", "urgency": "high"}
    )

    # Process with CRAG
    result = await crag.process_query(query)

    # Analyze results
    print(f"Final Quality Score: {result.quality_assessment.overall_score:.3f}")
    print(f"Corrections Applied: {len(result.corrections_applied)}")
    print(f"Processing Time: {result.total_processing_time:.1f}s")
    print(f"Answer: {result.final_result.answer}")

    return result
```

### Batch Processing

```python
async def batch_process_queries():
    queries = [
        RAGQuery("How to deploy to production?", RAGTaskType.DOCUMENT_SEARCH, {}),
        RAGQuery("What's the API rate limit?", RAGTaskType.TECHNICAL_CONTEXT, {}),
        RAGQuery("How to handle errors?", RAGTaskType.CODE_ANALYSIS, {})
    ]

    # Process all queries with CRAG
    results = await crag.batch_process(queries)

    # Analyze batch performance
    for i, result in enumerate(results):
        print(f"Query {i+1}: Quality {result.quality_assessment.overall_score:.3f}")
```

### Document Validation

```python
async def validate_documentation():
    processor = CRAGDocumentProcessor(crag, doc_service, metrics_service)

    # Validate specific document
    validation = await processor.validate_document_accuracy("api-guide-123")

    if validation.quality_assessment.overall_score < 0.8:
        print("⚠️ Document quality issues detected:")
        for issue in validation.quality_assessment.issues_identified:
            print(f"  - {issue}")
    else:
        print("✅ Document validation passed")
```

### Webhook Integration

```python
async def process_code_changes(webhook_data):
    webhook_processor = CRAGWebhookProcessor(crag_processor, supervisor)

    # Process GitHub webhook with CRAG enhancement
    results = await webhook_processor.process_github_webhook(webhook_data)

    # Generate documentation updates
    for result in results:
        if result.quality_assessment.overall_score > 0.8:
            print(f"📝 Suggested update: {result.final_result.answer[:100]}...")
```

## Testing

### Unit Tests

```bash
# Run CRAG-specific tests
pytest tests/test_crag_system.py -v

# Run with coverage
pytest tests/test_crag_system.py --cov=src.agents.self_corrective_rag
```

### Performance Benchmarks

```bash
# Benchmark processing time
pytest tests/test_crag_system.py::TestCRAGPerformance::test_processing_time_benchmark

# Memory usage testing
pytest tests/test_crag_system.py --benchmark-only
```

### Integration Tests

```bash
# Test full integration
pytest tests/test_crag_integration.py -v

# Test with real AWS services (requires credentials)
pytest tests/test_crag_integration.py --integration
```

## Monitoring and Observability

### Metrics Collection

CRAG automatically collects performance metrics when enabled:

```python
# Metrics automatically collected:
- Processing time per query
- Quality scores across all metrics
- Correction effectiveness
- Improvement trends
- Error rates and patterns
```

### Logging

```python
import logging

# Configure CRAG logging
logging.getLogger('src.agents.self_corrective_rag').setLevel(logging.INFO)

# Key log events:
# - Quality assessments
# - Correction applications
# - Performance metrics
# - Error conditions
```

### Health Checks

```python
async def health_check():
    """Verify CRAG system health"""
    try:
        # Test basic functionality
        test_query = RAGQuery("test", RAGTaskType.DOCUMENT_SEARCH, {})
        result = await crag.process_query(test_query)

        return {
            "status": "healthy",
            "processing_time": result.total_processing_time,
            "quality_score": result.quality_assessment.overall_score
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Best Practices

### Configuration

1. **Start with Balanced Profile**: Use `QualityProfile.BALANCED` for most use cases
2. **Tune Thresholds**: Adjust quality thresholds based on your accuracy requirements
3. **Monitor Performance**: Track processing times and adjust iteration limits
4. **Environment Specific**: Use different configurations for dev/staging/prod

### Query Optimization

1. **Specific Context**: Provide relevant context in queries for better results
2. **Appropriate Task Types**: Use correct `RAGTaskType` for your use case
3. **Reasonable Limits**: Set appropriate `max_results` for your needs

### Performance Optimization

1. **Batch Processing**: Use `batch_process()` for multiple queries
2. **Caching**: Enable result caching in production environments
3. **Parallel Limits**: Tune parallel processing based on your infrastructure
4. **Model Selection**: Use appropriate models for assessment vs. generation

### Quality Management

1. **Regular Validation**: Periodically validate document accuracy
2. **Feedback Loops**: Enable learning feedback for continuous improvement
3. **Correction Analysis**: Monitor which corrections are most effective
4. **Quality Trends**: Track quality improvements over time

## Troubleshooting

### Common Issues

#### Low Quality Scores
```python
# Check individual metric scores
for metric, score in assessment.scores.items():
    if score < 0.7:
        print(f"Low {metric.value}: {score:.3f}")
```

#### Slow Processing
```python
# Reduce iterations or adjust thresholds
config.max_iterations = 2
config.quality_threshold = 0.7
```

#### High Resource Usage
```python
# Limit parallel processing
config.parallel_processing_limit = 3
config.processing_timeout_seconds = 120
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('src.agents.self_corrective_rag').setLevel(logging.DEBUG)

# Add custom debugging
crag.debug_mode = True  # If implemented
```

## Future Enhancements

### Planned Features

1. **Adaptive Thresholds**: Dynamic quality thresholds based on query complexity
2. **Learning Feedback**: Continuous improvement from user feedback
3. **Multi-Modal Support**: Integration with image and document analysis
4. **Real-time Optimization**: Runtime performance optimization
5. **Custom Metrics**: Domain-specific quality metrics

### Extensibility

The CRAG system is designed for extensibility:

```python
# Custom quality metrics
class CustomQualityMetric(QualityMetric):
    DOMAIN_EXPERTISE = "domain_expertise"

# Custom correction strategies
class CustomCorrectionAction(CorrectionAction):
    DOMAIN_VALIDATION = "domain_validation"

# Custom assessors
class DomainSpecificAssessor(QualityAssessor):
    async def assess_domain_expertise(self, query, result):
        # Custom assessment logic
        pass
```

## API Reference

See the full API documentation in:
- `src/agents/self_corrective_rag.py` - Core CRAG implementation
- `src/agents/crag_integration.py` - Integration components
- `src/config/crag_config.py` - Configuration management
- `tests/test_crag_system.py` - Test examples and usage patterns