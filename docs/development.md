# Development Guide

This comprehensive guide covers everything you need for local Kinexus AI development, from initial setup to day-to-day workflows.

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Podman** (recommended) or Docker with docker-compose
- **8GB RAM** minimum (16GB recommended for full stack)
- **10GB free disk space**
- **AWS CLI v2** (optional, for live Bedrock testing)

### One-Command Setup
```bash
# Setup entire development environment
./quick-start.sh dev

# Test everything is working
./quick-start.sh test

# View service status
./quick-start.sh status
```

## 📊 Local Development Stack

The development environment runs on ports **3100-3110** with full containerization:

| Service | Port | Purpose | URL |
|---------|------|---------|-----|
| PostgreSQL | 3100 | Main database | `postgresql://kinexus_user:kinexus_pass@localhost:3100/kinexus_dev` |
| Redis | 3101 | Cache & sessions | `redis://localhost:3101/0` |
| LocalStack | 3102 | AWS services mock | http://localhost:3102 |
| OpenSearch | 3103 | Vector search | http://localhost:3103 |
| OpenSearch UI | 3104 | Search dashboard | http://localhost:3104 |
| **API Server** | **3105** | **Main backend** | **http://localhost:3105** |
| **Mock Bedrock** | **3106** | **AI services mock** | **http://localhost:3106** |
| **Frontend** | **3107** | **Web interface** | **http://localhost:3107** |
| GraphRAG | 3111 | Relationship-aware retrieval | http://localhost:3111 |

### Admin Tools (Optional)
```bash
# Start admin tools
podman-compose --profile tools up -d
```

| Tool | Port | Purpose |
|------|------|---------|
| Adminer | 3108 | Database admin |
| Redis Commander | 3109 | Redis admin |
| OpenSearch Dashboards | 3110 | Search admin |

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Server    │    │  Mock Bedrock   │
│   (React)       │◄──►│   (FastAPI)     │◄──►│  (AI Agents)    │
│   Port 3107     │    │   Port 3105     │    │   Port 3106     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │   OpenSearch    │
│   Port 3100     │    │   Port 3101     │    │   Port 3103     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────┐
                    │   LocalStack    │
                    │  (AWS Mock)     │
                    │   Port 3102     │
                    └─────────────────┘
```

## 📁 Repository Structure

```
src/
  api/                # FastAPI routers, dependencies, and lifespan wiring
  agents/             # Bedrock-facing agent orchestration and utilities
    agentic_rag_system.py    # Specialized retrieval agents
    graphrag/               # GraphRAG service
    multi_agent_supervisor.py # Agent coordination
  core/               # Domain services (auth, reviews, integrations, metrics)
    services/         # Business logic services
    websocket_manager.py     # Real-time connections
  database/           # SQLAlchemy models and connection helpers
  integrations/       # External system adapters (monday, github, servicenow, ...)
    github_actions_integration.py # GitHub Actions automation
    mcp_client.py     # Model Context Protocol client
  config/             # Model selection and MCP configuration helpers
scripts/              # Developer automation (dev-setup, dev-test, deploy helpers)
docs/                 # Consolidated documentation set
frontend/             # React dashboard for admin experience
tests/                # Pytest suites covering integrations and deployment
docker-compose.yml    # Local development stack definition
.github/workflows/    # GitHub Actions automation
```

## 🤖 Mock AI Services

The Mock Bedrock service provides **cost-free AI development** by simulating AWS Bedrock Agents:

### Available Mock Agents
- **DocumentOrchestrator**: Master coordination (Claude 4 Opus)
- **ChangeAnalyzer**: Change detection (Claude 4 Sonnet)
- **ContentCreator**: Content generation (Nova Pro)
- **QualityController**: Quality assurance (Nova Pro)
- **WebAutomator**: Browser automation (Nova Act)

### Testing Mock AI
```bash
# List available agents
curl http://localhost:3106/agents

# Test agent invocation
curl -X POST http://localhost:3106/agents/document-orchestrator/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "agentId": "document-orchestrator",
    "agentAliasId": "TSTALIASID",
    "sessionId": "test-session",
    "inputText": "Analyze this change for documentation impact"
  }'
```

## 🔧 Development Workflow

### Environment Setup

#### Python Environment
```bash
# Install Poetry (if not already installed)
pip install poetry==2.2.1

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

#### Starting Development
```bash
# Start all services
./quick-start.sh dev

# Check status
./quick-start.sh status

# View logs
./quick-start.sh logs api
```

### Making Code Changes

#### Backend (API) Changes
- Edit files in `src/`
- API server auto-reloads (thanks to volume mounts)
- Test: http://localhost:3105/docs

#### Frontend Changes
- Edit files in `frontend/src/`
- Vite dev server auto-reloads
- Test: http://localhost:3107

#### Database Changes
```bash
# Create migration
podman-compose exec api alembic revision --autogenerate -m "Description"

# Apply migration
podman-compose exec api alembic upgrade head
```

### Running API Outside Containers

For faster iteration, run the API directly on the host:

```bash
# Export environment variables
export $(cat .env | xargs)

# Run migrations first
alembic upgrade head

# Start API server (use 3105 to match containerized setup)
uvicorn src.api.main:app --reload --port 3105
```

### Developing Against Live Bedrock

Set environment variables in `.env`:
```bash
BEDROCK_ENDPOINT_URL=https://bedrock-runtime.us-east-1.amazonaws.com
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
ENABLE_MULTI_AGENT_AUTOMATION=true
```

Stop mock-bedrock to prevent collisions:
```bash
podman-compose stop mock-bedrock
```

## 🧪 Testing & Quality

### Running Tests
```bash
# Full test suite
pytest tests/

# Specific module
pytest tests/test_mcp_integration.py

# With coverage (recommended before PRs)
pytest --cov=src tests/

# Run in container
./quick-start.sh test
```

### Code Quality Tools
```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
ruff src/ tests/
# or
flake8 src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### Pre-commit Setup
```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 🗃️ Database Management

### Data Seeds
```bash
# Setup admin system
python scripts/setup_admin_system.py

# Manual SQL access
podman-compose exec postgres psql -U kinexus_user -d kinexus_dev
```

### Database Operations
```bash
# Database shell
podman-compose exec postgres psql -U kinexus_user -d kinexus_dev

# Run SQL file
podman-compose exec -T postgres psql -U kinexus_user -d kinexus_dev < file.sql

# Backup database
podman-compose exec postgres pg_dump -U kinexus_user kinexus_dev > backup.sql

# Restore database
podman-compose exec -T postgres psql -U kinexus_user -d kinexus_dev < backup.sql
```

## 🔧 Container Management

### Basic Operations
```bash
# View running containers
./quick-start.sh status

# Stop all services
./quick-start.sh stop

# Restart all services
./quick-start.sh restart

# Remove everything
./quick-start.sh cleanup

# Build images only
./quick-start.sh build
```

### Log Management
```bash
# View logs (follow all services)
./quick-start.sh logs

# View specific service logs
./quick-start.sh logs api

# View orchestrator logs
./quick-start.sh logs orchestrator
```

## 🐛 Troubleshooting

### Common Issues

#### Services Won't Start
```bash
# Check container status
./quick-start.sh status

# View logs
./quick-start.sh logs [service-name]

# Restart all services
./quick-start.sh restart

# Full reset
./quick-start.sh cleanup
./quick-start.sh dev
```

#### Database Connection Issues
```bash
# Check PostgreSQL logs
podman-compose logs postgres

# Connect manually
podman-compose exec postgres psql -U kinexus_user -d kinexus_dev

# Reset database
podman-compose down -v postgres
podman-compose up -d postgres
```

#### API Errors
```bash
# Check API logs
./quick-start.sh logs api

# Check health
curl http://localhost:3105/health

# Check metrics
curl http://localhost:3105/metrics
```

#### Podman-Specific Issues
```bash
# Check Podman machine status
podman machine list

# Start Podman machine if needed
podman machine start

# Check socket connection
podman system connection list

# Reset Podman state
podman system reset
```

#### Authentication Issues
- API 401s → confirm the default seed user exists or create one via admin endpoints
- Bedrock client errors → switch to mock service or ensure AWS credentials grant `bedrock:InvokeModel`

#### LocalStack Issues
- Delete `/tmp/localstack` to reset if stale state causes issues
- Check LocalStack logs: `./quick-start.sh logs localstack`

### Reset Environment
```bash
# Stop and remove everything
./quick-start.sh cleanup

# Rebuild and restart
./quick-start.sh dev
```

## ⚙️ Configuration

### Environment Variables

Create `.env` file with:
```bash
# Database
DB_HOST=localhost
DB_PORT=3100
DB_NAME=kinexus_dev
DB_USER=kinexus_user
DB_PASSWORD=kinexus_pass

# Redis
REDIS_URL=redis://localhost:3101/0

# AWS/Bedrock
AWS_REGION=us-east-1
BEDROCK_REGION=us-east-1
# For live testing:
# BEDROCK_ENDPOINT_URL=https://bedrock-runtime.us-east-1.amazonaws.com
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret

# Features
ENABLE_MULTI_AGENT_AUTOMATION=true
ENABLE_METRICS=true
ENVIRONMENT=development

# GitHub Actions (optional)
GITHUB_ACTIONS_WEBHOOK_TOKEN=your_token
```

### MCP Configuration

Enable Model Context Protocol for advanced integrations:
```bash
# In .env
MCP_ENABLED=true
MCP_CONFIG_PATH=src/config/mcp_config.json
```

## 🚀 Advanced Development

### Multi-Agent Pipeline

Enable automatic documentation updates:
1. Set `ENABLE_MULTI_AGENT_AUTOMATION=true`
2. Ensure Bedrock credentials are available
3. Webhook flows will automatically invoke AI agents

### GitHub Actions Integration

1. Set `GITHUB_ACTIONS_WEBHOOK_TOKEN` in environment
2. Workflows send token as Bearer auth to `/api/webhooks/github/actions`
3. Plans are stored in `documentation_plans` table
4. Use `/api/documentation-plans` endpoints to manage plans

### Documentation Plans

```bash
# List plans
curl http://localhost:3105/api/documentation-plans

# Link plan to review
curl -X POST http://localhost:3105/api/documentation-plans/{id}/link-review \
  -H "Content-Type: application/json" \
  -d '{"review_id": "review-uuid"}'
```

## 🤝 Contributing

### Before You Push

1. **Test locally**: `./quick-start.sh test`
2. **Run full test suite**: `pytest --cov=src tests/`
3. **Code quality checks**: `black`, `isort`, `ruff`, `mypy`
4. **Update documentation** if adding features
5. **Security scan**: `bandit -r src/`

### Development Best Practices

- Use feature branches: `git checkout -b feature/your-feature`
- Write tests for new functionality
- Update API documentation in docstrings
- Follow existing code patterns and conventions
- Add type hints for new functions
- Update migration scripts for database changes

## 🆘 Getting Help

- **View logs**: `./quick-start.sh logs [service]`
- **Check health**: `./quick-start.sh status`
- **Reset environment**: `./quick-start.sh cleanup && ./quick-start.sh dev`
- **API documentation**: http://localhost:3105/docs
- **Mock AI agents**: http://localhost:3106/agents
- **Database admin**: http://localhost:3108 (Adminer)

## 📚 Next Steps

1. **Explore API**: http://localhost:3105/docs
2. **Test Mock AI**: http://localhost:3106/agents
3. **Frontend Dashboard**: http://localhost:3107
4. **Database Access**: http://localhost:3108
5. **Check out**: [Testing Guide](testing.md), [Deployment Guide](deployment.md)