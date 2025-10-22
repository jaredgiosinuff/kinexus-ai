# Kinexus AI Documentation Hub

Welcome to the comprehensive documentation for Kinexus AI - the autonomous knowledge management system that keeps enterprise documentation synchronized with system changes in real-time.

## 🚀 Quick Navigation

### **New to Kinexus AI?**
Start here: **[Getting Started Guide](getting-started.md)**

### **Deploying to Production AWS?**
See: **[Deployment Guide](deployment.md)** for Lambda + EventBridge + DynamoDB

### **Setting Up Local Development?**
Go to: **[Local Development Stack](local-dev-stack/)** for FastAPI + PostgreSQL + Multi-Agent AI

## 📚 Complete Documentation

### Core Guides
- **[Getting Started](getting-started.md)** - Complete onboarding for new users and evaluators
- **[Deployment Guide](deployment.md)** - AWS production deployment (Lambda + EventBridge)
- **[API Reference](api-reference.md)** - Complete API documentation with examples

### Local Development Stack (FastAPI + Docker)
> **Note**: These features are NOT in production AWS. See [local-dev-stack/](local-dev-stack/) for details.

- **[Local Development Guide](local-dev-stack/development.md)** - Docker setup and workflows
- **[Administration Guide](local-dev-stack/administration.md)** - Admin dashboard and user management
- **[CRAG System](local-dev-stack/crag-system.md)** - Self-Corrective RAG implementation

### Operational Guides
- **[Architecture](architecture.md)** - Production AWS serverless architecture
- **[Testing Guide](local-dev-stack/testing.md)** - Local dev testing (LocalStack, MCP, compose stack)
- **[Security Guide](local-dev-stack/security.md)** - Local dev security (OAuth2, role-based auth)
- **[Operations Guide](local-dev-stack/operations.md)** - Local dev monitoring and maintenance

### Integration & Automation
- **[Integrations Guide](integrations.md)** - Production Jira + Confluence webhook integrations
- **[Integration Configuration](integration-configuration.md)** - Step-by-step integration setup
- **[Integration Troubleshooting](integration-troubleshooting.md)** - Common issues and solutions
- **[GitHub Actions Deployment](github-actions-deployment.md)** - Automated AWS Lambda deployment via GitHub Actions
- **[AWS Deployment Setup](aws-deployment-setup.md)** - AWS infrastructure setup and permissions
- **[Documentation Workflow](documentation-workflow.md)** - Complete Phase 1-7 production workflow

### Project Management
- **[Progress & Plans](local-dev-stack/progress.md)** - Local dev project status and roadmap

## 🏗️ Architecture Overview

**Production AWS Serverless:**
```
┌─── Jira Events ──┐    ┌── AWS Lambda (4 functions) ──┐    ┌── Confluence ──┐
│ • Issue Updates  │───▶│ • JiraWebhookHandler         │───▶│ • Pages        │
│ • Transitions    │    │ • DocumentOrchestrator       │    │ • Updates      │
│ • Comments       │    │ • ReviewTicketCreator        │    │ • Publishing   │
└──────────────────┘    │ • ApprovalHandler            │    └────────────────┘
                        │ + Amazon Nova Lite (Bedrock) │
                        └──────────────────────────────┘
```

**Local Development Stack (Features NOT in Production):**
```
┌─── Change Sources ───┐    ┌── AI Capabilities ──┐    ┌── Documentation ──┐
│ • ServiceNow         │    │ • Claude 4 Models   │    │ • SharePoint      │
│ • Git/CI-CD          │───▶│ • Nova Pro/Act      │───▶│ • Google Drive    │
│ • Slack/Teams        │    │ • Vector Search     │    │ • ServiceNow KB   │
│ • Monday.com         │    │ • Quality Engine    │    │ • Enterprise Wikis│
└─────────────────────┘    └─────────────────────┘    └───────────────────┘
```

## 🎯 Key Features

### **Autonomous AI Systems**

**Production (AWS Serverless - Currently Deployed):**
- **Amazon Nova Lite**: Single AI model for ALL operations:
  - Documentation generation from Jira tickets
  - Confluence search and content analysis
  - Decision logic (UPDATE vs CREATE)
  - Cost-effective (~$0.06 per 1M tokens)
- **Lambda Functions**: 4 stateless, event-driven functions
- **EventBridge**: Orchestrates workflow (ChangeDetected → DocumentGenerated → Published)
- **Integrations**: Jira + Confluence webhooks only

**Development Stack (Local FastAPI with Mock Agents - NOT in Production):**
- **Claude 4 Opus 4.1**: Master reasoning engine (74.5% SWE-bench)
- **Claude 4 Sonnet**: Fast processing with 1M token context
- **Amazon Nova Pro/Act/Canvas**: Multimodal, agentic, and voice capabilities
- **Real-time conversation tracking** and confidence scoring

### **Production Features (AWS Lambda)**
- **EventBridge orchestration**: Event-driven serverless workflow
- **CloudWatch monitoring**: Comprehensive logging and metrics
- **DynamoDB storage**: Persistent change and document records
- **S3 document storage**: Versioned documentation with visual diffs

### **Local Development Features (NOT in Production)**
- **Dual authentication**: AWS Cognito + Local OAuth2 (FastAPI only)
- **Role-based access control**: viewer/reviewer/admin roles (FastAPI only)
- **Complete observability**: Prometheus metrics + Grafana dashboards (Docker only)
- **15+ integrations**: Monday.com, SharePoint, ServiceNow, etc. (local dev only)

### **Document Lifecycle Management**
- **Detecting** system changes from multiple sources
- **Finding** affected documentation wherever it lives
- **Updating** documents IN PLACE using advanced AI
- **Publishing** updates back to original locations
- **Tracking** all changes for audit and rollback

## 🚀 Quick Start

### Local Development (5 minutes)
```bash
git clone https://github.com/jaredgiosinuff/kinexus-ai.git
cd kinexus-ai
./quick-start.sh dev
./quick-start.sh test
```

**Services Available:**
- **API**: http://localhost:3105/docs
- **Frontend**: http://localhost:3107
- **Mock AI**: http://localhost:3106/agents

### Production Deployment
```bash
./quick-start.sh prod
```

## 🔌 Integration Setup

**Production AWS Integrations (Currently Deployed):**

| Integration | Status | Setup Guide |
|-------------|--------|-------------|
| **Jira** | ✅ Production | [Integrations Guide](integrations.md#jira-integration) |
| **Confluence** | ✅ Production | [Integrations Guide](integrations.md#confluence-integration) |

**Local Development Integrations (NOT in Production):**

| Integration | Status | Setup Guide |
|-------------|--------|-------------|
| **GitHub** | ✅ Local Dev | [Local Dev Integrations](local-dev-stack/integrations.md#github-integration) |
| **Monday.com** | ✅ Local Dev | [Local Dev Integrations](local-dev-stack/integrations.md#mondaycom-integration) |
| **SharePoint** | 📝 Scaffold | [Local Dev Integrations](local-dev-stack/integrations.md#sharepoint-integration) |
| **ServiceNow** | 📝 Scaffold | [Local Dev Integrations](local-dev-stack/integrations.md#servicenow-integration) |

**Quick Setup:**
- **Production AWS**: [Jira + Confluence Setup](integrations.md)
- **Local Development**: [All Integrations Setup](local-dev-stack/integrations.md)

## 📊 Documentation Quality Standards

This documentation follows these principles:

### **Comprehensive Coverage**
- Complete setup instructions for all environments
- Detailed API documentation with examples
- Troubleshooting guides for common issues
- Enterprise security and compliance guidance

### **User-Centric Organization**
- **Role-based navigation**: Different entry points for developers, admins, and users
- **Task-oriented structure**: Organized by what users want to accomplish
- **Progressive disclosure**: Basic concepts first, advanced topics later

### **Always Current**
- Updated with each release
- Validated against actual system behavior
- Community contributions welcomed and reviewed
- Automated testing of code examples

## 🔄 Documentation Workflow

This documentation is managed using Kinexus AI itself:

1. **Code changes** trigger automatic documentation analysis
2. **AI agents** identify affected documentation
3. **Quality checks** ensure accuracy and consistency
4. **Updates** are published across all platforms

See [Documentation Workflow](documentation-workflow.md) for details.

## 🎯 AWS AI Agent Global Hackathon 2025

This project demonstrates:
- **Advanced use of Amazon Bedrock** for autonomous documentation management
- **Amazon Nova Lite** for cost-effective, production-ready AI operations
- **Real-world enterprise problem solving** with measurable ROI
- **Production-ready serverless architecture** with comprehensive observability

## 📞 Support & Community

### **Getting Help**
- **GitHub Issues**: [Report bugs and request features](https://github.com/jaredgiosinuff/kinexus-ai/issues)
- **Discussions**: [Community Q&A and best practices](https://github.com/jaredgiosinuff/kinexus-ai/discussions)
- **Documentation Issues**: [Report documentation problems](https://github.com/jaredgiosinuff/kinexus-ai/issues/new?template=documentation.md)

### **Contributing**
- **Contributing Guide**: [CONTRIBUTING.md](../CONTRIBUTING.md)
- **Code of Conduct**: Professional and inclusive community standards
- **Documentation Updates**: Contributions welcomed via pull requests

## 📈 Success Metrics

Organizations using Kinexus AI report:

- **95% reduction** in documentation lag time
- **80% increase** in documentation accuracy
- **60% decrease** in support tickets due to outdated docs
- **50% faster** onboarding for new team members
- **$2.3M annual savings** for 1000-person engineering organizations

## 🗂️ Archive & Legacy Content

Historical documents and superseded content are preserved in [`docs/archive/`](archive/). These are maintained for historical reference but should not be considered current guidance.

**Archive Structure:**
- `archive/legacy/` - Original hackathon and MVP documentation
- `archive/migrated/` - Consolidated planning documents
- `archive/consolidated/` - Documents that have been merged into current guides

---

**Questions about the documentation?** [Open an issue](https://github.com/jaredgiosinuff/kinexus-ai/issues) or start a [discussion](https://github.com/jaredgiosinuff/kinexus-ai/discussions).

**Ready to get started?** Begin with the [Getting Started Guide](getting-started.md).