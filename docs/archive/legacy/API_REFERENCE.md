# Kinexus AI: API Reference

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL and Versioning](#base-url-and-versioning)
- [Core APIs](#core-apis)
- [Integration APIs](#integration-apis)
- [Management APIs](#management-apis)
- [Webhook APIs](#webhook-apis)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [SDKs and Examples](#sdks-and-examples)

## Overview

The Kinexus AI API provides comprehensive access to all system functionality, enabling integration with existing enterprise systems and custom application development. The API follows RESTful principles with JSON payloads and standard HTTP methods.

### API Capabilities
- **Change Management**: Submit and track system changes
- **Documentation Operations**: Create, update, and retrieve documentation
- **Agent Control**: Manage and monitor AI agents
- **Quality Assurance**: Access quality metrics and compliance data
- **Integration Management**: Configure and monitor external integrations

## Authentication

Kinexus AI uses multiple authentication methods to support different integration scenarios.

### API Key Authentication
```http
GET /api/v1/documents
Authorization: Bearer sk_kinexus_abc123...
Content-Type: application/json
```

### AWS IAM Authentication
```python
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

# Using AWS credentials
session = boto3.Session()
credentials = session.get_credentials()
region = 'us-east-1'

request = AWSRequest(
    method='GET',
    url='https://api.kinexusai.com/api/v1/documents',
    headers={'Content-Type': 'application/json'}
)

SigV4Auth(credentials, 'kinexus', region).add_auth(request)
```

### OAuth 2.0 (Enterprise SSO)
```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=your_client_id&
client_secret=your_client_secret&
scope=read:documents write:documents
```

## Base URL and Versioning

### Production Environment
```
Base URL: https://api.kinexusai.com
Current Version: v1
Full API URL: https://api.kinexusai.com/api/v1/
```

### Version Strategy
- **v1**: Current stable version (2025)
- **v2**: Next major version (planned 2026)
- **beta**: Preview features and experimental endpoints

## Core APIs

### Documents API

#### List Documents
```http
GET /api/v1/documents
```

**Parameters:**
- `limit` (optional): Number of results (1-100, default: 20)
- `offset` (optional): Pagination offset (default: 0)
- `status` (optional): Filter by status (`active`, `draft`, `archived`)
- `type` (optional): Filter by type (`wiki`, `api_doc`, `runbook`, `guide`)
- `search` (optional): Full-text search query

**Response:**
```json
{
  "data": [
    {
      "id": "doc_12345",
      "title": "API Integration Guide",
      "type": "guide",
      "status": "active",
      "url": "https://wiki.company.com/api-guide",
      "last_updated": "2025-09-26T10:30:00Z",
      "quality_score": 92,
      "compliance_status": "compliant",
      "metadata": {
        "author": "john.doe@company.com",
        "reviewers": ["jane.smith@company.com"],
        "tags": ["api", "integration", "developer"],
        "word_count": 2456
      }
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

#### Get Document Details
```http
GET /api/v1/documents/{document_id}
```

**Response:**
```json
{
  "id": "doc_12345",
  "title": "API Integration Guide", 
  "content": "# API Integration Guide\n\nThis guide covers...",
  "type": "guide",
  "status": "active",
  "url": "https://wiki.company.com/api-guide",
  "created_at": "2025-09-01T09:00:00Z",
  "last_updated": "2025-09-26T10:30:00Z",
  "quality_metrics": {
    "score": 92,
    "readability": 85,
    "completeness": 95,
    "accuracy": 90,
    "freshness": 98
  },
  "compliance": {
    "status": "compliant",
    "checks": [
      {"rule": "accessibility", "status": "passed"},
      {"rule": "security_review", "status": "passed"},
      {"rule": "style_guide", "status": "passed"}
    ]
  },
  "metadata": {
    "author": "john.doe@company.com",
    "reviewers": ["jane.smith@company.com"],
    "tags": ["api", "integration", "developer"],
    "word_count": 2456,
    "reading_time": "12 minutes",
    "related_documents": ["doc_12346", "doc_12347"]
  },
  "change_history": [
    {
      "change_id": "chg_789",
      "timestamp": "2025-09-26T10:30:00Z",
      "type": "content_update",
      "summary": "Updated authentication section",
      "agent": "content-creator",
      "human_reviewer": "jane.smith@company.com"
    }
  ]
}
```

#### Create Document
```http
POST /api/v1/documents
Content-Type: application/json

{
  "title": "New API Endpoint Documentation",
  "type": "api_doc",
  "content": "# New API Endpoint\n\nThis endpoint provides...",
  "metadata": {
    "author": "system@kinexusai.com",
    "tags": ["api", "new-feature"],
    "related_systems": ["payment-service", "user-service"]
  },
  "target_platforms": [
    {
      "platform": "confluence",
      "space": "DEV",
      "parent_page": "API Documentation"
    }
  ]
}
```

### Changes API

#### Submit Change Event
```http
POST /api/v1/changes
Content-Type: application/json

{
  "source": "jira",
  "type": "feature_release",
  "data": {
    "issue_key": "PROJ-1234",
    "summary": "New payment processing API",
    "description": "Added support for cryptocurrency payments",
    "components": ["payment-service", "user-interface"],
    "impact_level": "medium",
    "release_date": "2025-09-30T00:00:00Z"
  },
  "context": {
    "project": "payment-platform",
    "team": "payments-team",
    "environment": "production"
  }
}
```

**Response:**
```json
{
  "change_id": "chg_67890",
  "status": "processing",
  "estimated_completion": "2025-09-26T11:00:00Z",
  "agents_assigned": [
    "change-analyzer",
    "content-creator",
    "quality-controller"
  ],
  "affected_documents": [
    {
      "document_id": "doc_12345",
      "action": "update_required",
      "sections": ["authentication", "endpoints"]
    }
  ]
}
```

#### Get Change Status
```http
GET /api/v1/changes/{change_id}
```

**Response:**
```json
{
  "change_id": "chg_67890",
  "status": "completed",
  "submitted_at": "2025-09-26T10:00:00Z",
  "completed_at": "2025-09-26T10:45:00Z",
  "processing_time": "45 minutes",
  "impact_analysis": {
    "affected_documents": 5,
    "new_documents_created": 2,
    "updates_made": 3,
    "quality_improvements": 1
  },
  "agent_activities": [
    {
      "agent": "change-analyzer",
      "action": "impact_analysis",
      "duration": "2 minutes",
      "result": "identified 5 affected documents"
    },
    {
      "agent": "content-creator", 
      "action": "content_generation",
      "duration": "35 minutes",
      "result": "generated 2 new documents, updated 3 existing"
    }
  ],
  "human_reviews": [
    {
      "reviewer": "tech.lead@company.com",
      "status": "approved",
      "comments": "Looks good, clear documentation",
      "reviewed_at": "2025-09-26T10:40:00Z"
    }
  ]
}
```

### Agents API

#### List Agents
```http
GET /api/v1/agents
```

**Response:**
```json
{
  "agents": [
    {
      "id": "agent_orchestrator",
      "name": "Documentation Orchestrator",
      "model": "claude-4-opus-4.1",
      "status": "active",
      "current_tasks": 3,
      "queue_length": 12,
      "performance_metrics": {
        "avg_response_time": "2.3s",
        "success_rate": 98.5,
        "quality_score": 94
      }
    },
    {
      "id": "agent_change_analyzer",
      "name": "Change Analyzer",
      "model": "claude-4-sonnet",
      "status": "active", 
      "current_tasks": 1,
      "queue_length": 5,
      "performance_metrics": {
        "avg_response_time": "1.1s",
        "success_rate": 99.2,
        "quality_score": 91
      }
    }
  ]
}
```

#### Get Agent Details
```http
GET /api/v1/agents/{agent_id}
```

#### Control Agent
```http
POST /api/v1/agents/{agent_id}/actions
Content-Type: application/json

{
  "action": "pause" | "resume" | "restart",
  "reason": "Scheduled maintenance"
}
```

## Integration APIs

### Source System Integration

#### Configure Jira Integration
```http
POST /api/v1/integrations/jira
Content-Type: application/json

{
  "base_url": "https://company.atlassian.net",
  "authentication": {
    "type": "bearer_token",
    "token": "ATATT3xFfGF0..."
  },
  "projects": ["PROJ", "DEV", "OPS"],
  "webhook_events": [
    "issue_created",
    "issue_updated", 
    "issue_deleted"
  ],
  "field_mappings": {
    "impact_level": "customfield_10001",
    "affected_systems": "customfield_10002"
  }
}
```

#### Configure Git Integration
```http
POST /api/v1/integrations/git
Content-Type: application/json

{
  "provider": "github",
  "repositories": [
    {
      "owner": "company",
      "repo": "payment-service",
      "webhook_events": ["push", "pull_request"]
    }
  ],
  "authentication": {
    "type": "github_app",
    "app_id": "123456",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----..."
  }
}
```

### Target System Integration

#### Configure Confluence Integration
```http
POST /api/v1/integrations/confluence
Content-Type: application/json

{
  "base_url": "https://company.atlassian.net/wiki",
  "authentication": {
    "type": "personal_access_token",
    "token": "ATATT3xFfGF0..."
  },
  "spaces": [
    {
      "key": "DEV",
      "name": "Developer Documentation",
      "auto_publish": true,
      "review_required": false
    },
    {
      "key": "OPS", 
      "name": "Operations",
      "auto_publish": false,
      "review_required": true
    }
  ],
  "templates": {
    "api_doc": "API Documentation Template",
    "runbook": "Operations Runbook Template"
  }
}
```

## Management APIs

### Quality Management

#### Get Quality Metrics
```http
GET /api/v1/quality/metrics
```

**Parameters:**
- `period`: Time period (`24h`, `7d`, `30d`, `90d`)
- `document_type`: Filter by document type
- `team`: Filter by team

**Response:**
```json
{
  "overall_quality": {
    "score": 89.4,
    "trend": "+2.1%",
    "total_documents": 1247
  },
  "quality_dimensions": {
    "accuracy": {"score": 92.1, "trend": "+1.8%"},
    "completeness": {"score": 87.3, "trend": "+3.2%"},
    "readability": {"score": 85.9, "trend": "-0.5%"},
    "freshness": {"score": 93.2, "trend": "+4.1%"}
  },
  "compliance": {
    "overall_compliance": 94.7,
    "failed_checks": 12,
    "common_issues": [
      {"issue": "missing_accessibility_alt_text", "count": 5},
      {"issue": "outdated_security_info", "count": 4}
    ]
  }
}
```

#### Get Quality Report
```http
GET /api/v1/quality/reports/{report_id}
```

### User Management

#### List Users
```http
GET /api/v1/users
```

#### Create User
```http
POST /api/v1/users
Content-Type: application/json

{
  "email": "new.user@company.com",
  "name": "New User",
  "role": "editor",
  "teams": ["development", "documentation"],
  "permissions": [
    "read:documents",
    "write:documents",
    "review:changes"
  ]
}
```

## Webhook APIs

### Webhook Registration

#### Register Webhook
```http
POST /api/v1/webhooks
Content-Type: application/json

{
  "url": "https://your-system.com/webhooks/kinexus",
  "events": [
    "document.created",
    "document.updated", 
    "change.completed",
    "quality.alert"
  ],
  "secret": "your_webhook_secret",
  "active": true
}
```

### Webhook Events

#### Document Events
```json
{
  "event": "document.updated",
  "timestamp": "2025-09-26T10:30:00Z",
  "data": {
    "document_id": "doc_12345",
    "title": "API Integration Guide",
    "changes": {
      "sections_updated": ["authentication", "rate_limiting"],
      "quality_score_change": "+3 points"
    },
    "change_id": "chg_67890"
  }
}
```

#### Change Events
```json
{
  "event": "change.completed",
  "timestamp": "2025-09-26T10:45:00Z", 
  "data": {
    "change_id": "chg_67890",
    "source": "jira",
    "processing_time": "45 minutes",
    "documents_affected": 5,
    "quality_improvement": "+2.1%"
  }
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is missing required parameters",
    "details": {
      "missing_fields": ["title", "content"],
      "invalid_fields": {"type": "must be one of: wiki, api_doc, runbook, guide"}
    },
    "request_id": "req_abc123",
    "timestamp": "2025-09-26T10:30:00Z"
  }
}
```

### HTTP Status Codes
- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate)
- `422 Unprocessable Entity`: Valid request, but business logic error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Temporary service unavailability

### Error Codes
```typescript
enum ErrorCodes {
  // Authentication & Authorization
  UNAUTHORIZED = "UNAUTHORIZED",
  FORBIDDEN = "FORBIDDEN", 
  INVALID_TOKEN = "INVALID_TOKEN",
  TOKEN_EXPIRED = "TOKEN_EXPIRED",
  
  // Request Validation
  INVALID_REQUEST = "INVALID_REQUEST",
  MISSING_PARAMETER = "MISSING_PARAMETER",
  INVALID_PARAMETER = "INVALID_PARAMETER",
  
  // Resource Management
  RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND",
  RESOURCE_CONFLICT = "RESOURCE_CONFLICT",
  RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED",
  
  // Agent & Processing
  AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE",
  PROCESSING_FAILED = "PROCESSING_FAILED",
  TIMEOUT = "TIMEOUT",
  
  // Integration
  INTEGRATION_ERROR = "INTEGRATION_ERROR",
  EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
}
```

## Rate Limiting

### Rate Limits by Plan
```yaml
Free_Tier:
  requests_per_minute: 60
  requests_per_hour: 1000
  requests_per_day: 10000

Professional:
  requests_per_minute: 300
  requests_per_hour: 10000
  requests_per_day: 100000

Enterprise:
  requests_per_minute: 1000
  requests_per_hour: 50000
  requests_per_day: 1000000
```

### Rate Limit Headers
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1632686400
X-RateLimit-Window: 3600
```

## SDKs and Examples

### Python SDK
```python
from kinexus_ai import KinexusClient

# Initialize client
client = KinexusClient(
    api_key="sk_kinexus_abc123...",
    base_url="https://api.kinexusai.com"
)

# Submit a change
change = client.changes.create({
    "source": "jira",
    "type": "feature_release",
    "data": {
        "issue_key": "PROJ-1234",
        "summary": "New API endpoint",
        "components": ["api-service"]
    }
})

# Monitor change progress
status = client.changes.get(change.id)
print(f"Status: {status.status}")

# List documents
documents = client.documents.list(
    limit=50,
    status="active",
    type="api_doc"
)

for doc in documents:
    print(f"{doc.title}: Quality {doc.quality_score}/100")
```

### JavaScript SDK
```javascript
const { KinexusClient } = require('@kinexus/sdk');

const client = new KinexusClient({
  apiKey: 'sk_kinexus_abc123...',
  baseURL: 'https://api.kinexusai.com'
});

// Submit change and wait for completion
async function submitChange() {
  const change = await client.changes.create({
    source: 'git',
    type: 'code_update',
    data: {
      repository: 'company/api-service',
      commit_hash: 'abc123...',
      files_changed: ['src/auth.py', 'docs/api.md']
    }
  });
  
  // Poll for completion
  let status;
  do {
    await new Promise(resolve => setTimeout(resolve, 5000));
    status = await client.changes.get(change.id);
    console.log(`Status: ${status.status}`);
  } while (status.status === 'processing');
  
  return status;
}
```

### cURL Examples

#### Submit Change
```bash
curl -X POST https://api.kinexusai.com/api/v1/changes \
  -H "Authorization: Bearer sk_kinexus_abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "source": "slack",
    "type": "decision_documented",
    "data": {
      "channel": "#architecture",
      "message_id": "1234567890.123456",
      "decision": "Migrate to microservices architecture",
      "stakeholders": ["john.doe", "jane.smith"]
    }
  }'
```

#### Get Quality Metrics
```bash
curl -X GET "https://api.kinexusai.com/api/v1/quality/metrics?period=7d" \
  -H "Authorization: Bearer sk_kinexus_abc123..."
```

This comprehensive API reference provides all the tools needed to integrate Kinexus AI into existing enterprise workflows and build custom applications on top of the platform.