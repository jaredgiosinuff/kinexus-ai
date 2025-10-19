# Atlassian Setup Guide for Kinexus AI

This guide walks you through setting up an Atlassian account with Jira and Confluence, and creating API tokens for Kinexus AI integration.

---

## 📋 Table of Contents

1. [Create an Atlassian Account](#step-1-create-an-atlassian-account)
2. [Set Up Jira Cloud](#step-2-set-up-jira-cloud)
3. [Set Up Confluence Cloud](#step-3-set-up-confluence-cloud)
4. [Create API Token](#step-4-create-api-token)
5. [Configure Kinexus AI](#step-5-configure-kinexus-ai)

---

## Step 1: Create an Atlassian Account

### Official Documentation

- **Create an Atlassian Account**: https://support.atlassian.com/atlassian-account/docs/create-an-atlassian-account/
- **What is an Atlassian Account?**: https://support.atlassian.com/atlassian-account/docs/what-is-an-atlassian-account/

### Quick Sign-Up

**Direct sign-up page**: https://id.atlassian.com/signup

**Try Atlassian Cloud (Free for up to 10 users)**: https://www.atlassian.com/try/cloud/signup

### Steps

1. **Go to the sign-up page**: Visit https://id.atlassian.com/signup

2. **Enter your email address**
   - Use a work email if possible
   - This email will be used to log in to Jira, Confluence, and other Atlassian products

3. **Verify your email**
   - Check your inbox for a verification email from Atlassian
   - Click the verification link

4. **Complete your profile**
   - Set a password
   - Enter your full name
   - Select your location/region

5. **Create your Atlassian organization** (optional but recommended)
   - **Official Guide**: https://support.atlassian.com/organization-administration/docs/get-started-with-an-atlassian-organization/
   - An organization helps manage users, billing, and security across multiple Atlassian products

**Result**: You now have an Atlassian account that can be used across all Atlassian Cloud products.

---

## Step 2: Set Up Jira Cloud

### Official Documentation

- **Get Started with Jira Cloud**: https://support.atlassian.com/jira-software-cloud/docs/get-started-with-jira-software-cloud/
- **Jira Cloud Resources**: https://support.atlassian.com/jira-software-cloud/resources/
- **Set Up Jira Cloud**: https://support.atlassian.com/jira-work-management/docs/set-up-your-site/

### Adding Jira to Your Account

1. **Sign up for Jira Cloud** (if not already done):
   - Visit: https://www.atlassian.com/try/cloud/signup
   - Select **"Try Jira"**
   - Use the same email you used for your Atlassian account

2. **Choose your Jira plan**:
   - **Free**: Up to 10 users (perfect for testing Kinexus AI)
   - **Standard**: $7.75/user/month (billed annually)
   - **Premium**: $15.25/user/month (billed annually)
   - **Enterprise**: Contact sales

3. **Set up your Jira site**:
   - **Site name**: Choose a unique name (e.g., `yourcompany.atlassian.net`)
   - **Project template**: Select "Scrum" or "Kanban" (can be changed later)
   - **Project name**: Create your first project (e.g., "Documentation")

4. **Create your first project**:
   - Go to **Projects** → **Create project**
   - Choose a template (Software, Work Management, or Business)
   - Set a **Project key** (e.g., `DOC`, `TOAST`, `PROJ`)
   - Note: This project key will be used in Kinexus AI configuration

5. **Invite team members** (optional):
   - Go to **Settings** → **User management**
   - Click **Invite users**
   - Enter email addresses

### Jira Configuration for Kinexus AI

**Required labels for Kinexus AI:**

Create these labels in your Jira project:
- `needs-docs` - Triggers documentation generation
- `new-feature` - Indicates a new feature
- `breaking-change` - Flags breaking changes
- `api-change` - API modifications

**To create labels:**
1. Go to any issue
2. Click **Labels** in the issue details
3. Type the label name and press Enter
4. Labels are now available project-wide

---

## Step 3: Set Up Confluence Cloud

### Official Documentation

- **Set Up Confluence Cloud**: https://support.atlassian.com/confluence-cloud/docs/set-up-confluence-cloud/
- **Get Started as Confluence Administrator**: https://support.atlassian.com/confluence-cloud/docs/get-started-as-confluence-cloud-administrator/
- **Confluence Cloud Resources**: https://support.atlassian.com/confluence-cloud/resources/
- **Configure Confluence Cloud**: https://support.atlassian.com/confluence-cloud/docs/configure-confluence-cloud/

### Adding Confluence to Your Account

1. **Sign up for Confluence Cloud**:
   - Visit: https://www.atlassian.com/software/confluence/try
   - Or from your Atlassian account: **Products** → **Try Confluence**
   - Use the same email as your Atlassian account

2. **Choose your Confluence plan**:
   - **Free**: Up to 10 users
   - **Standard**: $5.75/user/month (billed annually)
   - **Premium**: $11/user/month (billed annually)
   - **Enterprise**: Contact sales

3. **Set up your Confluence site**:
   - Your Confluence URL will typically be: `https://yourcompany.atlassian.net/wiki`
   - If you already have a Jira site, Confluence uses the same domain

4. **Create your first space**:
   - Go to **Spaces** → **Create space**
   - Choose **Blank space** or **Documentation space**
   - **Space name**: "Documentation" or "Knowledge Base"
   - **Space key**: `DOC` or `KB` (short identifier)
   - **Permissions**: Set to "Public" or "Private" as needed

5. **Configure space permissions** (important for Kinexus AI):
   - Go to **Space settings** → **Permissions**
   - Ensure the API user will have **Can Add** and **Can Edit** permissions
   - For testing, you can use **"Anyone with account access"**

### Get Your Confluence Space ID

Kinexus AI may need your Confluence space ID:

1. Go to your space in Confluence
2. Click **Space settings**
3. Look at the URL: `https://yourcompany.atlassian.net/wiki/spaces/SPACEID/overview`
4. The `SPACEID` is your space key (e.g., `DOC`, `KB`)

---

## Step 4: Create API Token

### Official Documentation

- **Manage API Tokens (User Accounts)**: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
- **Manage API Tokens (Service Accounts)**: https://support.atlassian.com/user-management/docs/manage-api-tokens-for-service-accounts/
- **Understand User API Tokens**: https://support.atlassian.com/organization-administration/docs/understand-user-api-tokens/
- **Basic Auth for REST APIs**: https://developer.atlassian.com/cloud/jira/software/basic-auth-for-rest-apis/

### Important Note About API Token Expiration (2025 Update)

⚠️ **As of December 15, 2024**:
- New API tokens expire in **one year by default**
- You can set expiration from **1 day to 1 year** when creating a token
- Tokens created before Dec 15, 2024 will expire between **March 14 - May 12, 2026**

**Recommendation**: Set a calendar reminder to rotate your API tokens before expiration.

### Creating an API Token

**Direct link**: https://id.atlassian.com/manage-profile/security/api-tokens

#### Steps:

1. **Log in to your Atlassian account**:
   - Go to: https://id.atlassian.com/manage-profile/security/api-tokens
   - Or: **Profile** → **Security** → **API tokens**

2. **Create a new token**:
   - Click **Create API token**

3. **Configure the token**:
   - **Label**: Give it a descriptive name (e.g., "Kinexus AI Production")
   - **Expiration**: Select expiration period (recommended: 1 year, set reminder to rotate)
   - **Scopes** (if available):
     - ✅ `read:jira-work` - Read Jira issues
     - ✅ `write:jira-work` - Create/update Jira issues
     - ✅ `read:confluence-content.all` - Read Confluence pages
     - ✅ `write:confluence-content` - Create/update Confluence pages
     - ✅ `read:confluence-space.summary` - Read Confluence spaces

   **Note**: Scoped tokens are more secure. If scopes aren't available, you'll get a token with full account access.

4. **Copy the token**:
   - Click **Copy** immediately
   - **⚠️ IMPORTANT**: The token is only shown once! Store it securely.
   - If you lose it, you'll need to create a new token

5. **Store the token securely**:
   - Use a password manager (1Password, LastPass, etc.)
   - Or use environment variables (never commit to git)
   - Or use AWS Secrets Manager / GitHub Secrets

### API Token Format

Your API token will look like:
```
ATATT3xFfGF0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Testing Your API Token

Test that your token works:

```bash
# Test Jira API access
curl -u "your-email@company.com:YOUR-API-TOKEN" \
  "https://yourcompany.atlassian.net/rest/api/3/myself"

# Expected: JSON response with your account details

# Test Confluence API access
curl -u "your-email@company.com:YOUR-API-TOKEN" \
  "https://yourcompany.atlassian.net/wiki/rest/api/space"

# Expected: JSON response with your Confluence spaces
```

### Security Best Practices

✅ **DO**:
- Use scoped tokens when available
- Set expiration dates (max 1 year)
- Use one token per integration
- Rotate tokens regularly
- Store in secrets manager (AWS Secrets Manager, GitHub Secrets)
- Set calendar reminders before expiration

❌ **DON'T**:
- Commit tokens to git repositories
- Share tokens via email or chat
- Use the same token for multiple applications
- Give tokens more permissions than needed
- Store tokens in plaintext files

### Revoking API Tokens

If a token is compromised:

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Find the token in the list
3. Click **Revoke** next to the token
4. Create a new token immediately

---

## Step 5: Configure Kinexus AI

Now that you have your Atlassian account, Jira, Confluence, and API token set up, configure Kinexus AI:

### Required Information

Collect these values:

| Value | Example | Where to Find |
|-------|---------|---------------|
| **Jira Base URL** | `https://yourcompany.atlassian.net` | Your Jira site URL (without `/jira`) |
| **Jira Email** | `user@company.com` | Email you used to create Atlassian account |
| **Jira API Token** | `ATATT3xFfGF0...` | Created in Step 4 above |
| **Confluence URL** | `https://yourcompany.atlassian.net/wiki` | Your Confluence URL |
| **Jira Project Key** | `DOC` or `TOAST` | From your Jira project settings |

### GitHub Secrets Configuration

If deploying via GitHub Actions, add these secrets to your forked repository:

**Go to**: `Repository → Settings → Secrets and variables → Actions → New repository secret`

Add these secrets:

```bash
# Atlassian Configuration
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN=ATATT3xFfGF0xxxxxxxxxxxxxxxxxxxxx
CONFLUENCE_URL=https://yourcompany.atlassian.net/wiki

# AWS Configuration (see deployment guide)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_ACCOUNT_ID=123456789012
```

### Local/Manual CDK Deployment

If deploying manually with CDK:

```bash
cdk deploy \
  -c deployment_type=mvp \
  -c environment=development \
  -c jira_base_url="https://yourcompany.atlassian.net" \
  -c jira_email="user@company.com" \
  -c jira_api_token="ATATT3xFfGF0xxxxxxxxxxxxxxxxxxxxx" \
  -c confluence_url="https://yourcompany.atlassian.net/wiki"
```

### Update Lambda Environment Variables (if needed)

If you need to update credentials after deployment:

```bash
# Update JiraWebhookHandler
aws lambda update-function-configuration \
  --function-name KinexusAIMVPStack-*-JiraWebhookHandler* \
  --environment Variables='{
    "JIRA_BASE_URL":"https://yourcompany.atlassian.net",
    "JIRA_EMAIL":"user@company.com",
    "JIRA_API_TOKEN":"YOUR-NEW-TOKEN",
    "CONFLUENCE_URL":"https://yourcompany.atlassian.net/wiki"
  }'

# Repeat for other Lambda functions:
# - DocumentOrchestrator
# - ReviewTicketCreator
# - ApprovalHandler
```

---

## 🧪 Testing the Integration

After configuration, test the complete workflow:

### 1. Test Jira Connection

```bash
# Test Jira API access with your credentials
curl -u "YOUR-EMAIL:YOUR-API-TOKEN" \
  "https://yourcompany.atlassian.net/rest/api/3/project"

# Expected: List of your Jira projects
```

### 2. Test Confluence Connection

```bash
# Test Confluence API access
curl -u "YOUR-EMAIL:YOUR-API-TOKEN" \
  "https://yourcompany.atlassian.net/wiki/rest/api/space"

# Expected: List of your Confluence spaces
```

### 3. Create a Test Jira Ticket

1. Go to your Jira project
2. Click **Create**
3. Fill in:
   - **Summary**: "Test Kinexus AI Integration"
   - **Issue Type**: Story or Task
   - **Labels**: `needs-docs`, `test`
   - **Description**: "Testing the documentation workflow"
4. Click **Create**

### 4. Close the Ticket

- Change status: **To Do** → **Done**
- This triggers the Kinexus AI workflow

### 5. Monitor Processing

Watch Lambda logs (if deployed to AWS):

```bash
# Monitor webhook handler
aws logs tail /aws/lambda/KinexusAIMVPStack-*-JiraWebhookHandler* --follow

# Monitor orchestrator
aws logs tail /aws/lambda/KinexusAIMVPStack-*-DocumentOrchestrator* --follow
```

### 6. Check for Review Ticket

Within ~2-3 minutes, you should see:
- A new Jira ticket: "Review: Test Kinexus AI Integration"
- Labels: `documentation-review`, `auto-generated`, `kinexus-ai`
- Description with visual diff link

### 7. Approve and Verify Confluence

1. Comment on review ticket: `APPROVED`
2. Wait ~30 seconds
3. Check Confluence for new page
4. Verify source ticket has Confluence link

---

## 🔧 Troubleshooting

### Authentication Errors

**Error**: "401 Unauthorized" when testing API

**Solutions**:
- Verify email and API token are correct
- Check token hasn't expired
- Ensure token has required scopes
- Try creating a new token

### Confluence Permission Errors

**Error**: "403 Forbidden" when publishing to Confluence

**Solutions**:
- Check space permissions: **Space settings** → **Permissions**
- Ensure API user has **Can Add** and **Can Edit** permissions
- Verify Confluence URL is correct (should end with `/wiki`)

### Jira Webhook Not Triggering

**Solutions**:
- Check webhook is enabled in Jira: **Settings** → **System** → **WebHooks**
- Verify webhook URL matches your API Gateway endpoint
- Check Jira ticket has `needs-docs` label
- Review Lambda logs for errors

---

## 📚 Additional Resources

### Official Atlassian Documentation

- **Atlassian Account Management**: https://support.atlassian.com/atlassian-account/
- **Jira Cloud Support**: https://support.atlassian.com/jira-software-cloud/
- **Confluence Cloud Support**: https://support.atlassian.com/confluence-cloud/
- **Atlassian Community**: https://community.atlassian.com/
- **Atlassian Developer Portal**: https://developer.atlassian.com/

### Kinexus AI Documentation

- [Deployment Guide](deployment.md) - Complete deployment instructions
- [Architecture](architecture.md) - System architecture details
- [Approval Workflow](../APPROVAL_WORKFLOW.md) - Workflow documentation
- [Documentation Workflow](documentation-workflow.md) - Process details

### API References

- **Jira Cloud REST API**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- **Confluence Cloud REST API**: https://developer.atlassian.com/cloud/confluence/rest/v2/
- **Webhooks for Jira**: https://developer.atlassian.com/server/jira/platform/webhooks/

---

## 🎯 Summary

**Complete setup checklist**:

- ✅ Create Atlassian account (https://id.atlassian.com/signup)
- ✅ Set up Jira Cloud (https://www.atlassian.com/try/cloud/signup)
- ✅ Create Jira project with project key
- ✅ Set up Confluence Cloud (https://www.atlassian.com/software/confluence/try)
- ✅ Create Confluence space
- ✅ Generate API token (https://id.atlassian.com/manage-profile/security/api-tokens)
- ✅ Configure GitHub Secrets or CDK context
- ✅ Deploy Kinexus AI to AWS
- ✅ Test with a Jira ticket

**Total setup time**: ~30-45 minutes

**Free tier limits**: Up to 10 users for Jira and Confluence

---

*This guide is maintained as part of the Kinexus AI project. For questions or issues, please open a GitHub issue.*
