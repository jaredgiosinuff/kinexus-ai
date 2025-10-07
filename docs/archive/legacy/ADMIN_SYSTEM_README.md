# Kinexus AI - Complete Admin System

## 🚀 Overview

This is a comprehensive, enterprise-grade admin system for Kinexus AI that provides advanced management capabilities, real-time monitoring, and configurable integrations. Built with modern technologies and designed for scalability.

## ✨ Key Features

### 🔐 Advanced Authentication
- **Dual Authentication Support**: AWS Cognito and Local authentication
- **Admin Interface**: Switch between authentication providers seamlessly
- **Role-Based Access Control**: Granular permissions system
- **Session Management**: Secure token-based authentication with refresh tokens

### 🎯 Agent Management & Monitoring
- **Advanced AI Reasoning**: Multiple reasoning patterns (Chain of Thought, Tree of Thought, Multi-Perspective, etc.)
- **Multi-Model Support**: Claude 4 Opus/Sonnet, Amazon Nova Pro/Lite/Micro, GPT-4 Turbo
- **Real-Time Conversation Tracking**: Monitor agent conversations and reasoning chains
- **Performance Analytics**: Confidence scores, token usage, costs, and timing metrics

### 📊 Comprehensive Monitoring
- **Structured Logging**: Category-based logging with context management
- **Prometheus Metrics**: 15+ detailed metrics for system health and performance
- **Grafana Dashboards**: Pre-built dashboards for system overview and agent performance
- **Real-Time Alerts**: Configurable alerting for system issues

### 🔌 Integration Framework
- **15+ Supported Integrations**: Monday.com, SharePoint, ServiceNow, GitHub, Jira, Slack, and more
- **Webhook Support**: Real-time event processing
- **Configurable Sync**: Bidirectional sync with customizable frequencies
- **Error Handling**: Robust retry mechanisms and error tracking

### 🎛️ Admin Dashboard
- **React-Based UI**: Modern, responsive admin interface
- **Real-Time Metrics**: Live system performance data
- **Integration Management**: Configure and monitor all integrations
- **User Management**: Complete user and role administration
- **System Health**: Comprehensive health monitoring

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Admin Dashboard (React)                  │
├─────────────────────────────────────────────────────────────────┤
│                        Admin API Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Authentication  │  Agent Management  │  Integration Management │
│   Service        │     Service        │        Service          │
├─────────────────────────────────────────────────────────────────┤
│   Logging        │    Metrics         │    Conversation         │
│   Service        │    Service         │    Repository           │
├─────────────────────────────────────────────────────────────────┤
│              Database Layer (PostgreSQL/SQLite)                 │
├─────────────────────────────────────────────────────────────────┤
│  External Integrations: Monday.com, SharePoint, ServiceNow...   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install frontend dependencies (if using React admin interface)
cd frontend && npm install
```

### 2. Database Setup

```bash
# Initialize database
alembic upgrade head

# Run setup script
python scripts/setup_admin_system.py
```

### 3. Start Services

```bash
# Start API server
uvicorn src.api.main:app --reload --port 8000

# Start admin interface (React)
cd frontend && npm start

# Start agent workers
python src/agents/orchestrator.py --dev
```

### 4. Access Admin Dashboard

- **Admin Interface**: http://localhost:3000/admin
- **API Documentation**: http://localhost:8000/docs
- **Metrics Endpoint**: http://localhost:8000/metrics

**Default Admin Credentials**:
- Email: `admin@kinexusai.com`
- Password: `KinexusAdmin2024!` (Change immediately!)

## 📖 Component Details

### Authentication System

#### Cognito Configuration
```python
# Configure via admin interface or API
{
    "type": "cognito",
    "config": {
        "user_pool_id": "us-east-1_xxxxxxxxx",
        "client_id": "your-client-id",
        "region": "us-east-1"
    }
}
```

#### Local Authentication
```python
# Default configuration
{
    "type": "local",
    "config": {
        "jwt_secret": "auto-generated",
        "token_expiry_hours": 24
    }
}
```

### Agent Reasoning Patterns

The system supports multiple advanced reasoning patterns:

1. **Linear**: Standard sequential reasoning
2. **Chain of Thought**: Step-by-step logical reasoning
3. **Tree of Thought**: Branching exploration of possibilities
4. **Multi-Perspective**: Multiple viewpoint analysis
5. **Critique & Refine**: Self-improving iterative reasoning
6. **Ensemble**: Multiple model consensus

### Integration Configuration

#### Monday.com Integration
```python
{
    "name": "Company Monday",
    "type": "monday",
    "config": {
        "boards": [12345, 67890],
        "webhook_events": ["create_item", "change_column_value"]
    },
    "auth_config": {
        "api_key": "your-monday-api-key"
    }
}
```

#### SharePoint Integration
```python
{
    "name": "SharePoint Docs",
    "type": "sharepoint",
    "config": {
        "site_url": "https://company.sharepoint.com/sites/docs",
        "libraries": ["Shared Documents", "Policies"],
        "file_types": ["docx", "pdf", "pptx"]
    }
}
```

### Metrics & Monitoring

#### Key Metrics Collected
- Agent reasoning duration and patterns
- Model usage and costs
- API request rates and latencies
- Error rates and types
- Integration sync status
- System resource usage

#### Grafana Dashboards
1. **System Overview** (`kinexus-ai-overview.json`)
   - Request rates and latencies
   - Component health status
   - Error rates
   - Active reasoning chains

2. **Agent Performance** (`kinexus-ai-agents.json`)
   - Reasoning duration percentiles
   - Confidence score distributions
   - Model usage and costs
   - Token consumption rates

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/kinexus

# Authentication
JWT_SECRET=your-jwt-secret
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_CLIENT_ID=your-client-id

# Integrations
MONDAY_API_KEY=your-monday-key
SHAREPOINT_CLIENT_ID=your-sp-client-id
SERVICENOW_API_KEY=your-sn-key

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

### Admin Interface Configuration

The admin interface supports:
- **Authentication Provider Selection**: Switch between Cognito and local auth
- **Integration Management**: Add, configure, test, and monitor integrations
- **User Management**: Create users, assign roles, manage permissions
- **System Monitoring**: Real-time metrics and health status
- **Agent Conversation Tracking**: Monitor and analyze agent interactions

## 📊 API Endpoints

### Admin API
```
GET    /api/admin/metrics              # System metrics
GET    /api/admin/conversations        # Agent conversations
GET    /api/admin/conversations/{id}   # Conversation details
GET    /api/admin/auth/config          # Auth configuration
PUT    /api/admin/auth/config          # Update auth config
GET    /api/admin/integrations         # All integrations
POST   /api/admin/integrations         # Create integration
PUT    /api/admin/integrations/{id}    # Update integration
DELETE /api/admin/integrations/{id}    # Delete integration
GET    /api/admin/integrations/{id}/test # Test integration
```

### Monitoring Endpoints
```
GET    /metrics                        # Prometheus metrics
GET    /health                         # Health check
GET    /api/admin/system/health        # Detailed health
```

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Issues**
   - Check JWT secret configuration
   - Verify Cognito settings if using AWS Cognito
   - Ensure user has proper roles assigned

2. **Integration Connection Failures**
   - Verify API keys and credentials
   - Check network connectivity
   - Review integration-specific logs

3. **Metrics Not Appearing**
   - Ensure Prometheus is configured correctly
   - Check metric collection service status
   - Verify Grafana data source configuration

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Start with enhanced logging
python src/api/main.py --debug
```

### Health Checks

```bash
# Check system health
curl http://localhost:8000/health

# Check admin API
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/admin/metrics
```

## 🔒 Security Considerations

### Authentication Security
- JWT tokens with configurable expiry
- Secure password hashing with bcrypt
- Session management with automatic cleanup
- Rate limiting on authentication endpoints

### Integration Security
- Encrypted credential storage
- API key rotation support
- Webhook signature verification
- SSL/TLS for all external communications

### Admin Interface Security
- Role-based access control
- Admin-only endpoints protection
- CSRF protection
- XSS prevention

## 📈 Performance & Scaling

### Database Optimization
- Indexed queries for conversation tracking
- Efficient metrics aggregation
- Connection pooling
- Read replicas support

### Caching Strategy
- Redis for session storage
- Metric caching for dashboards
- Integration response caching
- Query result caching

### Monitoring Performance
- Response time tracking
- Database query performance
- Integration sync performance
- Resource usage monitoring

## 🎯 Future Enhancements

### Planned Features
- Multi-tenant support
- Advanced analytics and ML insights
- Custom dashboard builder
- Integration marketplace
- Automated troubleshooting
- Enhanced security features

### Integration Roadmap
- Slack (enhanced)
- Microsoft Teams
- Google Workspace
- Notion
- Asana/Trello
- Zendesk/Freshdesk

## 🤝 Contributing

This admin system is designed to be extensible. Key extension points:

1. **New Integrations**: Extend `BaseIntegration` class
2. **Custom Metrics**: Add to `MetricsService`
3. **Authentication Providers**: Extend `AuthService`
4. **Reasoning Patterns**: Add to `BaseAgent`

## 📚 Documentation

- **API Documentation**: Available at `/docs` when running
- **Integration Guides**: See `src/integrations/` for examples
- **Configuration Reference**: Check environment variable examples
- **Troubleshooting Guide**: This README and log files

## 🏆 System Highlights

This admin system represents a **production-ready, enterprise-grade** solution with:

- ✅ **Complete authentication system** with dual provider support
- ✅ **Advanced AI agent management** with multi-model reasoning
- ✅ **Comprehensive monitoring** with Prometheus and Grafana
- ✅ **Robust integration framework** with 15+ supported services
- ✅ **Real-time conversation tracking** for AI agents
- ✅ **Modern React admin interface** with live updates
- ✅ **Production-ready architecture** with proper error handling
- ✅ **Extensive logging and metrics** for observability
- ✅ **Role-based security** with granular permissions
- ✅ **Scalable design** ready for enterprise deployment

The system is designed to handle the complete lifecycle of AI document management, from change detection through agent reasoning to document updates, all while providing comprehensive visibility and control through the admin interface.