# Kinexus AI

Kinexus AI is a human-supervised documentation assistant powered by AWS serverless architecture. It automatically detects changes in Jira tickets, generates documentation using Claude AI (Bedrock), and orchestrates human review workflows with visual diffs before publishing to Confluence.

## Features
- **🤖 AI-Powered Documentation Generation** - Uses Claude (AWS Bedrock) to analyze Jira tickets and generate contextual documentation
- **👁️ Visual Diff Review** - HTML diffs with red/green highlighting for easy change review
- **✅ Jira-Based Approval Workflow** - Simple comment-based approval (APPROVED/REJECTED/NEEDS REVISION)
- **🔄 Automatic Confluence Publishing** - Approved documentation automatically published to Confluence
- **🖼️ Image Change Detection** - Identifies when images need updating separate from text changes
- **📊 Event-Driven Architecture** - AWS EventBridge orchestrates Lambda functions for reliable workflows
- **🔗 Full Integration** - Connects Jira, AWS Bedrock, S3, DynamoDB, and Confluence seamlessly

## Production Deployment (AWS)

Kinexus AI is deployed as a serverless application on AWS:

```bash
# Deploy to AWS (via GitHub Actions)
git push origin develop

# Or deploy manually with CDK
cd infrastructure
cdk deploy --context environment=development \
  --context jira_base_url=$JIRA_BASE_URL \
  --context jira_email=$JIRA_EMAIL \
  --context jira_api_token=$JIRA_API_TOKEN \
  --context confluence_url=$CONFLUENCE_URL
```

**Production Endpoints:**
- API: `https://z1rsr9mld0.execute-api.us-east-1.amazonaws.com/prod/`
- Jira Webhook: `.../webhooks/jira`
- Approval Webhook: `.../webhooks/approval`
- Documents API: `.../documents`

**📚 Complete Documentation**: [docs/README.md](docs/README.md) - Comprehensive guides for development, deployment, and administration

## Architecture Overview

Kinexus AI uses a serverless event-driven architecture:

```mermaid
graph TB
    A[Jira Ticket Closed] -->|Webhook| B[JiraWebhookHandler]
    B -->|EventBridge| C[DocumentOrchestrator]
    C -->|Claude/Bedrock| D[Generate Docs]
    D -->|S3| E[Store Content]
    E -->|EventBridge| F[ReviewTicketCreator]
    F -->|Create| G[Jira Review Ticket]
    G -->|Human Review| H[Visual Diff]
    H -->|Comment: APPROVED| I[ApprovalHandler]
    I -->|Publish| J[Confluence Page]

    style D fill:#e1f5e1
    style H fill:#fff3cd
    style J fill:#d4edda
```

**Key Components:**
- **5 Lambda Functions** - Webhook handlers, orchestrator, review ticket creator, approval handler
- **EventBridge** - Event routing (ChangeDetected → DocumentGenerated → DocumentationPublished)
- **DynamoDB** - Change tracking and document metadata
- **S3** - Document storage and HTML diffs
- **API Gateway** - REST endpoints for webhooks and queries

A detailed breakdown lives in [docs/architecture.md](docs/architecture.md) and [APPROVAL_WORKFLOW.md](APPROVAL_WORKFLOW.md).

## Quick Start Guide

### 1. Close a Jira Ticket
Close any Jira ticket (e.g., `TOAST-42`) with appropriate labels (e.g., `needs-docs`, `new-feature`)

### 2. Review Ticket Auto-Created
Within ~2 minutes, a review ticket appears (e.g., `TOAST-43: Review: API Authentication Guide`)

### 3. Review the Visual Diff
Open the review ticket and click the **"View Full Diff (HTML)"** link to see:
- Side-by-side comparison (original vs. new)
- Red highlighting for deletions
- Green highlighting for additions
- Image change warnings

### 4. Approve or Reject
Comment on the review ticket:
- `APPROVED` - Publish to Confluence immediately
- `REJECTED` - Reject and mark for regeneration
- `NEEDS REVISION` - Request specific changes

### 5. Documentation Published
If approved, documentation automatically publishes to Confluence with version tracking and audit trail.

## Documentation
- [Architecture](docs/architecture.md) - AWS serverless architecture details
- [Approval Workflow](APPROVAL_WORKFLOW.md) - Complete Phase 4 workflow documentation
- [Deployment](docs/deployment.md) - AWS deployment and GitHub Actions setup
- [Development](docs/development.md) - Local development (FastAPI legacy stack)
- [Documentation Workflow](docs/documentation-workflow.md) - Document lifecycle and storage
- [AWS Deployment Setup](docs/aws-deployment-setup.md) - Infrastructure configuration
- [Testing](docs/testing.md) - Test suite and coverage
- [Security](docs/security.md) - Security policies and best practices
- [Integrations](docs/integrations.md) - External system connections
- [Operations](docs/operations.md) - Operational procedures
- [Progress & Plans](docs/progress.md) - Project status and roadmap

## Local Development (FastAPI Stack)

For local development and testing with the FastAPI stack:

```bash
./quick-start.sh dev    # build containers, apply migrations, launch services
./quick-start.sh test   # verify containers and run smoke checks
```

Key endpoints once the stack is running:
- API docs: `http://localhost:3105/docs`
- Frontend (experimental): `http://localhost:3107`
- Mock Bedrock service: `http://localhost:3106`

**Note:** The production deployment uses AWS Lambda, not the local FastAPI stack. The local stack is for development and testing only.

## Testing
```bash
# Run all tests
pytest tests/

# Targeted tests
pytest tests/test_model_integration.py

# Coverage before PRs
pytest --cov=src tests/

# CI checks (black, isort, ruff)
./check-ci.sh
```

Ensure LocalStack and the mock Bedrock service are running if the suite touches AWS dependencies.

## Contributing
Read the [Contributor Guidelines](CONTRIBUTING.md) and the new [Repository Guidelines](AGENTS.md) for style and workflow expectations. We welcome issues and PRs that improve accuracy, automation, and integration coverage.

## License
Apache 2.0 — see [LICENSE](LICENSE).
