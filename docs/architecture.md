# Architecture

Kinexus AI uses a **serverless event-driven architecture** on AWS to automatically generate, review, and publish documentation. The production system is fully deployed on AWS using Lambda functions, EventBridge, DynamoDB, S3, and API Gateway. A local FastAPI development stack is available for testing.

## Production Architecture (AWS Serverless)

### High-Level Components

```mermaid
flowchart TB
    subgraph External
        Jira[Jira/Confluence]
        Bedrock[AWS Bedrock - Claude]
    end

    subgraph AWS_Infrastructure
        subgraph API_Layer
            APIGW[API Gateway]
        end

        subgraph Compute
            L1[JiraWebhookHandler]
            L2[DocumentOrchestrator]
            L3[ReviewTicketCreator]
            L4[ApprovalHandler]
            Layer[Lambda Layer - Dependencies]
        end

        subgraph Events
            EventBus[EventBridge Bus]
            R1[ChangeDetected Rule]
            R2[DocumentGenerated Rule]
        end

        subgraph Storage
            S3[S3 Bucket - Documents & Diffs]
            DDB1[(DynamoDB - Changes)]
            DDB2[(DynamoDB - Documents)]
        end
    end

    Jira -->|Webhook: Issue Events| APIGW
    Jira -->|Webhook: Comment Events| APIGW
    APIGW -->|/webhooks/jira| L1
    APIGW -->|/webhooks/approval| L4

    L1 -->|Put Event| EventBus
    EventBus -->|ChangeDetected| R1
    R1 -->|Trigger| L2

    L2 -->|Invoke Model| Bedrock
    L2 -->|Store Content| S3
    L2 -->|Store Metadata| DDB2
    L2 -->|Put Event| EventBus

    EventBus -->|DocumentGenerated| R2
    R2 -->|Trigger| L3

    L3 -->|Read Content| S3
    L3 -->|Generate Diff| S3
    L3 -->|Create Ticket| Jira

    L4 -->|Read Content| S3
    L4 -->|Publish Page| Jira
    L4 -->|Update Status| DDB2

    L1 -.->|Uses| Layer
    L2 -.->|Uses| Layer
    L3 -.->|Uses| Layer
    L4 -.->|Uses| Layer

    style Bedrock fill:#e1f5e1
    style S3 fill:#d4edda
    style EventBus fill:#fff3cd
```

### AWS Components

**Lambda Functions:**
1. **JiraWebhookHandler** (`src/lambdas/jira_webhook_handler.py`)
   - Processes Jira webhook events (ticket created, updated, closed)
   - Smart filtering to determine if documentation needed
   - Creates change records in DynamoDB
   - Emits `ChangeDetected` events to EventBridge
   - Timeout: 30s | Memory: 512MB

2. **DocumentOrchestrator** (`src/lambdas/document_orchestrator.py`)
   - Triggered by `ChangeDetected` events
   - Analyzes changes using Claude (AWS Bedrock)
   - Generates documentation content
   - Stores content in S3 with versioning
   - Updates document metadata in DynamoDB
   - Emits `DocumentGenerated` events
   - Timeout: 5min | Memory: 1024MB

3. **ReviewTicketCreator** (`src/lambdas/review_ticket_creator.py`)
   - Triggered by `DocumentGenerated` events
   - Retrieves previous and current versions from S3
   - Generates HTML visual diffs (red/green highlighting)
   - Detects image changes (added/removed)
   - Uploads diff to S3 with presigned URL
   - Auto-creates Jira review ticket with diff link
   - Timeout: 60s | Memory: 512MB

4. **ApprovalHandler** (`src/lambdas/approval_handler.py`)
   - Processes Jira comment webhooks
   - Pattern matches approval commands (APPROVED/REJECTED/NEEDS REVISION)
   - Publishes approved docs to Confluence
   - Updates DynamoDB and Jira tickets
   - Emits `DocumentationPublished` events
   - Timeout: 90s | Memory: 512MB

**EventBridge:**
- **Event Bus**: `kinexus-events`
- **Rules:**
  - `ChangeDetectedRule`: Routes `kinexus.jira/ChangeDetected` → DocumentOrchestrator
  - `DocumentGeneratedRule`: Routes `kinexus.orchestrator/DocumentGenerated` → ReviewTicketCreator

**DynamoDB Tables:**
- **kinexus-changes**: Stores change records from Jira tickets
  - Partition key: `change_id`
  - Tracks: ticket_key, summary, status, labels, documentation context
- **kinexus-documents**: Stores document metadata and versions
  - Partition key: `document_id`
  - Tracks: title, content location (S3), version, approval status, review tickets

**S3 Bucket:**
- **kinexus-documents-{account}-{region}**
  - `documents/` - Generated documentation content (markdown)
  - `diffs/` - HTML visual diffs with presigned URLs (7-day expiry)
  - Versioning enabled for audit trail

**API Gateway:**
- **Endpoints:**
  - `POST /webhooks/jira` → JiraWebhookHandler
  - `POST /webhooks/approval` → ApprovalHandler
  - `GET /documents` → DocumentOrchestrator (query)

**Lambda Layer:**
- Shared dependencies: structlog, httpx, anthropic, pydantic, requests, orjson
- Excludes boto3/botocore (provided by AWS runtime)
- Size: ~30MB compressed

### Production Workflow

```mermaid
sequenceDiagram
    participant Jira as Jira Ticket
    participant WH as JiraWebhookHandler
    participant EB as EventBridge
    participant Orch as DocumentOrchestrator
    participant Bedrock as Claude/Bedrock
    participant S3 as S3 Storage
    participant Rev as ReviewTicketCreator
    participant Human as Human Reviewer
    participant App as ApprovalHandler
    participant Conf as Confluence

    Jira->>WH: Webhook: Ticket Closed (needs-docs)
    WH->>WH: Smart filtering
    WH->>DynamoDB: Store change record
    WH->>EB: Event: ChangeDetected
    EB->>Orch: Trigger Lambda

    Orch->>Bedrock: Analyze change + generate docs
    Bedrock-->>Orch: Documentation content
    Orch->>S3: Store content (v2)
    Orch->>DynamoDB: Update document metadata
    Orch->>EB: Event: DocumentGenerated

    EB->>Rev: Trigger Lambda
    Rev->>S3: Get previous version (v1)
    Rev->>S3: Get current version (v2)
    Rev->>Rev: Generate HTML diff
    Rev->>S3: Upload diff.html
    Rev->>Jira: Create review ticket
    Note over Jira: TOAST-43: Review: Docs

    Human->>Jira: View diff link
    Human->>Jira: Comment: APPROVED

    Jira->>App: Webhook: Comment Created
    App->>App: Parse approval decision
    App->>S3: Read approved content
    App->>Conf: Publish/Update page
    App->>DynamoDB: Update status: published
    App->>Jira: Comment success + URL
    App->>EB: Event: DocumentationPublished
```

## Local Development Topology (FastAPI Stack)

For **local development and testing**, Kinexus provides a containerized FastAPI stack:

```mermaid
flowchart TB
    subgraph Containers
        API[api - FastAPI]
        Frontend[frontend - React]
        Postgres[postgres]
        Redis[redis]
        LocalStack[localstack - AWS services]
        OpenSearch[opensearch]
        MockBedrock[mock-bedrock]
    end

    Developer --> API
    Developer --> Frontend
    API --> Postgres
    API --> Redis
    API --> LocalStack
    API --> OpenSearch
    Agents --> MockBedrock
```

- `./quick-start.sh dev` orchestrates the stack, generates Poetry lock files, builds Docker images, and launches all containerized services
- `mock-bedrock` offers deterministic responses for integration tests; switch to live Bedrock by setting `BEDROCK_ENDPOINT_URL` and credentials
- LocalStack keeps S3, DynamoDB, and EventBridge APIs available for the agent scripts that expect AWS resources
- **Note:** The local stack is for development only. Production uses AWS Lambda.

## Infrastructure as Code

Kinexus uses **AWS CDK (Python)** for infrastructure:

```python
# infrastructure/app.py
class KinexusAIMVPStack(Stack):
    - Lambda functions (5 total)
    - Lambda layer (shared dependencies)
    - EventBridge bus and rules
    - DynamoDB tables (2)
    - S3 bucket (versioned)
    - API Gateway REST API
    - IAM roles and permissions

# Deployment
cdk deploy --context environment=development \
  --context jira_base_url=$JIRA_BASE_URL \
  --context jira_api_token=$JIRA_API_TOKEN
```

**GitHub Actions CI/CD:**
- `.github/workflows/dev.yaml`
- Triggers: Push to `develop` branch
- Steps:
  1. Run tests (pytest, black, isort, ruff)
  2. Build Lambda layer (`scripts/build-layer.sh`)
  3. Deploy CDK stack with secrets from GitHub
  4. Verify deployment

## Event Patterns

**ChangeDetected Event:**
```json
{
  "source": "kinexus.jira",
  "detail-type": "ChangeDetected",
  "detail": {
    "change_id": "jira_TOAST-42_...",
    "ticket_key": "TOAST-42",
    "summary": "Add OAuth2 authentication",
    "documentation_context": {...}
  }
}
```

**DocumentGenerated Event:**
```json
{
  "source": "kinexus.orchestrator",
  "detail-type": "DocumentGenerated",
  "detail": {
    "document_id": "doc_api-auth_v3",
    "title": "API Authentication Guide",
    "version": 3,
    "s3_location": "s3://kinexus-documents-.../documents/..."
  }
}
```

**DocumentationPublished Event:**
```json
{
  "source": "kinexus.approval",
  "detail-type": "DocumentationPublished",
  "detail": {
    "document_id": "doc_api-auth_v3",
    "confluence_url": "https://.../wiki/spaces/SD/pages/98310",
    "approved_by": "sarah.techwriter",
    "approved_at": "2025-10-19T20:45:00Z"
  }
}
```

## Security & Permissions

**Lambda IAM Roles:**
- Bedrock: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- DynamoDB: Read/write on `kinexus-changes`, `kinexus-documents`
- S3: Read/write on `kinexus-documents-*` bucket
- EventBridge: `events:PutEvents` on `kinexus-events` bus
- CloudWatch Logs: Write logs (1-week retention)

**Secrets Management:**
- Jira/Confluence credentials passed via CDK context from GitHub Secrets
- Environment variables on Lambda functions
- **Production**: Should migrate to AWS Secrets Manager

## Planned Enhancements

- **Automated Image Generation**: AI-generated diagrams using Mermaid/PlantUML
- **Multi-Stage Approval**: Technical review → Documentation review → Product approval
- **Slack Integration**: Notifications and inline approval buttons
- **Metrics Dashboard**: Approval times, rejection rates, quality scores
- **Revision Workflow**: Track changes after "NEEDS REVISION" feedback
- **Enhanced RAG**: Use OpenSearch for context retrieval before generation
- **Integration Hardening**: GitHub, ServiceNow, SharePoint adapters
