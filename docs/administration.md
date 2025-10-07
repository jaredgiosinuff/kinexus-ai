# Administration Guide

This comprehensive guide covers all administrative aspects of Kinexus AI, from user management to system configuration and monitoring.

## 🎛️ Admin Dashboard Overview

The React-based admin dashboard provides centralized management for all Kinexus AI components:

- **System Health Monitoring**: Real-time metrics and status
- **User & Role Management**: Complete access control
- **Integration Management**: Configure and monitor external systems
- **AI Agent Monitoring**: Track agent performance and conversations
- **Configuration Management**: System-wide settings and policies

**Access**: http://localhost:3107 (development) or your deployed admin URL

## 🔐 Authentication & Access Control

### Dual Authentication System

Kinexus AI supports both AWS Cognito and local authentication:

#### AWS Cognito Integration
```bash
# Environment configuration
AWS_COGNITO_USER_POOL_ID=your_pool_id
AWS_COGNITO_CLIENT_ID=your_client_id
AWS_COGNITO_REGION=us-east-1
ENABLE_COGNITO_AUTH=true
```

#### Local Authentication
```bash
# Environment configuration
ENABLE_LOCAL_AUTH=true
JWT_SECRET=your_secret_key
TOKEN_EXPIRES_IN=24h
```

### Role-Based Access Control (RBAC)

#### Built-in Roles

**Super Admin**
- Full system access
- User management
- System configuration
- Integration management

**Admin**
- User management (limited)
- Integration monitoring
- Agent management
- System monitoring

**Manager**
- Team user management
- Integration status viewing
- Agent conversation monitoring
- Report generation

**User**
- Document management
- Basic agent interaction
- Personal settings

#### Custom Roles

Create custom roles via API:
```bash
curl -X POST http://localhost:3105/api/admin/roles \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "Documentation Manager",
    "permissions": [
      "documents:read",
      "documents:write",
      "agents:invoke",
      "integrations:view"
    ]
  }'
```

### User Management

#### Creating Users

**Via Admin Dashboard:**
1. Navigate to Users → Add User
2. Fill in user details and role
3. Choose authentication method
4. Send invitation email

**Via API:**
```bash
curl -X POST http://localhost:3105/api/admin/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "email": "user@company.com",
    "name": "John Doe",
    "role": "user",
    "authentication_method": "local"
  }'
```

#### User Status Management

- **Active**: Full system access
- **Inactive**: No login access, data preserved
- **Suspended**: Temporary access restriction
- **Pending**: Awaiting email verification

## 🤖 AI Agent Administration

### Agent Configuration

#### Available Agents

**DocumentOrchestrator** (Claude 4 Opus 4.1)
- Primary coordination agent
- Handles complex reasoning tasks
- High cost, reserved for critical decisions

**ChangeAnalyzer** (Claude 4 Sonnet)
- Fast change detection and analysis
- 1M token context window
- Optimized for real-time processing

**ContentCreator** (Nova Pro + Canvas)
- Document generation and updates
- Multi-modal content creation
- Style-preserving updates

**QualityController** (Nova Pro)
- Quality assurance and compliance
- Consistency validation
- Enterprise standards enforcement

**WebAutomator** (Nova Act)
- Browser automation
- Legacy system integration
- Complex UI interactions

#### Agent Configuration

```bash
# Configure agent settings
curl -X PUT http://localhost:3105/api/admin/agents/document-orchestrator \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "model": "claude-4-opus-4.1",
    "max_tokens": 4096,
    "temperature": 0.1,
    "reasoning_pattern": "chain_of_thought",
    "confidence_threshold": 0.8,
    "cost_limit_per_hour": 50.00
  }'
```

### Agent Monitoring

#### Real-Time Conversation Tracking

Monitor agent conversations and reasoning:

```bash
# Get active conversations
curl http://localhost:3105/api/admin/agents/conversations \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get conversation details
curl http://localhost:3105/api/admin/agents/conversations/{conversation_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### Performance Metrics

Track agent performance through the dashboard:

- **Response Times**: Average processing time per agent
- **Confidence Scores**: Quality of agent responses
- **Token Usage**: Cost tracking and optimization
- **Success Rates**: Successful task completion rates
- **Error Rates**: Failed invocations and causes

### Cost Management

#### Budget Controls

Set spending limits per agent:
```bash
curl -X PUT http://localhost:3105/api/admin/agents/budget \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "agent_id": "document-orchestrator",
    "daily_limit": 100.00,
    "monthly_limit": 2000.00,
    "alert_threshold": 0.8
  }'
```

#### Cost Optimization

- **Model Selection**: Choose appropriate models for tasks
- **Batch Processing**: Group similar requests
- **Caching**: Store frequent responses
- **Fallback Models**: Use cheaper models when possible

## 🔌 Integration Management

### Supported Integrations

#### Current Integrations (15+)

**Documentation Platforms:**
- Confluence
- SharePoint
- Google Drive
- Notion
- GitBook

**Development Tools:**
- GitHub
- GitLab
- Jira
- Azure DevOps

**Communication:**
- Slack
- Microsoft Teams
- Discord

**Project Management:**
- Monday.com
- Asana
- Trello

**Enterprise Systems:**
- ServiceNow
- Salesforce

### Integration Configuration

#### Adding New Integration

**Via Admin Dashboard:**
1. Navigate to Integrations → Add Integration
2. Select integration type
3. Configure authentication and settings
4. Test connection
5. Enable sync

**Via API:**
```bash
curl -X POST http://localhost:3105/api/admin/integrations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "GitHub",
    "type": "github",
    "config": {
      "organization": "your-org",
      "token": "ghp_token",
      "webhook_url": "http://your-domain/api/webhooks/github",
      "sync_frequency": "real-time"
    },
    "enabled": true
  }'
```

#### Integration Health Monitoring

Monitor integration status:

```bash
# Get all integration statuses
curl http://localhost:3105/api/admin/integrations/status \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Get specific integration health
curl http://localhost:3105/api/admin/integrations/{integration_id}/health \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Webhook Management

#### Configuring Webhooks

Set up webhook endpoints for real-time events:

```bash
curl -X POST http://localhost:3105/api/admin/webhooks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "source": "github",
    "events": ["push", "pull_request"],
    "endpoint": "/api/webhooks/github",
    "secret": "webhook_secret",
    "enabled": true
  }'
```

#### Webhook Security

- **Secret Validation**: Verify webhook signatures
- **IP Whitelisting**: Restrict webhook sources
- **Rate Limiting**: Prevent webhook abuse
- **Audit Logging**: Track all webhook events

## 📊 System Monitoring

### Prometheus Metrics

#### Available Metrics (15+)

**System Health:**
- `kinexus_http_requests_total`: HTTP request counts
- `kinexus_http_request_duration_seconds`: Request latency
- `kinexus_database_connections_active`: Database connections
- `kinexus_redis_connections_active`: Redis connections

**Agent Performance:**
- `kinexus_agent_invocations_total`: Agent usage counts
- `kinexus_agent_response_time_seconds`: Agent response times
- `kinexus_agent_confidence_score`: Agent confidence levels
- `kinexus_agent_cost_dollars`: Agent costs

**Integration Health:**
- `kinexus_integration_status`: Integration health status
- `kinexus_webhook_events_total`: Webhook event counts
- `kinexus_sync_operations_total`: Sync operation counts

#### Grafana Dashboards

Pre-built dashboards included:

**System Overview Dashboard:**
- System health summary
- Request rates and latency
- Database and cache performance
- Error rates and alerts

**Agent Performance Dashboard:**
- Agent usage patterns
- Response times and confidence
- Cost tracking and optimization
- Conversation flow analysis

**Integration Status Dashboard:**
- Integration health matrix
- Sync operation status
- Webhook event monitoring
- Error tracking and resolution

### Alerting

#### Alert Configuration

Set up alerts for critical events:

```bash
curl -X POST http://localhost:3105/api/admin/alerts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "name": "High Agent Costs",
    "condition": "kinexus_agent_cost_dollars > 100",
    "severity": "warning",
    "notification_channels": ["email", "slack"],
    "enabled": true
  }'
```

#### Notification Channels

**Email Notifications:**
```bash
ALERT_EMAIL_SMTP_HOST=smtp.gmail.com
ALERT_EMAIL_SMTP_PORT=587
ALERT_EMAIL_USERNAME=alerts@company.com
ALERT_EMAIL_PASSWORD=app_password
```

**Slack Integration:**
```bash
ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
ALERT_SLACK_CHANNEL=#alerts
```

## 🔧 System Configuration

### Environment Variables

#### Core Configuration

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kinexus_prod
DB_USER=kinexus_user
DB_PASSWORD=secure_password

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=20

# AWS/Bedrock
AWS_REGION=us-east-1
BEDROCK_REGION=us-east-1
BEDROCK_ENDPOINT_URL=https://bedrock-runtime.us-east-1.amazonaws.com

# Features
ENABLE_MULTI_AGENT_AUTOMATION=true
ENABLE_METRICS=true
ENABLE_REAL_TIME_MONITORING=true
```

#### Security Configuration

```bash
# Authentication
JWT_SECRET=your_secure_jwt_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:3000", "https://your-domain.com"]
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=200
```

### Database Administration

#### Backup & Recovery

**Automated Backups:**
```bash
# Configure backup schedule
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=kinexus-backups
```

**Manual Backup:**
```bash
# Create backup
./scripts/backup-database.sh

# Restore from backup
./scripts/restore-database.sh backup-2025-01-15.sql
```

#### Database Maintenance

```bash
# Run database maintenance
curl -X POST http://localhost:3105/api/admin/maintenance/database \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"operation": "vacuum", "tables": ["documents", "reviews"]}'

# Update statistics
curl -X POST http://localhost:3105/api/admin/maintenance/database \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"operation": "analyze"}'
```

## 🔍 Audit & Compliance

### Audit Logging

#### Audit Trail Configuration

```bash
# Enable comprehensive audit logging
ENABLE_AUDIT_LOGGING=true
AUDIT_LOG_LEVEL=INFO
AUDIT_LOG_RETENTION_DAYS=365
```

#### Audit Log Categories

- **Authentication Events**: Login, logout, failed attempts
- **User Management**: User creation, role changes, deactivation
- **Agent Activities**: Agent invocations, responses, costs
- **Integration Events**: Sync operations, webhook events
- **Configuration Changes**: System settings, integration configs
- **Data Access**: Document views, edits, downloads

#### Compliance Reports

Generate compliance reports:

```bash
# Generate user activity report
curl -X POST http://localhost:3105/api/admin/reports/user-activity \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "format": "pdf"
  }'

# Generate data access report
curl -X POST http://localhost:3105/api/admin/reports/data-access \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "user_id": "user-uuid",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }'
```

## 🛠️ Maintenance & Troubleshooting

### Routine Maintenance

#### Daily Tasks
- Review system health metrics
- Check integration statuses
- Monitor agent costs and usage
- Review security alerts

#### Weekly Tasks
- Analyze performance trends
- Review user activity reports
- Update integration configurations
- Test backup and recovery procedures

#### Monthly Tasks
- Audit user access and roles
- Review and optimize agent configurations
- Analyze cost trends and optimization opportunities
- Update security policies and procedures

### Troubleshooting

#### Common Issues

**High Agent Costs:**
```bash
# Review agent usage
curl http://localhost:3105/api/admin/agents/usage \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Set cost limits
curl -X PUT http://localhost:3105/api/admin/agents/budget \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"daily_limit": 50.00}'
```

**Integration Failures:**
```bash
# Check integration health
curl http://localhost:3105/api/admin/integrations/status \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Restart failed integration
curl -X POST http://localhost:3105/api/admin/integrations/{id}/restart \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Performance Issues:**
```bash
# Check system metrics
curl http://localhost:3105/metrics

# Review database performance
curl http://localhost:3105/api/admin/system/database/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Emergency Procedures

#### System Recovery

**Service Restart:**
```bash
# Restart API service
./scripts/restart-api.sh

# Restart all services
./scripts/restart-all.sh
```

**Database Recovery:**
```bash
# Emergency database restore
./scripts/emergency-restore.sh latest-backup.sql

# Rebuild indexes
./scripts/rebuild-indexes.sh
```

**Agent Recovery:**
```bash
# Reset agent states
curl -X POST http://localhost:3105/api/admin/agents/reset \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Clear agent caches
curl -X POST http://localhost:3105/api/admin/agents/clear-cache \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 📞 Support & Resources

### Admin Support Contacts

- **Technical Issues**: admin-support@kinexusai.com
- **Security Concerns**: security@kinexusai.com
- **Billing Questions**: billing@kinexusai.com

### Documentation Resources

- **API Documentation**: [API Reference](api-reference.md)
- **Security Guide**: [Security](security.md)
- **Deployment Guide**: [Deployment](deployment.md)
- **Operations Guide**: [Operations](operations.md)

### Community Resources

- **GitHub Issues**: Report technical issues
- **Community Forum**: Admin best practices and discussions
- **Knowledge Base**: Comprehensive troubleshooting guides