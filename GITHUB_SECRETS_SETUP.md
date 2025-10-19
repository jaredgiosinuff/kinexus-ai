# GitHub Secrets Setup for Jira/Confluence Integration

## Required Secrets

Add these secrets to your GitHub repository at:
`https://github.com/jaredgiosinuff/kinexus-ai/settings/secrets/actions`

### 1. JIRA_BASE_URL
```
https://jared-cluff.atlassian.net
```

### 2. JIRA_EMAIL
```
jbcluff@gmail.com
```

### 3. JIRA_API_TOKEN
```
(Use the Jira API token you created - starts with ATATT...)
```
**Note:** This should be the actual Jira API token you already have.

### 4. CONFLUENCE_URL
```
https://jared-cluff.atlassian.net/wiki
```

## Steps to Add Secrets

1. Go to: https://github.com/jaredgiosinuff/kinexus-ai/settings/secrets/actions
2. Click "New repository secret"
3. For each secret above:
   - Name: Use the exact name shown (e.g., `JIRA_BASE_URL`)
   - Secret: Paste the value from above
   - Click "Add secret"

## Verification

After adding all 4 secrets, you should see them listed (values hidden) at:
https://github.com/jaredgiosinuff/kinexus-ai/settings/secrets/actions

The secrets will be available to the GitHub Actions workflow and passed as environment variables to the Lambda functions.

## Security Note

These credentials are stored securely in GitHub Secrets and are:
- Encrypted at rest
- Only accessible during workflow runs
- Never exposed in logs (GitHub automatically masks them)
- Passed to Lambda functions as environment variables
