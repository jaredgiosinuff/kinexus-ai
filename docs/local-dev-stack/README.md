# Local Development Stack Documentation

> **⚠️ Development Environment Only**
>
> This folder contains documentation for the **local FastAPI development stack** - a comprehensive development environment that is NOT deployed to production.
>
> **Production Environment**: Uses AWS Lambda + EventBridge + DynamoDB + S3. See [Production Documentation](../README.md).

## What's in This Folder

This folder documents the **Docker-based local development environment** with full-featured services for testing and development:

### Local Dev Stack Features

**✅ Multi-Agent AI System**
- 5 separate AI agents (orchestrator, change-analyzer, content-creator, quality-controller, web-automator)
- Claude 4 Sonnet, Nova Pro + Canvas, Nova Act
- Ports 8010-8014

**✅ Admin Dashboard & Authentication**
- React frontend with Material-UI (port 3107)
- User management and RBAC
- Login system with roles (admin, lead reviewer, reviewer)
- Review dashboard for document workflows

**✅ PostgreSQL Database**
- Full relational database (port 3100)
- Schema migrations with Alembic
- User tables, approval rules, review tracking

**✅ CRAG (Self-Corrective RAG) System**
- Iterative quality assessment with 7 metrics
- Automatic correction with 7 strategies
- Enhanced retrieval-augmented generation

**✅ Additional Services**
- Redis cache (port 3101)
- LocalStack for AWS mocking (port 3102)
- OpenSearch for vector search (ports 3103-3104)
- GraphRAG service (port 3111)
- Mock Bedrock service (port 3106)
- Admin tools: Adminer, Redis Commander, OpenSearch Dashboards

## Documentation Files

- **[administration.md](administration.md)** - Admin dashboard, user management, system monitoring
- **[crag-system.md](crag-system.md)** - Self-Corrective RAG implementation and usage
- **[development.md](development.md)** - Local development setup and workflows

## Production vs Development

| Feature | Local Development | AWS Production |
|---------|-------------------|----------------|
| **Architecture** | FastAPI + Docker | Lambda + EventBridge |
| **Database** | PostgreSQL | DynamoDB |
| **AI Models** | 5 agents (Claude 4, Nova Pro/Act/Canvas) | 1 model (Amazon Nova Lite) |
| **Authentication** | Full auth system + RBAC | None (public webhooks) |
| **Admin UI** | React dashboard | None |
| **CRAG System** | ✅ Full implementation | ❌ Not deployed |
| **Cache** | Redis | None |
| **Vector Search** | OpenSearch | None |
| **Ports** | 3100-3111, 8010-8014 | API Gateway HTTPS only |

## Quick Start

```bash
# Start the full local dev stack
./quick-start.sh dev

# Access services
open http://localhost:3105        # API root
open http://localhost:3105/docs   # API documentation (Swagger UI)
open http://localhost:3106        # Mock AI Agents
open http://localhost:3107        # Frontend dashboard

# View admin tools
podman-compose --profile tools up -d
open http://localhost:3108        # Adminer (database admin)
open http://localhost:3109        # Redis Commander
open http://localhost:3110        # OpenSearch Dashboards
```

## When to Use This Stack

**✅ Use Local Dev Stack For:**
- Developing new features locally
- Testing multi-agent AI workflows
- UI/UX development with the admin dashboard
- Database schema changes and migrations
- CRAG system experimentation
- Integration testing with full stack

**❌ Don't Use for Production:**
- The local dev stack is NOT production-ready
- Production uses AWS Lambda serverless architecture
- No PostgreSQL, Redis, or admin dashboard in production
- See [Production Deployment Guide](../deployment.md)

## Related Documentation

**Production AWS Documentation:**
- [Architecture](../architecture.md) - AWS Lambda serverless architecture
- [Deployment](../deployment.md) - Production deployment guide
- [AWS Setup](../aws-deployment-setup.md) - IAM and infrastructure
- [Documentation Workflow](../documentation-workflow.md) - Phase 1-4 approval workflow

**Development Documentation:**
- [Getting Started](../getting-started.md) - Both local dev and production setup
- [Testing](../testing.md) - Test suite and coverage
- [API Reference](../api-reference.md) - API endpoints

## Future Plans

This local development stack represents a **potential future production architecture** with:
- Multi-agent AI orchestration
- Advanced RAG with quality assessment
- Full admin dashboard and user management
- Comprehensive monitoring and observability

However, the current production deployment prioritizes:
- ✅ Simplicity: Serverless Lambda functions
- ✅ Cost: Pay-per-invocation pricing
- ✅ Scalability: Auto-scaling with EventBridge
- ✅ Reliability: AWS-managed infrastructure
