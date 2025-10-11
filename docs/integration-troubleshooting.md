# Integration Troubleshooting Guide

This guide helps resolve common issues when setting up and using Kinexus AI integrations.

## 🚨 Quick Diagnostics

### System Health Check
```bash
# Check all services
./quick-start.sh status

# Test integration endpoints
curl http://localhost:3105/api/integrations
curl http://localhost:3105/health

# View integration logs
./quick-start.sh logs api | grep -i integration
```

### Integration Status Dashboard
Access the admin dashboard for real-time status:
```
http://localhost:3107/integrations
```

---

## Common Integration Issues

### 🔐 Authentication Failures

#### Symptom: "HTTP 401 Unauthorized"
```json
{
  "error": "Authentication failed",
  "status": 401
}
```

**Root Causes & Solutions:**

**1. Expired API Token (2025 Update)**
- **Problem**: API tokens now expire (1-365 days)
- **Solution**:
  ```bash
  # Check token expiration
  curl -u username:token https://yourcompany.atlassian.net/rest/api/3/myself

  # If expired, generate new token at:
  # https://id.atlassian.com/manage-profile/security/api-tokens
  ```

**2. Incorrect Credentials**
- **Problem**: Wrong username, token, or URL
- **Solution**: Verify credentials step by step
  ```bash
  # Test Confluence
  curl -u "email@company.com:token" \
    "https://company.atlassian.net/wiki/rest/api/space"

  # Test Jira
  curl -u "email@company.com:token" \
    "https://company.atlassian.net/rest/api/3/myself"

  # Test GitHub
  curl -H "Authorization: token ghp_token" \
    "https://api.github.com/user"
  ```

**3. Insufficient Token Scopes**
- **Problem**: Token lacks required permissions
- **Solution**: Update token scopes

  **Confluence Required Scopes:**
  ```
  ✅ read:confluence-content.all
  ✅ write:confluence-content
  ✅ read:confluence-space.summary
  ```

  **Jira Required Scopes:**
  ```
  ✅ read:jira-work
  ✅ write:jira-work
  ✅ read:jira-user
  ```

### 🌐 Connection Timeouts

#### Symptom: "Connection timeout" or "Network unreachable"

**Root Causes & Solutions:**

**1. Network Connectivity**
```bash
# Test basic connectivity
ping yourcompany.atlassian.net
telnet yourcompany.atlassian.net 443

# Test DNS resolution
nslookup yourcompany.atlassian.net
```

**2. Firewall/Proxy Issues**
```bash
# Test with curl verbose mode
curl -v -u username:token \
  "https://yourcompany.atlassian.net/rest/api/3/myself"

# Check for proxy requirements
export http_proxy=http://proxy.company.com:8080
export https_proxy=http://proxy.company.com:8080
```

**3. SSL Certificate Issues**
```bash
# Test SSL certificate
openssl s_client -connect yourcompany.atlassian.net:443

# Ignore SSL errors for testing (not recommended for production)
curl -k -u username:token "https://yourcompany.atlassian.net/rest/api/3/myself"
```

### 📊 Sync Failures

#### Symptom: "Sync completed with errors" or "No data synchronized"

**Root Causes & Solutions:**

**1. Rate Limiting**
```bash
# Check for rate limit headers
curl -I -u username:token \
  "https://yourcompany.atlassian.net/rest/api/3/myself"

# Look for headers:
# X-RateLimit-Remaining: 0
# Retry-After: 3600
```

**Solution**: Implement exponential backoff or reduce sync frequency

**2. Data Format Issues**
```bash
# Check integration logs for parsing errors
./quick-start.sh logs api | grep -E "(parse|format|json)"

# Test individual API responses
curl -u username:token \
  "https://yourcompany.atlassian.net/wiki/rest/api/content/search?cql=space=DEV"
```

**3. Permission Issues**
```bash
# Test specific resource access
curl -u username:token \
  "https://yourcompany.atlassian.net/wiki/rest/api/space/SPACEKEY"

# Check for 403 Forbidden responses
```

### 🎯 Webhook Issues

#### Symptom: "Webhook not receiving events" or "Webhook delivery failed"

**Root Causes & Solutions:**

**1. Webhook URL Configuration**
- **Problem**: Incorrect webhook URL or unreachable endpoint
- **Solution**:
  ```bash
  # Test webhook endpoint accessibility
  curl -X POST http://your-kinexus-domain.com/api/webhooks/github \
    -H "Content-Type: application/json" \
    -d '{"test": "payload"}'

  # Check webhook configuration in source system
  curl -H "Authorization: token github_token" \
    "https://api.github.com/repos/owner/repo/hooks"
  ```

**2. Webhook Secret Mismatch**
- **Problem**: Secret doesn't match between systems
- **Solution**: Verify and update secrets
  ```bash
  # Generate new webhook secret
  openssl rand -hex 20

  # Update in Kinexus AI configuration
  # Update in source system webhook settings
  ```

**3. Payload Format Issues**
```bash
# Check webhook payload logs
./quick-start.sh logs api | grep webhook

# Test webhook processing manually
curl -X POST http://localhost:3105/api/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=signature" \
  -d '{"action": "opened", "pull_request": {}}'
```

---

## Integration-Specific Troubleshooting

### Confluence Issues

#### Issue: "Page not found" when updating
**Solution:**
```bash
# Check page exists and get ID
curl -u username:token \
  "https://company.atlassian.net/wiki/rest/api/content/search?cql=title='Page Title'"

# Verify space access
curl -u username:token \
  "https://company.atlassian.net/wiki/rest/api/space/SPACEKEY"
```

#### Issue: "Version conflict" when updating pages
**Solution:**
```bash
# Get current page version
curl -u username:token \
  "https://company.atlassian.net/wiki/rest/api/content/PAGE_ID?expand=version"

# Update with correct version number
```

### Jira Issues

#### Issue: "Project not found" or "Issue type not available"
**Solution:**
```bash
# List available projects
curl -u username:token \
  "https://company.atlassian.net/rest/api/3/project"

# List issue types for project
curl -u username:token \
  "https://company.atlassian.net/rest/api/3/issuetype"

# Test project access
curl -u username:token \
  "https://company.atlassian.net/rest/api/3/project/PROJECTKEY"
```

#### Issue: "Cannot create issue" or "Required fields missing"
**Solution:**
```bash
# Get project metadata including required fields
curl -u username:token \
  "https://company.atlassian.net/rest/api/3/issue/createmeta?projectKeys=PROJECTKEY"

# Check field requirements and update payload accordingly
```

### GitHub Issues

#### Issue: "Repository not found" or "Access denied"
**Solution:**
```bash
# Test repository access
curl -H "Authorization: token github_token" \
  "https://api.github.com/repos/owner/repository"

# Check token permissions
curl -H "Authorization: token github_token" \
  "https://api.github.com/user/repos?type=all"

# Verify organization membership (if applicable)
curl -H "Authorization: token github_token" \
  "https://api.github.com/user/orgs"
```

#### Issue: "Webhook delivery failed"
**Solution:**
```bash
# Check webhook delivery attempts
curl -H "Authorization: token github_token" \
  "https://api.github.com/repos/owner/repo/hooks/HOOK_ID/deliveries"

# Test webhook endpoint manually
curl -X POST https://your-kinexus-domain.com/api/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"ref": "refs/heads/main"}'
```

### Monday.com Issues

#### Issue: "Board not accessible" or "GraphQL errors"
**Solution:**
```bash
# Test API token
curl -H "Authorization: Bearer monday_token" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { me { name } }"}' \
  https://api.monday.com/v2

# List accessible boards
curl -H "Authorization: Bearer monday_token" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { boards { id name } }"}' \
  https://api.monday.com/v2

# Test specific board access
curl -H "Authorization: Bearer monday_token" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { boards(ids: [BOARD_ID]) { id name } }"}' \
  https://api.monday.com/v2
```

---

## Advanced Debugging

### Enable Debug Logging

#### API Service Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Restart with debug logging
./quick-start.sh restart

# View debug logs
./quick-start.sh logs api | grep -E "(DEBUG|integration)"
```

#### Integration-Specific Debugging
```python
# Add to integration configuration
{
  "config": {
    "debug_mode": true,
    "log_requests": true,
    "log_responses": true
  }
}
```

### Network Debugging

#### Capture HTTP Traffic
```bash
# Using tcpdump (requires root)
sudo tcpdump -i any -w capture.pcap host yourcompany.atlassian.net

# Using curl with detailed output
curl -v -u username:token \
  "https://yourcompany.atlassian.net/rest/api/3/myself" \
  2>&1 | tee curl-debug.log
```

#### Test with Different Tools
```bash
# Using wget
wget --user=username --password=token \
  "https://yourcompany.atlassian.net/rest/api/3/myself"

# Using httpie
http GET https://yourcompany.atlassian.net/rest/api/3/myself \
  Authorization:"Basic $(echo -n username:token | base64)"
```

### Database Debugging

#### Check Integration Records
```bash
# Connect to database
./quick-start.sh exec postgres psql -U kinexus_user -d kinexus_dev

# Query integrations
SELECT id, name, type, enabled, last_sync, status FROM integrations;

# Check sync history
SELECT * FROM integration_sync_logs WHERE integration_id = 'your_id'
ORDER BY created_at DESC LIMIT 10;
```

---

## Performance Issues

### Slow Sync Performance

#### Symptoms
- Sync takes longer than expected
- High memory/CPU usage during sync
- Timeout errors

#### Solutions

**1. Optimize Sync Parameters**
```json
{
  "config": {
    "batch_size": 50,
    "max_concurrent_requests": 5,
    "request_timeout": 30,
    "max_pages_per_update": 3
  }
}
```

**2. Implement Incremental Sync**
```json
{
  "config": {
    "incremental_sync": true,
    "last_sync_timestamp": "2025-10-11T10:00:00Z",
    "sync_window_hours": 24
  }
}
```

**3. Monitor Resource Usage**
```bash
# Check container resource usage
./quick-start.sh exec api top

# Monitor memory usage
./quick-start.sh exec api free -h

# Check API response times
curl -w "%{time_total}" -u username:token \
  "https://yourcompany.atlassian.net/rest/api/3/myself"
```

### Rate Limiting Issues

#### Symptoms
- HTTP 429 responses
- Slow API responses
- "Rate limit exceeded" errors

#### Solutions

**1. Implement Exponential Backoff**
```json
{
  "config": {
    "retry_policy": {
      "max_retries": 3,
      "backoff_factor": 2,
      "base_delay": 1
    }
  }
}
```

**2. Reduce Request Frequency**
```json
{
  "config": {
    "sync_frequency": "hourly",
    "concurrent_requests": 3,
    "request_delay": 1000
  }
}
```

---

## Emergency Recovery

### Integration Recovery Steps

**1. Stop All Integrations**
```bash
# Disable all integrations
curl -X POST http://localhost:3105/api/integrations/disable-all

# Stop sync processes
./quick-start.sh restart
```

**2. Reset Integration State**
```bash
# Reset integration sync status
curl -X POST http://localhost:3105/api/integrations/{id}/reset

# Clear error states
curl -X DELETE http://localhost:3105/api/integrations/{id}/errors
```

**3. Verify System Health**
```bash
# Check system health
curl http://localhost:3105/health

# Verify database connectivity
./quick-start.sh exec postgres pg_isready

# Test core services
curl http://localhost:3105/api/status
```

**4. Gradual Re-enable**
```bash
# Re-enable integrations one by one
curl -X PUT http://localhost:3105/api/integrations/{id} \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Monitor each integration after enabling
./quick-start.sh logs api | grep "integration_id"
```

---

## Support Resources

### Documentation
- [Integration Guide](integrations.md) - Main integration documentation
- [Configuration Guide](integration-configuration.md) - Step-by-step setup
- [API Documentation](http://localhost:3105/docs) - REST API reference

### System Information
- **Health Check**: http://localhost:3105/health
- **Metrics**: http://localhost:3105/metrics
- **Admin Dashboard**: http://localhost:3107
- **API Docs**: http://localhost:3105/docs

### Debug Commands
```bash
# View all integration status
curl http://localhost:3105/api/integrations | jq '.[].status'

# Test specific integration
curl -X POST http://localhost:3105/api/integrations/{id}/test

# View recent logs
./quick-start.sh logs api --tail 100 | grep integration

# Check database connections
./quick-start.sh exec postgres pg_stat_activity
```

### Contact Information
- **Technical Issues**: Create issue at repository
- **Configuration Help**: Refer to [Configuration Guide](integration-configuration.md)
- **API Questions**: Check [API Documentation](http://localhost:3105/docs)

---

This troubleshooting guide covers the most common integration issues. For additional help, consult the specific integration documentation or system logs.