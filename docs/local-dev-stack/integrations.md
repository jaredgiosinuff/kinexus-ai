# Integration Guide - Local Development Stack

> **⚠️ Local Development Environment Only**
>
> This integration guide documents the **local FastAPI development stack** only. These integrations are NOT available in production AWS.
>
> **Production Environment**: Uses only Jira and Confluence webhooks (no REST API, no admin dashboard, no Monday.com/GitHub/SharePoint/ServiceNow).
>
> See [Production Integrations](../integrations.md) for the actual production setup.

Kinexus AI's local development environment provides comprehensive integration capabilities with enterprise systems for automated documentation management. This guide covers setup, configuration, and management of all supported integrations in the local Docker/Podman stack.

## 🔌 Supported Integrations

| Integration | Status | Features | Documentation |
|-------------|--------|----------|---------------|
| **Confluence** | ✅ **Local Dev Ready** | Page updates, search, section editing, AI-driven content management | [Confluence Setup](#confluence-integration) |
| **Jira** | ✅ **Local Dev Ready** | Issue tracking, comment automation, documentation issue creation, JQL search | [Jira Setup](#jira-integration) |
| **Monday.com** | ✅ **Working Prototype** | Board sync, GraphQL queries, webhook processing | [Monday.com Setup](#mondaycom-integration) |
| **GitHub** | ✅ **Commit Sync** | Repository sync, commit tracking, webhook automation | [GitHub Setup](#github-integration) |
| **SharePoint** | 📝 **Scaffold** | Connection testing framework, planned document library sync | [SharePoint Setup](#sharepoint-integration) |
| **ServiceNow** | 📝 **Scaffold** | Connection testing framework, planned ITSM integration | [ServiceNow Setup](#servicenow-integration) |

## 🚀 Quick Setup

### Prerequisites
1. **Running Kinexus AI instance** (`./quick-start.sh dev`)
2. **Admin access** to target systems
3. **API credentials** for each integration

### Basic Configuration Steps
1. **Access Admin Dashboard**: http://localhost:3107
2. **Navigate to Integrations** → Add New Integration
3. **Select Integration Type** and provide configuration
4. **Test Connection** to validate setup
5. **Enable Sync** to start automation

---

## Confluence Integration

### Overview
Confluence integration enables AI-driven documentation updates directly within your existing Confluence spaces. The system finds and updates existing pages in-place, maintaining your current documentation structure.

### ✅ Features
- **Page Management**: Update existing pages, create new pages when needed
- **Section Updates**: Targeted updates to specific page sections
- **Search & Discovery**: CQL-based page search and relevance scoring
- **AI Content Generation**: Context-aware documentation updates
- **Version Control**: Automatic version tracking with update notes

### 🔧 Configuration

#### Required Information
- **Confluence Base URL**: Your Confluence instance URL
- **Username**: Your Confluence username (email)
- **API Token**: Personal Access Token with appropriate scopes
- **Cloud ID**: (Optional) For scoped API tokens in Confluence Cloud

#### Step-by-Step Setup

**1. Generate API Token (2025 Method)**
```bash
# Visit: https://id.atlassian.com/manage-profile/security/api-tokens
# Create new token with scopes:
# - read:confluence-content.all
# - write:confluence-content
# - read:confluence-space.summary
```

**2. Configure in Kinexus AI**
```json
{
  "name": "confluence",
  "type": "confluence",
  "config": {
    "base_url": "https://yourcompany.atlassian.net",
    "username": "your-email@company.com",
    "api_token": "your_api_token_here",
    "cloud_id": "your_cloud_id",
    "default_space": "DEV"
  },
  "enabled": true
}
```

**3. Test Connection**
```bash
curl -X POST http://localhost:3105/api/integrations/test \
  -H "Content-Type: application/json" \
  -d '{"integration_id": "confluence_integration_id"}'
```

#### Advanced Configuration
```json
{
  "config": {
    "base_url": "https://yourcompany.atlassian.net",
    "username": "your-email@company.com",
    "api_token": "your_api_token_here",
    "cloud_id": "your_cloud_id",
    "default_space": "DEV",
    "update_sections": ["API Reference", "Code Examples", "Troubleshooting"],
    "auto_create_pages": false,
    "label_prefix": "kinexus-ai",
    "max_pages_per_update": 5
  }
}
```

---

## Jira Integration

### Overview
Jira integration provides intelligent issue tracking and documentation automation. The system can update existing issues, create documentation tasks, and maintain links between code changes and project requirements.

### ✅ Features
- **Issue Management**: Search, update, and create issues
- **Smart Comments**: Automated comments on relevant issues
- **Documentation Tasks**: Auto-create documentation issues for significant changes
- **Issue Linking**: Connect related issues and documentation
- **JQL Search**: Advanced issue discovery with relevance scoring

### 🔧 Configuration

#### Required Information
- **Jira Server URL**: Your Jira instance URL
- **Username**: Your Jira username (email)
- **API Token**: Personal Access Token
- **Project Keys**: List of projects to monitor

#### Step-by-Step Setup

**1. Generate API Token**
```bash
# Visit: https://id.atlassian.com/manage-profile/security/api-tokens
# Create new token with scopes:
# - read:jira-work
# - write:jira-work
# - read:jira-user
```

**2. Configure in Kinexus AI**
```json
{
  "name": "jira",
  "type": "jira",
  "config": {
    "server_url": "https://yourcompany.atlassian.net",
    "username": "your-email@company.com",
    "api_token": "your_api_token_here",
    "projects": ["PROJ", "DEV", "DOC"],
    "default_project": "DOC",
    "issue_types": ["Task", "Story", "Bug"]
  },
  "enabled": true
}
```

**3. Test Connection**
```bash
curl -X POST http://localhost:3105/api/integrations/test \
  -H "Content-Type: application/json" \
  -d '{"integration_id": "jira_integration_id"}'
```

#### Advanced Configuration
```json
{
  "config": {
    "server_url": "https://yourcompany.atlassian.net",
    "username": "your-email@company.com",
    "api_token": "your_api_token_here",
    "projects": ["PROJ", "DEV", "DOC"],
    "default_project": "DOC",
    "issue_types": ["Task", "Story", "Bug"],
    "auto_create_documentation_issues": true,
    "impact_threshold": 7,
    "default_components": ["Documentation"],
    "label_prefix": "kinexus-ai",
    "max_issues_per_update": 10
  }
}
```

---

## Monday.com Integration

### Overview
Monday.com integration syncs project boards and enables workflow automation through GraphQL queries.

### ✅ Features
- **Board Synchronization**: Sync board data and structure
- **GraphQL Queries**: Advanced data retrieval
- **Webhook Processing**: Real-time updates
- **Connection Testing**: Validate API access

### 🔧 Configuration

#### Required Information
- **API Token**: Monday.com API key
- **Board IDs**: List of boards to monitor

#### Setup
```json
{
  "name": "monday",
  "type": "monday",
  "config": {
    "api_token": "your_monday_api_token",
    "board_ids": ["123456789", "987654321"],
    "webhook_url": "http://localhost:3105/api/webhooks/monday"
  },
  "enabled": true
}
```

---

## GitHub Integration

### Overview
GitHub integration provides repository monitoring and commit synchronization for documentation automation.

### ✅ Features
- **Repository Sync**: Monitor multiple repositories
- **Commit Tracking**: Track recent commits and changes
- **Webhook Support**: Real-time change notifications
- **Branch Monitoring**: Configure which branches to track

### 🔧 Configuration

#### Required Information
- **Personal Access Token**: GitHub PAT with repo permissions
- **Repositories**: List of repositories to monitor

#### Setup
```json
{
  "name": "github",
  "type": "github",
  "config": {
    "access_token": "ghp_your_personal_access_token",
    "repositories": ["owner/repo1", "owner/repo2"],
    "webhook_secret": "your_webhook_secret",
    "branches": ["main", "develop"],
    "webhook_url": "http://localhost:3105/api/webhooks/github"
  },
  "enabled": true
}
```

---

## SharePoint Integration

### Overview
SharePoint integration is currently scaffolded with connection testing capabilities. Full document library management is planned for future releases.

### 📝 Current Status: Scaffold Implementation

#### Planned Features
- Document library synchronization
- File upload/download operations
- Metadata management
- Permission handling
- Site collection management

### 🔧 Configuration

#### Required Information
- **Site URL**: SharePoint site URL
- **Client ID**: Azure App registration client ID
- **Client Secret**: Azure App registration secret
- **Tenant ID**: Azure tenant identifier

#### Setup (Framework Only)
```json
{
  "name": "sharepoint",
  "type": "sharepoint",
  "config": {
    "site_url": "https://yourcompany.sharepoint.com/sites/documentation",
    "client_id": "your_azure_app_client_id",
    "client_secret": "your_azure_app_secret",
    "tenant_id": "your_azure_tenant_id",
    "libraries": ["Documents", "Wiki"]
  },
  "enabled": false
}
```

---

## ServiceNow Integration

### Overview
ServiceNow integration is currently scaffolded with connection testing capabilities. Full ITSM integration is planned for future releases.

### 📝 Current Status: Scaffold Implementation

#### Planned Features
- Incident and change request management
- Knowledge base article sync
- CMDB integration
- Workflow automation
- Service catalog integration

### 🔧 Configuration

#### Required Information
- **Instance URL**: ServiceNow instance URL
- **Username**: ServiceNow username
- **Password**: ServiceNow password or API key
- **Tables**: List of tables to sync

#### Setup (Framework Only)
```json
{
  "name": "servicenow",
  "type": "servicenow",
  "config": {
    "instance_url": "https://yourcompany.service-now.com",
    "username": "api_user",
    "password": "api_password",
    "tables": ["incident", "change_request", "kb_knowledge"]
  },
  "enabled": false
}
```

---

## 🔧 Integration Management

### API Endpoints

#### List Integrations
```bash
GET /api/integrations
```

#### Create Integration
```bash
POST /api/integrations
Content-Type: application/json

{
  "name": "integration_name",
  "type": "integration_type",
  "config": { /* configuration object */ },
  "enabled": true
}
```

#### Test Integration
```bash
POST /api/integrations/{id}/test
```

#### Update Integration
```bash
PUT /api/integrations/{id}
Content-Type: application/json

{
  "config": { /* updated configuration */ }
}
```

#### Trigger Sync
```bash
POST /api/integrations/{id}/sync
```

### CLI Management

```bash
# Using the quick-start script
./quick-start.sh

# View integration status
curl http://localhost:3105/api/integrations

# Test specific integration
curl -X POST http://localhost:3105/api/integrations/{id}/test
```

## 🛠️ Development

### Adding a New Integration

1. **Create Integration Class**
```python
from .base_integration import BaseIntegration, SyncResult, TestResult

class MyIntegration(BaseIntegration):
    def __init__(self, integration):
        super().__init__(integration)
        self.required_config_fields = ["api_key", "base_url"]

    async def test_connection(self) -> TestResult:
        # Implement connection test
        pass

    async def sync(self) -> SyncResult:
        # Implement sync logic
        pass

    async def process_webhook(self, event_type: str, payload: dict) -> bool:
        # Implement webhook processing
        pass
```

2. **Register Integration**
```python
# In src/core/services/integration_service.py
INTEGRATION_TYPES = {
    "my_integration": MyIntegration,
    # ... other integrations
}
```

3. **Add Configuration Schema**
```python
# Add validation schema and documentation
```

## 🔍 Troubleshooting

### Common Issues

#### Authentication Failures
- **Check API token expiration** (tokens expire 1-365 days in 2025)
- **Verify token scopes** match required permissions
- **Confirm base URLs** are correct and accessible

#### Connection Timeouts
- **Check firewall settings** and network connectivity
- **Verify SSL certificates** for HTTPS endpoints
- **Test with curl** to isolate issues

#### Sync Failures
- **Review integration logs**: `./quick-start.sh logs api`
- **Check rate limiting** from external APIs
- **Verify data format** matches expected schemas

### Debug Commands

```bash
# View integration logs
./quick-start.sh logs api | grep integration

# Test specific integration
curl -X POST http://localhost:3105/api/integrations/{id}/test

# Manual sync trigger
curl -X POST http://localhost:3105/api/integrations/{id}/sync

# Check integration status
curl http://localhost:3105/api/integrations/{id}/status
```

### Support Resources

- **API Documentation**: http://localhost:3105/docs
- **Integration Status**: http://localhost:3107 (Admin Dashboard)
- **System Health**: http://localhost:3105/health
- **Metrics**: http://localhost:3105/metrics

---

## 📊 Monitoring & Analytics

### Integration Metrics

Each integration provides:
- **Connection Status**: Real-time health monitoring
- **Sync Statistics**: Records processed, success rates
- **Error Tracking**: Failed operations and retry attempts
- **Performance Metrics**: Response times and throughput

### Dashboard Views

Access comprehensive monitoring at http://localhost:3107:
- **Integration Overview**: All integrations status
- **Sync History**: Historical sync performance
- **Error Reports**: Detailed error analysis
- **Usage Analytics**: API call patterns and costs

## 🔐 Security Best Practices

### API Token Management
- **Use scoped tokens** with minimal required permissions
- **Rotate tokens regularly** (recommended: 90 days)
- **Store tokens securely** in environment variables or secrets management
- **Monitor token usage** for unusual activity

### Network Security
- **Use HTTPS** for all API communications
- **Implement IP whitelisting** where possible
- **Configure proper firewall rules**
- **Enable audit logging** for all integration activities

### Access Control
- **Principle of least privilege** for integration accounts
- **Regular access reviews** and cleanup
- **Multi-factor authentication** where supported
- **Separate integration credentials** from user accounts

---

This integration guide provides comprehensive setup instructions for all supported systems. For additional help, consult the [Administration Guide](administration.md) or [GitHub Actions Guide](github-actions.md).