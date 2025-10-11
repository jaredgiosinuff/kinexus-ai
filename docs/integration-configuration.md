# Integration Configuration Guide

This guide provides detailed, step-by-step configuration instructions for all Kinexus AI integrations. Use this alongside the main [Integration Guide](integrations.md) for comprehensive setup.

## 🎯 Configuration Overview

All integrations follow a consistent pattern:
1. **External System Setup**: Configure API access in the target system
2. **Credential Generation**: Create API tokens or authentication credentials
3. **Kinexus AI Configuration**: Add integration through API or Admin Dashboard
4. **Connection Testing**: Verify connectivity and permissions
5. **Sync Configuration**: Enable and configure automated synchronization

---

## Atlassian Products (Confluence & Jira)

### Prerequisites
- **Atlassian Account** with admin access to your organization
- **Confluence/Jira Cloud** or **Server** instance
- **API Token Generation** permissions

### Step 1: Generate API Token (2025 Method)

**For Confluence Cloud & Jira Cloud:**

1. **Navigate to API Token Management**
   ```
   Visit: https://id.atlassian.com/manage-profile/security/api-tokens
   ```

2. **Create New Token**
   - Click "Create API token"
   - Label: "Kinexus AI Integration"
   - Set expiration: 90 days (recommended)
   - Select scopes:

   **For Confluence:**
   ```
   ✅ read:confluence-content.all
   ✅ write:confluence-content
   ✅ read:confluence-space.summary
   ✅ read:confluence-props
   ✅ write:confluence-props
   ```

   **For Jira:**
   ```
   ✅ read:jira-work
   ✅ write:jira-work
   ✅ read:jira-user
   ✅ read:issue-meta
   ✅ write:issue-meta
   ```

3. **Copy Token**
   - Save the token securely (it won't be shown again)
   - Note the expiration date for renewal planning

### Step 2: Find Your Cloud ID (for scoped tokens)

```bash
# Method 1: From any Atlassian URL
https://yourcompany.atlassian.net
# Cloud ID is in the URL or accessible via:

# Method 2: API call
curl -u your-email@company.com:your_api_token \
  https://yourcompany.atlassian.net/_edge/tenant_info | jq .cloudId
```

### Step 3: Test API Access

**Test Confluence Access:**
```bash
curl -u your-email@company.com:your_api_token \
  -H "Accept: application/json" \
  "https://yourcompany.atlassian.net/wiki/rest/api/space"
```

**Test Jira Access:**
```bash
curl -u your-email@company.com:your_api_token \
  -H "Accept: application/json" \
  "https://yourcompany.atlassian.net/rest/api/3/myself"
```

### Step 4: Configure in Kinexus AI

**Via API:**
```bash
# Confluence Configuration
curl -X POST http://localhost:3105/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "company-confluence",
    "type": "confluence",
    "config": {
      "base_url": "https://yourcompany.atlassian.net",
      "username": "your-email@company.com",
      "api_token": "your_api_token_here",
      "cloud_id": "your_cloud_id",
      "default_space": "DEV",
      "update_sections": ["API Reference", "Code Examples"],
      "auto_create_pages": false,
      "max_pages_per_update": 5
    },
    "enabled": true
  }'

# Jira Configuration
curl -X POST http://localhost:3105/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "company-jira",
    "type": "jira",
    "config": {
      "server_url": "https://yourcompany.atlassian.net",
      "username": "your-email@company.com",
      "api_token": "your_api_token_here",
      "projects": ["PROJ", "DEV", "DOC"],
      "default_project": "DOC",
      "auto_create_documentation_issues": true,
      "impact_threshold": 7
    },
    "enabled": true
  }'
```

**Via Admin Dashboard:**
1. Navigate to http://localhost:3107
2. Go to **Integrations** → **Add New**
3. Select **Confluence** or **Jira**
4. Fill in the configuration form
5. Click **Test Connection**
6. If successful, click **Save & Enable**

---

## GitHub Integration

### Prerequisites
- **GitHub Account** with access to target repositories
- **Repository Admin** permissions for webhook setup
- **Personal Access Token** generation permissions

### Step 1: Create Personal Access Token

1. **Navigate to GitHub Settings**
   ```
   Visit: https://github.com/settings/tokens
   ```

2. **Generate New Token (Classic)**
   - Click "Generate new token" → "Generate new token (classic)"
   - Note: "Kinexus AI Integration"
   - Expiration: 90 days
   - Select scopes:
   ```
   ✅ repo (Full control of private repositories)
   ✅ admin:repo_hook (Full control of repository hooks)
   ✅ read:org (Read org and team membership)
   ✅ user:email (Access user email addresses)
   ```

3. **Copy Token**
   - Save securely (not shown again)
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 2: Test Repository Access

```bash
# Test repository access
curl -H "Authorization: token ghp_your_token_here" \
  https://api.github.com/repos/owner/repository

# Test webhook permissions
curl -H "Authorization: token ghp_your_token_here" \
  https://api.github.com/repos/owner/repository/hooks
```

### Step 3: Configure Webhook Secret

Generate a secure webhook secret:
```bash
# Generate random secret
openssl rand -hex 20
# Example output: a1b2c3d4e5f6789...
```

### Step 4: Configure in Kinexus AI

```bash
curl -X POST http://localhost:3105/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "github-repos",
    "type": "github",
    "config": {
      "access_token": "ghp_your_personal_access_token",
      "repositories": ["owner/repo1", "owner/repo2"],
      "webhook_secret": "your_webhook_secret_here",
      "branches": ["main", "develop", "feature/*"],
      "webhook_url": "https://your-kinexus-domain.com/api/webhooks/github",
      "sync_frequency": "hourly"
    },
    "enabled": true
  }'
```

### Step 5: Setup Repository Webhooks

For each repository, add webhook:
1. Go to **Repository** → **Settings** → **Webhooks**
2. Click **Add webhook**
3. Configure:
   - **Payload URL**: `https://your-kinexus-domain.com/api/webhooks/github`
   - **Content type**: `application/json`
   - **Secret**: Your webhook secret
   - **Events**: Select "Push", "Pull requests", "Issues"
4. Click **Add webhook**

---

## Monday.com Integration

### Prerequisites
- **Monday.com Account** with board access
- **API Permissions** in your Monday.com workspace

### Step 1: Generate API Token

1. **Navigate to Admin Settings**
   ```
   Visit your Monday.com workspace → Admin → API
   ```

2. **Create API Token**
   - Click "Generate API Token"
   - Name: "Kinexus AI Integration"
   - Copy the token (format: `eyJhbGci...`)

### Step 2: Find Board IDs

```bash
# Get all boards
curl -H "Authorization: Bearer your_monday_api_token" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { boards { id name } }"}' \
  https://api.monday.com/v2

# Example response:
# {
#   "data": {
#     "boards": [
#       {"id": "123456789", "name": "Project Board"},
#       {"id": "987654321", "name": "Documentation Board"}
#     ]
#   }
# }
```

### Step 3: Configure in Kinexus AI

```bash
curl -X POST http://localhost:3105/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "monday-boards",
    "type": "monday",
    "config": {
      "api_token": "your_monday_api_token",
      "board_ids": ["123456789", "987654321"],
      "webhook_url": "https://your-kinexus-domain.com/api/webhooks/monday",
      "sync_frequency": "daily",
      "include_archived": false
    },
    "enabled": true
  }'
```

---

## SharePoint Integration (Scaffold)

### Prerequisites
- **Azure AD Application** with appropriate permissions
- **SharePoint Admin** access
- **Tenant Admin** permissions for app registration

### Step 1: Register Azure AD Application

1. **Navigate to Azure Portal**
   ```
   Visit: https://portal.azure.com → Azure Active Directory → App registrations
   ```

2. **Create New Registration**
   - Name: "Kinexus AI SharePoint Integration"
   - Account types: "Accounts in this organizational directory only"
   - Redirect URI: (Leave blank for now)

3. **Note Application Details**
   - Copy **Application (client) ID**
   - Copy **Directory (tenant) ID**

### Step 2: Create Client Secret

1. **Navigate to Certificates & secrets**
2. **Create New Client Secret**
   - Description: "Kinexus AI Integration"
   - Expires: 12 months
   - Copy the **Value** (not shown again)

### Step 3: Configure API Permissions

Add the following Microsoft Graph permissions:
```
✅ Sites.Read.All (Application)
✅ Sites.ReadWrite.All (Application)
✅ Files.Read.All (Application)
✅ Files.ReadWrite.All (Application)
```

### Step 4: Grant Admin Consent

1. Click **Grant admin consent for [Organization]**
2. Confirm the consent

### Step 5: Configure in Kinexus AI (Scaffold)

```bash
curl -X POST http://localhost:3105/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sharepoint-docs",
    "type": "sharepoint",
    "config": {
      "site_url": "https://yourcompany.sharepoint.com/sites/documentation",
      "client_id": "your_azure_app_client_id",
      "client_secret": "your_azure_app_secret",
      "tenant_id": "your_azure_tenant_id",
      "libraries": ["Documents", "Wiki", "Shared Documents"]
    },
    "enabled": false
  }'
```

---

## ServiceNow Integration (Scaffold)

### Prerequisites
- **ServiceNow Instance** with appropriate access
- **API Access** permissions
- **Integration User** account (recommended)

### Step 1: Create Integration User

1. **Navigate to User Administration**
   ```
   ServiceNow → System Security → Users and Groups → Users
   ```

2. **Create New User**
   - User ID: `kinexus_ai_integration`
   - First name: `Kinexus`
   - Last name: `AI Integration`
   - Email: Use a service account email
   - Active: ✅

### Step 2: Assign Roles

Assign minimum required roles:
```
✅ rest_api_explorer
✅ knowledge_admin (for KB articles)
✅ itil (for incidents/changes)
✅ web_service_admin
```

### Step 3: Generate API Credentials

Option 1: Basic Authentication
- Use the integration user credentials

Option 2: OAuth 2.0 (Recommended)
- Create OAuth application entity
- Generate client credentials

### Step 4: Test API Access

```bash
# Test basic authentication
curl -u kinexus_ai_integration:password \
  -H "Accept: application/json" \
  "https://yourcompany.service-now.com/api/now/table/sys_user?sysparm_limit=1"

# Test OAuth (if configured)
curl -H "Authorization: Bearer your_oauth_token" \
  -H "Accept: application/json" \
  "https://yourcompany.service-now.com/api/now/table/sys_user?sysparm_limit=1"
```

### Step 5: Configure in Kinexus AI (Scaffold)

```bash
curl -X POST http://localhost:3105/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "servicenow-itsm",
    "type": "servicenow",
    "config": {
      "instance_url": "https://yourcompany.service-now.com",
      "username": "kinexus_ai_integration",
      "password": "secure_password_here",
      "tables": ["incident", "change_request", "kb_knowledge", "cmdb_ci"],
      "sync_frequency": "hourly"
    },
    "enabled": false
  }'
```

---

## Environment Variables

For production deployments, use environment variables instead of hardcoded credentials:

### .env Configuration
```bash
# Confluence
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your_confluence_token
CONFLUENCE_CLOUD_ID=your_cloud_id

# Jira
JIRA_SERVER_URL=https://yourcompany.atlassian.net
JIRA_USERNAME=your-email@company.com
JIRA_API_TOKEN=your_jira_token

# GitHub
GITHUB_ACCESS_TOKEN=ghp_your_github_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Monday.com
MONDAY_API_TOKEN=your_monday_token

# SharePoint (Scaffold)
SHAREPOINT_CLIENT_ID=your_azure_client_id
SHAREPOINT_CLIENT_SECRET=your_azure_client_secret
SHAREPOINT_TENANT_ID=your_azure_tenant_id

# ServiceNow (Scaffold)
SERVICENOW_INSTANCE_URL=https://yourcompany.service-now.com
SERVICENOW_USERNAME=kinexus_ai_integration
SERVICENOW_PASSWORD=secure_password_here
```

### Docker Configuration
```yaml
# docker-compose.yml
services:
  api:
    environment:
      - CONFLUENCE_BASE_URL=${CONFLUENCE_BASE_URL}
      - CONFLUENCE_USERNAME=${CONFLUENCE_USERNAME}
      - CONFLUENCE_API_TOKEN=${CONFLUENCE_API_TOKEN}
      - JIRA_SERVER_URL=${JIRA_SERVER_URL}
      - JIRA_USERNAME=${JIRA_USERNAME}
      - JIRA_API_TOKEN=${JIRA_API_TOKEN}
      # ... other environment variables
```

---

## Validation Scripts

Create validation scripts to test your configurations:

### test-integrations.sh
```bash
#!/bin/bash

# Test Confluence
echo "Testing Confluence..."
curl -u "$CONFLUENCE_USERNAME:$CONFLUENCE_API_TOKEN" \
  -H "Accept: application/json" \
  "$CONFLUENCE_BASE_URL/wiki/rest/api/space" > /dev/null
echo "Confluence: $?"

# Test Jira
echo "Testing Jira..."
curl -u "$JIRA_USERNAME:$JIRA_API_TOKEN" \
  -H "Accept: application/json" \
  "$JIRA_SERVER_URL/rest/api/3/myself" > /dev/null
echo "Jira: $?"

# Test GitHub
echo "Testing GitHub..."
curl -H "Authorization: token $GITHUB_ACCESS_TOKEN" \
  https://api.github.com/user > /dev/null
echo "GitHub: $?"

# Test Monday.com
echo "Testing Monday.com..."
curl -H "Authorization: Bearer $MONDAY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { me { name } }"}' \
  https://api.monday.com/v2 > /dev/null
echo "Monday.com: $?"
```

### Usage
```bash
chmod +x test-integrations.sh
./test-integrations.sh
```

---

## Security Considerations

### Token Security
- **Rotate tokens regularly** (90 days recommended)
- **Use environment variables** instead of hardcoded values
- **Implement token expiration monitoring**
- **Store tokens in secure vaults** (AWS Secrets Manager, Azure Key Vault)

### Network Security
- **Use HTTPS** for all API communications
- **Implement IP whitelisting** where possible
- **Configure proper firewall rules**
- **Monitor API usage** for unusual patterns

### Access Control
- **Create dedicated service accounts** for integrations
- **Apply principle of least privilege**
- **Regular access reviews** and cleanup
- **Enable audit logging** for all integration activities

---

## Common Configuration Issues

### Token Expiration
```bash
# Check token expiration
curl -u username:token https://api.atlassian.com/oauth/token/accessible-resources

# Expected error for expired token:
# {"error": "invalid_token"}
```

### Permission Issues
```bash
# Test specific permissions
curl -u username:token \
  -H "Accept: application/json" \
  "https://yourcompany.atlassian.net/wiki/rest/api/space"

# Check for 403 Forbidden or permission errors
```

### Network Connectivity
```bash
# Test basic connectivity
ping yourcompany.atlassian.net
telnet yourcompany.atlassian.net 443

# Test SSL certificate
openssl s_client -connect yourcompany.atlassian.net:443
```

---

This configuration guide provides step-by-step instructions for setting up all Kinexus AI integrations. For troubleshooting specific issues, refer to the [Integration Guide](integrations.md) troubleshooting section.