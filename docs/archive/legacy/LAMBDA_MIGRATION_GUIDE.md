# Lambda Functions Migration Guide

## Overview

This guide explains how to migrate from the original Lambda-only architecture to the new hybrid FastAPI + Lambda system that supports human review workflows.

## Architecture Changes

### Original Architecture (V1)
```
GitHub Webhook → Lambda → DynamoDB → EventBridge → Document Orchestrator → S3/Confluence
```

### New Architecture (V2)
```
GitHub Webhook → Lambda V2 → FastAPI Review API → Human Review → Document Processor → S3/Confluence
                     ↓                               ↓                    ↓
                 DynamoDB                     PostgreSQL            WebSocket Notifications
```

## Migration Steps

### Phase 1: Deploy New Infrastructure

1. **Deploy FastAPI Application**
   ```bash
   # Start the FastAPI server
   cd /Users/genkinsforge-svc/kinexusai
   uvicorn src.api.main:app --reload --port 8000
   ```

2. **Set Up PostgreSQL Database**
   ```bash
   # Run database setup script
   python scripts/setup_database.py
   ```

3. **Configure Environment Variables**
   ```bash
   export FASTAPI_BASE_URL="http://localhost:8000"
   export SERVICE_TOKEN="your-service-jwt-token"
   export DATABASE_URL="postgresql://kinexus:password@localhost/kinexusai"
   ```

### Phase 2: Update Lambda Functions

#### Option A: Gradual Migration (Recommended)

1. **Deploy V2 Lambda functions alongside V1**
   - Keep existing functions running
   - Deploy new V2 functions with different names
   - Use environment variables to control routing

2. **Update EventBridge Rules**
   ```python
   # Route to V2 functions for new repositories
   if repository in NEW_REPOSITORIES:
       target_function = "github_webhook_handler_v2"
   else:
       target_function = "github_webhook_handler"  # Legacy
   ```

3. **Test with Pilot Repositories**
   - Start with non-critical repositories
   - Monitor review workflow performance
   - Gather user feedback

#### Option B: Direct Replacement

1. **Update Lambda Function Code**
   - Replace `github_webhook_handler.py` with `github_webhook_handler_v2.py`
   - Replace `document_orchestrator.py` with `document_processor_v2.py`

2. **Update Environment Variables**
   ```bash
   # Add to Lambda environment
   FASTAPI_BASE_URL=https://your-api-domain.com
   SERVICE_TOKEN=your-jwt-token
   ```

### Phase 3: Data Migration

#### Migrate Existing Documents

```python
# Migration script example
import boto3
import httpx

def migrate_documents():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('kinexus-documents')

    # Scan existing documents
    response = table.scan()

    for item in response['Items']:
        # Convert to new format
        document_data = {
            "external_id": item['document_id'],
            "source_system": "legacy",
            "path": item.get('s3_key', ''),
            "title": item.get('title', 'Migrated Document'),
            "document_type": "general",
            "doc_metadata": {
                "migrated_from": "dynamodb",
                "original_id": item['document_id']
            }
        }

        # Create in new system
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FASTAPI_BASE_URL}/api/documents",
                headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
                json=document_data
            )
```

#### Migrate Change History

```python
def migrate_changes():
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('kinexus-changes')

    # Process recent changes that haven't been reviewed
    recent_changes = table.scan(
        FilterExpression='#status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': 'pending'}
    )

    for change in recent_changes['Items']:
        # Create review for pending changes
        create_review_for_change(change)
```

## Function-by-Function Migration

### 1. GitHub Webhook Handler

**Changes:**
- ✅ Added AI impact assessment
- ✅ Integration with review API
- ✅ Enhanced error handling
- ✅ Backward compatibility maintained

**Migration:**
```python
# Old function call
await orchestrator.process_change(change_id)

# New function call
await create_review_via_api(document_id, change_id, impact_score, ai_assessment, change_data)
```

### 2. Document Orchestrator → Document Processor

**Changes:**
- ✅ Now processes APPROVED reviews instead of raw changes
- ✅ Generates final documents after human approval
- ✅ Updates source systems (GitHub, Confluence)
- ✅ Integrates with version control

**Migration:**
```python
# Old: Process all changes automatically
async def process_change(change_id):
    analysis = await analyze_documentation_impact(change_data)
    result = await create_documentation(change_data, analysis)

# New: Process only approved reviews
async def process_approved_review(review_data):
    content = await generate_document_content(review_data)
    content = apply_modifications(content, review_data['modifications'])
    result = await update_source_document(document_data, content, review_data)
```

### 3. Integration Clients

**Changes:**
- ✅ Enhanced GitHub integration with PR support
- ✅ Proper Confluence API integration
- ✅ SharePoint integration framework
- ✅ Consistent error handling

**Migration:**
```python
# Old: Direct S3 storage
s3.put_object(Bucket=bucket, Key=key, Body=content)

# New: Multi-target publishing
await github_client.update_document(external_id, path, content)
await confluence_client.update_document(external_id, path, content)
s3_key = await save_to_s3(review_data, content)  # Backup
```

## Testing Strategy

### 1. Unit Tests

```python
# Test new webhook handler
def test_github_webhook_v2():
    event = create_test_webhook_event()
    result = lambda_handler_sync(event, None)
    assert result['statusCode'] == 200
    assert 'reviews_created' in json.loads(result['body'])

# Test document processor
def test_document_processor():
    review_data = create_test_review_data()
    result = process_approved_review(review_data)
    assert result['status'] == 'success'
```

### 2. Integration Tests

```python
# End-to-end workflow test
async def test_complete_workflow():
    # 1. Send webhook
    webhook_result = await send_test_webhook()

    # 2. Verify review created
    reviews = await get_pending_reviews()
    assert len(reviews) > 0

    # 3. Approve review
    await approve_review(reviews[0]['id'])

    # 4. Verify document published
    # Check S3, GitHub, Confluence
```

### 3. Performance Tests

```bash
# Load test webhook handling
wrk -t12 -c400 -d30s --script=webhook_test.lua http://localhost:8000/api/webhooks/github

# Monitor review processing times
curl http://localhost:8000/api/reviews/metrics/summary
```

## Rollback Plan

### If Issues Occur

1. **Immediate Rollback**
   ```bash
   # Switch EventBridge rules back to V1 functions
   aws events put-rule --name "github-changes" --targets="arn:aws:lambda:region:account:function:github_webhook_handler"
   ```

2. **Data Rollback**
   ```python
   # Export review data before rollback
   reviews = get_all_pending_reviews()
   save_reviews_to_s3(reviews)

   # Convert reviews back to change records
   for review in reviews:
       create_legacy_change_record(review)
   ```

3. **Gradual Rollback**
   - Move repositories back to V1 one by one
   - Monitor for any data consistency issues
   - Preserve review data for future migration attempts

## Monitoring & Observability

### Key Metrics to Track

1. **Review Workflow Metrics**
   ```python
   # Review processing times
   avg_review_time = get_avg_review_time()

   # Queue depths
   pending_count = get_pending_reviews_count()

   # Approval rates
   approval_rate = get_approval_rate()
   ```

2. **System Performance**
   ```python
   # API response times
   api_latency = get_api_latency_metrics()

   # Lambda execution times
   lambda_duration = get_lambda_metrics()

   # Database performance
   db_query_time = get_db_metrics()
   ```

3. **Error Rates**
   ```python
   # Webhook processing errors
   webhook_error_rate = get_webhook_error_rate()

   # Review creation failures
   review_creation_errors = get_review_creation_errors()

   # Document publication failures
   publication_errors = get_publication_errors()
   ```

### Alerting

```yaml
# CloudWatch Alarms
review_queue_backup:
  metric: pending_reviews_count
  threshold: 100
  action: notify_admin

api_error_rate:
  metric: api_5xx_error_rate
  threshold: 5%
  action: page_oncall

lambda_failures:
  metric: lambda_error_rate
  threshold: 10%
  action: slack_notification
```

## Timeline

### Week 1: Infrastructure
- ✅ Deploy FastAPI application
- ✅ Set up PostgreSQL database
- ✅ Create service accounts and tokens

### Week 2: Lambda Updates
- ✅ Deploy V2 Lambda functions
- ✅ Update environment variables
- ✅ Configure EventBridge routing

### Week 3: Data Migration
- Migrate existing documents
- Import change history
- Test data consistency

### Week 4: Validation
- End-to-end testing
- Performance validation
- User acceptance testing

### Week 5: Rollout
- Gradual migration of repositories
- Monitor system performance
- Gather user feedback

## Success Criteria

✅ **All webhooks processed successfully**
✅ **Review workflow operational**
✅ **No data loss during migration**
✅ **Performance within acceptable limits**
✅ **User training completed**
✅ **Rollback procedures tested**

## Support & Troubleshooting

### Common Issues

1. **Service Token Authentication**
   ```bash
   # Test token validity
   curl -H "Authorization: Bearer $SERVICE_TOKEN" http://localhost:8000/api/auth/me
   ```

2. **Database Connection Issues**
   ```python
   # Test database connectivity
   from src.database.connection import db_manager
   health = db_manager.health_check()
   ```

3. **WebSocket Connection Problems**
   ```javascript
   // Test WebSocket connection
   const ws = new WebSocket('ws://localhost:8000/api/ws/notifications?token=...');
   ```

### Getting Help

- **Documentation**: Check `/docs` endpoint for API documentation
- **Logs**: Monitor CloudWatch logs for Lambda functions
- **Metrics**: Use CloudWatch dashboards for system health
- **Support**: Contact the development team for urgent issues

This migration maintains full backward compatibility while adding powerful new human review capabilities. The gradual migration approach minimizes risk while allowing teams to adapt to the new workflow at their own pace.