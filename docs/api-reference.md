# API Reference

The Kinexus AI API provides comprehensive access to all system functionality, enabling integration with existing enterprise systems and custom application development.

## Overview

### API Capabilities
- **Document Management**: Create, update, and retrieve documentation
- **AI Agent Control**: Manage and monitor AI agents
- **Change Management**: Submit and track system changes
- **Quality Assurance**: Access quality metrics and compliance data
- **Integration Management**: Configure and monitor external integrations
- **Real-time Updates**: WebSocket connections for live data

### Base URL
- **Development**: `http://localhost:3105`
- **Production**: `https://api.kinexusai.com`

### API Versioning
All endpoints are versioned with the prefix `/api/v1/`

## Authentication

### API Key Authentication (Recommended)
```http
GET /api/v1/documents
Authorization: Bearer your_api_key_here
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
SigV4Auth(credentials, 'execute-api', region).add_auth(request)
```

### Getting API Keys
```bash
# Create API key
curl -X POST http://localhost:3105/api/auth/api-keys \
  -H "Authorization: Bearer $USER_TOKEN" \
  -d '{"name": "My Integration", "scopes": ["documents:read", "agents:invoke"]}'
```

## Core APIs

### Documents API

#### List Documents
```http
GET /api/v1/documents
```

**Parameters:**
- `limit` (integer): Number of documents to return (default: 20)
- `offset` (integer): Number of documents to skip
- `status` (string): Filter by status (active, archived, draft)
- `type` (string): Filter by document type
- `search` (string): Search in title and content

**Response:**
```json
{
  "documents": [
    {
      "id": "doc_123",
      "title": "User Authentication Guide",
      "status": "active",
      "document_type": "guide",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T15:45:00Z",
      "current_version": 3,
      "ai_generated": true,
      "ai_confidence": 85
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

#### Get Document
```http
GET /api/v1/documents/{document_id}
```

**Response:**
```json
{
  "id": "doc_123",
  "title": "User Authentication Guide",
  "content": "# Authentication Guide\n\n...",
  "status": "active",
  "document_type": "guide",
  "metadata": {
    "tags": ["authentication", "security"],
    "category": "developer-guides"
  },
  "versions": [
    {
      "version": 3,
      "content": "# Authentication Guide\n\n...",
      "created_at": "2025-01-15T15:45:00Z",
      "ai_generated": true,
      "ai_model": "claude-4-sonnet",
      "ai_confidence": 85
    }
  ],
  "integrations": [
    {
      "system": "confluence",
      "external_id": "page_456",
      "last_sync": "2025-01-15T16:00:00Z"
    }
  ]
}
```

#### Create Document
```http
POST /api/v1/documents
```

**Request:**
```json
{
  "title": "New Feature Guide",
  "content": "# Feature Guide\n\nThis guide explains...",
  "document_type": "guide",
  "metadata": {
    "tags": ["feature", "guide"],
    "category": "user-guides"
  },
  "integrations": [
    {
      "system": "confluence",
      "space_key": "DOCS",
      "auto_sync": true
    }
  ]
}
```

#### Update Document
```http
PUT /api/v1/documents/{document_id}
```

**Request:**
```json
{
  "title": "Updated Feature Guide",
  "content": "# Updated Feature Guide\n\n...",
  "metadata": {
    "tags": ["feature", "guide", "updated"]
  }
}
```

### Reviews API

#### List Reviews
```http
GET /api/v1/reviews
```

**Parameters:**
- `status` (string): pending, approved, rejected, in_progress
- `reviewer_id` (string): Filter by reviewer
- `document_id` (string): Filter by document

**Response:**
```json
{
  "reviews": [
    {
      "id": "rev_123",
      "document_id": "doc_123",
      "status": "pending",
      "change_id": "commit_abc123",
      "impact_score": 7,
      "ai_confidence": 82,
      "created_at": "2025-01-15T10:00:00Z",
      "change_context": {
        "source": "github",
        "repository": "company/app",
        "files": ["src/auth.py", "docs/auth.md"]
      }
    }
  ]
}
```

#### Get Review
```http
GET /api/v1/reviews/{review_id}
```

#### Create Review
```http
POST /api/v1/reviews
```

**Request:**
```json
{
  "document_id": "doc_123",
  "change_id": "commit_abc123",
  "change_context": {
    "source": "github",
    "repository": "company/app",
    "files": ["src/auth.py"],
    "commit_message": "Add OAuth support"
  },
  "reviewer_id": "user_456"
}
```

## AI Agents API

### Agent Management

#### List Agents
```http
GET /api/v1/agents
```

**Response:**
```json
{
  "agents": [
    {
      "id": "document-orchestrator",
      "name": "Document Orchestrator",
      "model": "claude-4-opus-4.1",
      "status": "active",
      "capabilities": ["reasoning", "planning", "coordination"],
      "cost_per_1k_tokens": 0.015,
      "average_response_time": 2.3
    },
    {
      "id": "change-analyzer",
      "name": "Change Analyzer",
      "model": "claude-4-sonnet",
      "status": "active",
      "capabilities": ["analysis", "impact-assessment"],
      "cost_per_1k_tokens": 0.003,
      "average_response_time": 0.8
    }
  ]
}
```

#### Invoke Agent
```http
POST /api/v1/agents/{agent_id}/invoke
```

**Request:**
```json
{
  "input": "Analyze the impact of adding OAuth authentication to the user system",
  "context": {
    "document_id": "doc_123",
    "change_files": ["src/auth.py", "src/oauth.py"],
    "reasoning_pattern": "chain_of_thought"
  },
  "max_tokens": 4000,
  "temperature": 0.1
}
```

**Response:**
```json
{
  "response": {
    "content": "Based on the analysis of OAuth integration...",
    "confidence": 0.87,
    "reasoning_steps": [
      "Analyzed existing authentication system",
      "Identified integration points for OAuth",
      "Assessed impact on user experience"
    ]
  },
  "usage": {
    "input_tokens": 450,
    "output_tokens": 1200,
    "total_cost": 0.018
  },
  "execution_time": 2.1
}
```

### Agent Conversations

#### Get Conversation History
```http
GET /api/v1/agents/{agent_id}/conversations
```

#### Get Specific Conversation
```http
GET /api/v1/agents/conversations/{conversation_id}
```

**Response:**
```json
{
  "id": "conv_123",
  "agent_id": "document-orchestrator",
  "session_id": "session_456",
  "messages": [
    {
      "role": "user",
      "content": "Analyze documentation requirements for new feature",
      "timestamp": "2025-01-15T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "I'll analyze the documentation requirements...",
      "confidence": 0.89,
      "reasoning_pattern": "tree_of_thought",
      "timestamp": "2025-01-15T10:00:02Z"
    }
  ],
  "total_cost": 0.024,
  "total_tokens": 1850
}
```

## Integration APIs

### Integration Management

#### List Integrations
```http
GET /api/v1/integrations
```

**Response:**
```json
{
  "integrations": [
    {
      "id": "int_123",
      "name": "GitHub Integration",
      "type": "github",
      "status": "active",
      "config": {
        "organization": "company",
        "repositories": ["app", "docs"],
        "webhook_url": "https://api.kinexusai.com/webhooks/github"
      },
      "last_sync": "2025-01-15T16:00:00Z",
      "sync_status": "success"
    }
  ]
}
```

#### Create Integration
```http
POST /api/v1/integrations
```

**Request:**
```json
{
  "name": "Confluence Integration",
  "type": "confluence",
  "config": {
    "base_url": "https://company.atlassian.net",
    "username": "service@company.com",
    "token": "api_token",
    "space_key": "DOCS",
    "auto_sync": true,
    "sync_frequency": "real-time"
  }
}
```

#### Test Integration
```http
POST /api/v1/integrations/{integration_id}/test
```

**Response:**
```json
{
  "success": true,
  "connection_time": 150,
  "permissions": [
    "read_content",
    "write_content",
    "manage_webhooks"
  ],
  "test_results": {
    "authentication": "success",
    "permissions": "success",
    "connectivity": "success"
  }
}
```

## GitHub Actions API

### Change Analysis

#### Analyze Code Changes
```http
POST /api/v1/analyze-changes
```

**Request:**
```json
{
  "repository": "company/app",
  "ref": "refs/heads/feature/oauth",
  "sha": "abc123",
  "changed_files": ["src/auth.py", "docs/auth.md"],
  "scope": "repository",
  "pr_number": 42,
  "branch": "feature/oauth"
}
```

**Response:**
```json
{
  "status": "analyzed",
  "impact_score": 7,
  "affected_documents": ["docs/auth.md", "docs/api.md"],
  "recommendations": [
    "Update authentication documentation",
    "Add OAuth configuration examples",
    "Update API endpoint documentation"
  ],
  "estimated_effort": "120 minutes",
  "agent_analysis": {
    "agent_id": "change-analyzer",
    "confidence": 0.91,
    "reasoning": "High confidence based on clear OAuth implementation patterns"
  }
}
```

#### Update Documentation
```http
POST /api/v1/update-documentation
```

**Request:**
```json
{
  "action": "update_repository_docs",
  "repository": "company/app",
  "branch": "feature/oauth",
  "changed_files": ["src/auth.py"],
  "scope": "repository",
  "targets": ["README.md", "docs/auth.md"]
}
```

**Response:**
```json
{
  "status": "updated",
  "targets_updated": ["README.md", "docs/auth.md", "CHANGELOG.md"],
  "changes_made": [
    "Added OAuth configuration section to README",
    "Updated authentication flow diagram",
    "Added OAuth examples to auth documentation"
  ],
  "quality_score": 0.94,
  "agent_details": {
    "content_creator": {
      "confidence": 0.92,
      "tokens_used": 850,
      "cost": 0.012
    }
  }
}
```

## Webhook APIs

### GitHub Webhooks

#### GitHub Push Events
```http
POST /api/webhooks/github
```

**Headers:**
```
X-GitHub-Event: push
X-GitHub-Delivery: 12345
X-Hub-Signature-256: sha256=...
```

**Payload:**
```json
{
  "repository": {
    "full_name": "company/app"
  },
  "ref": "refs/heads/main",
  "after": "abc123",
  "commits": [
    {
      "id": "abc123",
      "message": "Add OAuth support",
      "modified": ["src/auth.py", "docs/auth.md"]
    }
  ]
}
```

### Jira Webhooks

#### Issue Created/Updated
```http
POST /api/webhooks/jira
```

### Slack Webhooks

#### Interactive Components
```http
POST /api/webhooks/slack
```

## WebSocket API

### Real-time Updates

#### Connect to WebSocket
```javascript
const ws = new WebSocket('ws://localhost:3105/api/ws');

// Authentication
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your_api_key'
}));

// Subscribe to document updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'documents',
  document_id: 'doc_123'
}));
```

#### Event Types

**Document Updates:**
```json
{
  "type": "document_updated",
  "document_id": "doc_123",
  "version": 4,
  "changes": {
    "title": "Updated title",
    "content_diff": "..."
  }
}
```

**Agent Activity:**
```json
{
  "type": "agent_activity",
  "agent_id": "document-orchestrator",
  "activity": "processing",
  "progress": 0.7,
  "estimated_completion": "2025-01-15T10:05:00Z"
}
```

**Integration Status:**
```json
{
  "type": "integration_status",
  "integration_id": "int_123",
  "status": "syncing",
  "progress": {
    "completed": 15,
    "total": 23
  }
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid document format",
    "details": {
      "field": "content",
      "reason": "Content cannot be empty"
    },
    "request_id": "req_123"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_FAILED` | 401 | Invalid or missing API key |
| `AUTHORIZATION_FAILED` | 403 | Insufficient permissions |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `RESOURCE_NOT_FOUND` | 404 | Resource does not exist |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `AGENT_UNAVAILABLE` | 503 | AI agent temporarily unavailable |
| `INTEGRATION_ERROR` | 502 | External integration failure |

## Rate Limiting

### Rate Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| General API | 1000 requests | 1 hour |
| Agent Invocation | 100 requests | 1 hour |
| Webhook | 10000 requests | 1 hour |
| WebSocket | 1000 messages | 1 hour |

### Rate Limit Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1642694400
```

## SDKs and Examples

### Python SDK
```python
from kinexus import KinexusClient

client = KinexusClient(api_key='your_api_key')

# Create document
document = client.documents.create(
    title='API Guide',
    content='# API Guide\n\n...',
    document_type='guide'
)

# Invoke agent
response = client.agents.invoke(
    agent_id='document-orchestrator',
    input='Analyze documentation requirements',
    context={'document_id': document.id}
)
```

### JavaScript SDK
```javascript
import { KinexusClient } from '@kinexus/sdk';

const client = new KinexusClient({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.kinexusai.com'
});

// List documents
const documents = await client.documents.list({
  limit: 20,
  status: 'active'
});

// Real-time updates
client.ws.connect();
client.ws.subscribe('documents', (event) => {
  console.log('Document updated:', event);
});
```

### cURL Examples
```bash
# Get documents
curl -X GET "http://localhost:3105/api/v1/documents" \
  -H "Authorization: Bearer your_api_key"

# Create review
curl -X POST "http://localhost:3105/api/v1/reviews" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_123",
    "change_id": "commit_abc"
  }'

# Invoke agent
curl -X POST "http://localhost:3105/api/v1/agents/change-analyzer/invoke" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Analyze code changes",
    "context": {"files": ["src/auth.py"]}
  }'
```

## Support

### API Documentation
- **OpenAPI Spec**: Available at `/docs` endpoint
- **Interactive Docs**: Available at `/redoc` endpoint

### Contact
- **Technical Support**: api-support@kinexusai.com
- **Documentation**: [docs.kinexusai.com](https://docs.kinexusai.com)
- **GitHub Issues**: [github.com/kinexusai/kinexus-ai](https://github.com/kinexusai/kinexus-ai)