# Deployment Guide

Kinexus AI is a fully containerized multi-agent AI system built with modern DevOps practices. This guide covers deployment for both development and production environments using Docker and Docker Compose.

## Quick Start

**One-line development setup:**
```bash
./quick-start.sh
```

**Production deployment:**
```bash
./quick-start.sh prod
```

## Architecture Overview

Kinexus AI consists of **8 containerized services**:

### 🚀 **Core Services**
- **API Server** (port 8000/3105) - FastAPI with Poetry dependency management
- **Frontend** (port 80/3107) - React + TypeScript with Nginx (production)

### 🤖 **AI Agent Services**
- **Orchestrator** (port 8010) - Master coordinator using Claude 4 Opus 4.1
- **Change Analyzer** (port 8011) - Real-time change detection using Claude 4 Sonnet
- **Content Creator** (port 8012) - Document generation using Nova Pro + Canvas
- **Quality Controller** (port 8013) - Quality assurance using Nova Pro
- **Web Automator** (port 8014) - Browser automation using Nova Act

### 🛠️ **Infrastructure Services**
- **PostgreSQL** (port 3100) - Primary database
- **Redis** (port 3101) - Caching and job queues
- **OpenSearch** (port 3103) - Vector search and analytics
- **LocalStack** (port 3102) - AWS services emulator for development

## Environments

### **Development Environment**
- Full observability with admin tools (Adminer, Redis Commander, OpenSearch Dashboards)
- Hot reload for API and frontend development
- Mock AWS services via LocalStack
- Volume mounts for live code editing

### **Production Environment**
- Multi-stage Docker builds for optimized images
- Non-root container users for security
- Resource limits and health checks
- Gunicorn + Nginx for production serving
- Persistent volumes for data

### **Legacy CDK Stack (Historical)**
- AWS Lambda + EventBridge serverless architecture
- Kept in `infrastructure/` for reference
- Not actively maintained

## Quick Start Commands

### Development
```bash
# Start all services with one command
./quick-start.sh dev

# View all service logs
./quick-start.sh logs

# View specific service logs
./quick-start.sh logs api
./quick-start.sh logs orchestrator

# Run tests
./quick-start.sh test

# Stop all services
./quick-start.sh stop

# Clean up Docker resources
./quick-start.sh cleanup
```

### Production
```bash
# Deploy production environment
./quick-start.sh prod

# Stop production services
./quick-start.sh stop-prod

# Check service status
./quick-start.sh status
```

## Service Access URLs

### Development Environment
- 🌐 **Frontend**: http://localhost:3107
- 🚀 **API**: http://localhost:3105
- 🎯 **Orchestrator**: http://localhost:8010
- 🔍 **Change Analyzer**: http://localhost:8011
- 📝 **Content Creator**: http://localhost:8012
- ✅ **Quality Controller**: http://localhost:8013
- 🌐 **Web Automator**: http://localhost:8014
- 📊 **GraphRAG**: http://localhost:3111

**Admin Tools:**
- 📋 **Database Admin (Adminer)**: http://localhost:3108
- 🔴 **Redis Commander**: http://localhost:3109
- 🔍 **OpenSearch Dashboards**: http://localhost:3110

### Production Environment
- 🌐 **Frontend**: http://localhost:80
- 🚀 **API**: http://localhost:8000
- 🤖 **AI Agents**: http://localhost:8010-8014

## Configuration

### Environment Variables
The quick-start script automatically creates a `.env` file with default development settings:

```bash
# Database Configuration
DB_NAME=kinexus_dev
DB_USER=kinexus_user
DB_PASSWORD=kinexus_secure_pass_2024

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# AI Model API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# Security
JWT_SECRET_KEY=auto_generated_secure_key
```

### Production Configuration
For production deployment:
1. **Update credentials**: Replace placeholder values in `.env`
2. **Rotate secrets**: Generate new JWT secret keys
3. **Configure AWS**: Use IAM roles instead of access keys when possible
4. **Database**: Use managed RDS instead of containerized PostgreSQL
5. **Redis**: Use ElastiCache for production caching
6. **Monitoring**: Enable CloudWatch or similar monitoring

## Docker Architecture

### Multi-Stage Production Builds
All production Dockerfiles use multi-stage builds for optimization:

1. **Builder Stage**: Installs all dependencies including dev tools
2. **Production Stage**: Copies only runtime dependencies and application code
3. **Security**: Runs as non-root user with minimal privileges
4. **Health Checks**: Built-in health monitoring for all services

### Dependency Management
- **Poetry**: Unified dependency management across all Python services
- **Lock Files**: Consistent versions across development and production
- **Layer Caching**: Optimized Docker layer caching for faster builds

### Service Communication
- **Internal Network**: All services communicate via Docker network
- **Service Discovery**: Services discover each other by container name
- **Health Checks**: Services wait for dependencies to be healthy before starting

## Legacy CDK Stack
If you need to replicate the original AWS Lambda demo:

```bash
npm install
npm run build        # packages lambda layer
npx cdk deploy       # deploys KinexusAIMVPStack
```

Prerequisites:
- AWS account with Bedrock model access
- `lambda_layer.zip` build succeeds (requires `pip install -r requirements.txt -t lambda_layer/python`)
- IAM permissions to create buckets, DynamoDB tables, EventBridge rules, and Lambda functions

> **Note:** The serverless stack persists in `docs/archive/legacy/` documentation; treat it as historical until the modern container deployment is scripted in IaC.

## Release Checklist
- [ ] Application container images built and pushed
- [ ] Database migrations applied
- [ ] `.env` / secret material updated for target environment
- [ ] Smoke tests executed (`pytest tests/test_mcp_integration.py`, `pytest tests/test_model_integration.py`)
- [ ] Monitoring endpoints verified (`/health` and `/metrics` if enabled)
