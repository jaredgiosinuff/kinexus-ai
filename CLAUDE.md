# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kinexus AI is an AI-driven document management system built for the AWS AI Agent Global Hackathon 2025. It manages EXISTING documentation by detecting system changes, finding affected documents where they already live (GitHub, Confluence, etc.), and updating them IN PLACE using AI - not generating parallel documentation, but keeping real documentation synchronized with reality.

## Key AWS Services & Models

This project leverages cutting-edge AWS AI capabilities (September 2025):
- **Claude 4 Opus 4.1**: Master reasoning engine (74.5% SWE-bench)
- **Claude 4 Sonnet**: Fast processing with 1M token context
- **Amazon Nova Pro/Act/Canvas/Sonic**: Multimodal, agentic, and voice capabilities
- **Amazon Bedrock Agents**: Multi-agent orchestration
- **Amazon Q**: Business intelligence and analytics

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install

# Start local services
docker-compose up -d postgres redis localstack

# Database setup
alembic upgrade head
python scripts/seed_dev_data.py
```

### Development Server
```bash
# Start API server
uvicorn src.api.main:app --reload --port 8000

# Start agent workers (separate terminals)
python src/agents/orchestrator.py --dev
python src/agents/change_analyzer.py --dev
python src/agents/content_creator.py --dev

# Start frontend
cd frontend && npm run dev
```

### Testing
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests with coverage
pytest --cov=src tests/

# Single test file
pytest tests/unit/test_services/test_document_service.py

# Specific test
pytest tests/unit/test_services/test_document_service.py::TestDocumentService::test_create_document_success
```

### Code Quality
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
mypy src/

# Security scan
bandit -r src/

# Pre-commit checks
pre-commit run --all-files
```

### Deployment
```bash
# AWS CDK deployment
cdk deploy --profile production --context env=production

# Quick development deployment
./scripts/quick-deploy.sh

# Full production deployment
./scripts/deploy-aws.sh --environment production
```

## Architecture Overview

### Multi-Agent System
The system uses 5 specialized Bedrock agents:
1. **DocumentOrchestrator** - Master coordination using Claude 4 Opus 4.1
2. **ChangeAnalyzer** - Real-time change detection using Claude 4 Sonnet
3. **ContentCreator** - Document generation using Nova Pro + Canvas
4. **QualityController** - Quality assurance using Nova Pro
5. **WebAutomator** - Browser automation using Nova Act

Agents communicate via EventBridge and share state through DynamoDB.

### Data Flow
1. **Change Detection**: Webhooks from Jira/Git/Slack → API Gateway → Lambda
2. **Processing**: EventBridge → Agent Lambda functions → Bedrock API calls
3. **Storage**: DynamoDB (metadata), S3 (documents), OpenSearch (vectors)
4. **Output**: Agent results → Target systems (Confluence, SharePoint)

### Key Integration Points
- **Input Sources**: Jira, GitHub, Slack, ServiceNow, CI/CD systems
- **Output Targets**: Confluence, SharePoint, Google Drive, Enterprise Wikis
- **Authentication**: AWS Cognito for users, Secrets Manager for integrations

## Project Structure

```
kinexus-ai/
├── src/                    # Source code
│   ├── agents/            # AI agent implementations
│   ├── api/               # REST API endpoints
│   ├── core/              # Domain logic and services
│   ├── integrations/      # External system connectors
│   └── utils/             # Shared utilities
├── infrastructure/        # IaC (CDK/Terraform)
├── tests/                 # Test suite
├── frontend/              # React UI (if exists)
└── scripts/               # Deployment and utility scripts
```

## Critical Design Patterns

### Repository Pattern
All data access goes through repositories (e.g., `DocumentRepository`) which abstract database operations.

### Service Layer
Business logic resides in services (e.g., `DocumentService`) that coordinate between repositories and external systems.

### Agent Base Class
All agents inherit from `BaseAgent` which provides task queue, retry logic, and event emission.

### Integration Framework
Each external integration extends `BaseIntegration` with webhook handling and authentication.

## Security Considerations

- **Authentication**: AWS Cognito for user management, API keys for service-to-service
- **Secrets**: All credentials in AWS Secrets Manager with automatic rotation
- **Encryption**: KMS for at-rest, TLS 1.2+ for in-transit
- **Multi-tenancy**: Tenant isolation through separate DynamoDB tables and S3 prefixes
- **AI Security**: Prompt injection prevention, PII scrubbing before AI processing

## Development Phases

Currently targeting a 6-month roadmap:
1. **Foundation** (Months 1-2): Core infrastructure and MVP
2. **Agent Development** (Months 2-3): Complete multi-agent system
3. **Integration Hub** (Months 3-4): Enterprise connectors
4. **Quality & Compliance** (Month 4): Enterprise features
5. **Beta Release** (Month 5): Customer validation
6. **Production Launch** (Month 6): General availability

## AWS Hackathon Requirements

This project specifically addresses AWS AI Agent Global Hackathon requirements:
- Uses Bedrock Agents for orchestration (required)
- Leverages Claude 4 and Nova models from Bedrock (required)
- Demonstrates autonomous capabilities with reasoning
- Integrates 15+ external APIs and databases
- Solves real enterprise problem with measurable ROI ($4.7M over 5 years)