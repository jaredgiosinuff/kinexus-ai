# GitHub Secrets Setup for Jira/Confluence Integration

## Required Secrets

Add these secrets to your forked GitHub repository at:
`https://github.com/YOUR-USERNAME/kinexus-ai/settings/secrets/actions`

### 1. JIRA_BASE_URL
```
https://yourcompany.atlassian.net
```
**Example:** `https://acme-corp.atlassian.net`

### 2. JIRA_EMAIL
```
user@company.com
```
**Example:** `john.doe@acme-corp.com`

### 3. JIRA_API_TOKEN
```
ATATT3xFfGF0...
```
**Note:** Create your Jira API token at https://id.atlassian.com/manage-profile/security/api-tokens
See [Atlassian Setup Guide](docs/atlassian-setup-guide.md) for detailed instructions.

### 4. CONFLUENCE_URL
```
https://yourcompany.atlassian.net/wiki
```
**Example:** `https://acme-corp.atlassian.net/wiki`

### 5. AWS_ACCESS_KEY_ID
```
AKIA...
```
**Note:** From AWS IAM user with Lambda/DynamoDB/S3/EventBridge permissions

### 6. AWS_SECRET_ACCESS_KEY
```
wJalr...
```
**Note:** Created with the access key above

### 7. AWS_ACCOUNT_ID
```
123456789012
```
**Note:** Your 12-digit AWS account ID

## Steps to Add Secrets

1. Go to: `https://github.com/YOUR-USERNAME/kinexus-ai/settings/secrets/actions`
2. Click "New repository secret"
3. For each secret above:
   - Name: Use the exact name shown (e.g., `JIRA_BASE_URL`)
   - Secret: Paste your actual value
   - Click "Add secret"

## Verification

After adding all 7 secrets, you should see them listed (values hidden) at:
`https://github.com/YOUR-USERNAME/kinexus-ai/settings/secrets/actions`

The secrets will be available to the GitHub Actions workflow and passed as:
- CDK context variables (Jira/Confluence credentials)
- Lambda environment variables
- AWS credentials for deployment

## Security Note

These credentials are stored securely in GitHub Secrets and are:
- Encrypted at rest
- Only accessible during workflow runs
- Never exposed in logs (GitHub automatically masks them)
- Passed to Lambda functions as environment variables
