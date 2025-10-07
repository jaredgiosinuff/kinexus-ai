# Kinexus AI Infrastructure Guide

This document describes the infrastructure architecture and deployment options for Kinexus AI.

## 🏗️ Architecture Overview

Kinexus AI supports two deployment models:

### 1. MVP Stack (Quick Demo/Development)
- **Lambda Functions**: Event-driven processing
- **DynamoDB**: NoSQL database for rapid development
- **S3**: Document storage
- **API Gateway**: HTTP endpoints
- **EventBridge**: Event orchestration

### 2. Production Stack (Enterprise Scale)
- **ECS Fargate**: Containerized application hosting
- **RDS PostgreSQL**: Managed relational database
- **ElastiCache Redis**: In-memory caching
- **Application Load Balancer**: High availability
- **VPC**: Network isolation
- **CloudWatch**: Monitoring and alerting
- **Backup & DR**: Automated backups and disaster recovery

## 🚀 Deployment Options

### Quick Start (MVP)
```bash
# Deploy MVP stack for development/demo
./scripts/deploy-aws.sh --environment development --type mvp
```

### Production Deployment
```bash
# Deploy full production stack
./scripts/deploy-aws.sh \
    --environment production \
    --type production \
    --account 123456789012 \
    --region us-east-1 \
    --build-images
```

### Staging Environment
```bash
# Deploy staging environment
./scripts/deploy-aws.sh \
    --environment staging \
    --type production \
    --account 123456789012 \
    --build-images \
    --diff
```

## 📋 Prerequisites

### AWS Account Setup
1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Configured with credentials
3. **AWS CDK**: Version 2.x installed globally
4. **Docker**: For building container images (production only)

### Required Permissions
The deploying user/role needs permissions for:
- CloudFormation stack operations
- ECS, RDS, ElastiCache, EC2, VPC management
- IAM role and policy management
- S3 bucket operations
- Lambda function deployment
- Secrets Manager access

### Environment Configuration
```bash
# Set up AWS profile (recommended)
aws configure --profile kinexus-prod

# Or export credentials
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

## 🏛️ Production Architecture Details

### Network Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                          VPC (10.0.0.0/16)                 │
├─────────────────────────────────────────────────────────────┤
│  Public Subnets (3 AZs)          │  Private Subnets (3 AZs) │
│  ┌─────────────────────┐          │  ┌─────────────────────┐ │
│  │ Application         │          │  │ ECS Services        │ │
│  │ Load Balancer       │ ◄────────┤  │ - API Service       │ │
│  │ (Internet-facing)   │          │  │ - Worker Services   │ │
│  └─────────────────────┘          │  └─────────────────────┘ │
│                                   │                          │
│                                   │  Database Subnets       │
│                                   │  ┌─────────────────────┐ │
│                                   │  │ RDS PostgreSQL      │ │
│                                   │  │ ElastiCache Redis   │ │
│                                   │  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Security Architecture
- **VPC Isolation**: Private subnets for application and database tiers
- **Security Groups**: Least-privilege network access
- **Secrets Management**: Database credentials in AWS Secrets Manager
- **IAM Roles**: Task-specific permissions with minimal scope
- **Encryption**: At-rest and in-transit encryption

### High Availability
- **Multi-AZ Deployment**: Resources distributed across 3 availability zones
- **Auto Scaling**: ECS services scale based on CPU/memory utilization
- **Database Failover**: RDS Multi-AZ for automatic failover
- **Load Balancing**: ALB distributes traffic with health checks

## 🛠️ Infrastructure Components

### ECS Fargate Cluster
```yaml
Configuration:
  - Cluster: kinexus-production
  - Service: API Service (2-10 tasks)
  - Task Definition: 2GB RAM, 1 vCPU
  - Auto Scaling: CPU/Memory based
  - Health Checks: Application-level
```

### RDS PostgreSQL
```yaml
Configuration:
  - Engine: PostgreSQL 15.4
  - Instance: db.t3.medium (burstable)
  - Storage: 100GB (auto-scaling to 1TB)
  - Multi-AZ: Enabled
  - Backups: 7-day retention
  - Encryption: Enabled
```

### ElastiCache Redis
```yaml
Configuration:
  - Node Type: cache.t3.micro
  - Cluster Mode: Single node (can be upgraded)
  - Backup: 5-day retention
  - Encryption: In-transit and at-rest
```

### Application Load Balancer
```yaml
Configuration:
  - Scheme: Internet-facing
  - Listeners: HTTP (80), HTTPS (443)
  - Target Groups: ECS services
  - Health Checks: /health endpoint
  - SSL: AWS Certificate Manager
```

## 🗂️ Environment Management

### Environment Variables
Each environment (dev/staging/prod) has its own configuration:

#### Development
```bash
ENVIRONMENT=development
DB_HOST=localhost
REDIS_HOST=localhost
DEBUG=true
LOG_LEVEL=DEBUG
```

#### Staging
```bash
ENVIRONMENT=staging
DB_HOST=kinexus-staging.cluster-xxx.us-east-1.rds.amazonaws.com
REDIS_HOST=kinexus-staging.xxx.cache.amazonaws.com
DEBUG=false
LOG_LEVEL=INFO
```

#### Production
```bash
ENVIRONMENT=production
DB_HOST=kinexus-prod.cluster-xxx.us-east-1.rds.amazonaws.com
REDIS_HOST=kinexus-prod.xxx.cache.amazonaws.com
DEBUG=false
LOG_LEVEL=WARNING
```

### Secrets Management
Sensitive configuration is stored in AWS Secrets Manager:
- Database credentials
- JWT signing keys
- External API keys
- SSL certificates

## 📊 Monitoring and Observability

### CloudWatch Integration
- **Custom Metrics**: Application-specific metrics
- **Log Aggregation**: Centralized logging from all services
- **Alarms**: Automated alerts for critical metrics
- **Dashboards**: Real-time operational visibility

### Key Metrics Monitored
- **Application**: Request latency, error rates, throughput
- **Infrastructure**: CPU, memory, disk utilization
- **Database**: Connection count, query performance
- **Network**: Load balancer metrics, target health

### Alerting
```yaml
Critical Alerts:
  - High CPU utilization (>80%)
  - Database connection exhaustion
  - Application error rate spike
  - Service health check failures

Warning Alerts:
  - Memory utilization (>70%)
  - Disk space low
  - Slow query performance
```

## 🔄 Backup and Disaster Recovery

### Automated Backups
- **RDS**: Automated daily backups with 7-day retention
- **S3**: Cross-region replication for document storage
- **Configuration**: Infrastructure as Code in Git

### Disaster Recovery Plan
1. **RDS Recovery**: Point-in-time restore from automated backups
2. **Application Recovery**: Deploy from Docker images
3. **Data Recovery**: S3 cross-region replication
4. **Configuration Recovery**: CDK re-deployment

### Recovery Time Objectives
- **RTO (Recovery Time Objective)**: 2 hours
- **RPO (Recovery Point Objective)**: 1 hour
- **Data Loss Tolerance**: Maximum 1 hour

## 🎯 Scaling Strategy

### Horizontal Scaling
- **ECS Services**: Auto-scale from 2-10 tasks
- **Database**: Read replicas for read-heavy workloads
- **Caching**: Redis cluster mode for high throughput

### Vertical Scaling
- **ECS Tasks**: Increase CPU/memory allocation
- **Database**: Upgrade instance class
- **Cache**: Upgrade node types

### Cost Optimization
- **Reserved Instances**: RDS and ElastiCache reservations
- **Spot Instances**: Development environments
- **S3 Lifecycle**: Intelligent tiering for document storage
- **CloudWatch**: Log retention policies

## 🔧 Operational Procedures

### Deployment Process
1. **Pre-deployment**: Run tests, build images
2. **Staging**: Deploy to staging environment
3. **Validation**: Run integration tests
4. **Production**: Blue-green deployment
5. **Monitoring**: Watch metrics for issues
6. **Rollback**: Automated rollback on failure

### Database Migrations
```bash
# Run migrations in ECS task
aws ecs run-task \
    --cluster kinexus-production \
    --task-definition kinexus-migration-task \
    --launch-type FARGATE
```

### Configuration Updates
```bash
# Update secrets
aws secretsmanager update-secret \
    --secret-id kinexus/production/database \
    --secret-string '{"username":"admin","password":"newpass"}'

# Restart services to pick up changes
aws ecs update-service \
    --cluster kinexus-production \
    --service kinexus-api \
    --force-new-deployment
```

## 🚨 Troubleshooting

### Common Issues

#### ECS Task Startup Failures
```bash
# Check task logs
aws logs filter-log-events \
    --log-group-name /ecs/kinexus-api \
    --start-time $(date -d '1 hour ago' +%s)000

# Check task definition
aws ecs describe-task-definition \
    --task-definition kinexus-api:latest
```

#### Database Connection Issues
```bash
# Check RDS status
aws rds describe-db-instances \
    --db-instance-identifier kinexus-production

# Check security groups
aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=kinexus-database-sg"
```

#### Load Balancer Issues
```bash
# Check target health
aws elbv2 describe-target-health \
    --target-group-arn arn:aws:elasticloadbalancing:...

# Check load balancer logs
aws s3 sync s3://kinexus-alb-logs/... ./logs/
```

### Performance Tuning

#### Database Optimization
- **Connection Pooling**: Configure appropriate pool sizes
- **Query Optimization**: Monitor slow query logs
- **Indexing**: Add indexes for frequent queries
- **Read Replicas**: Offload read-heavy operations

#### Application Optimization
- **Caching**: Implement Redis caching strategies
- **Connection Limits**: Tune database connection pools
- **Memory Management**: Monitor for memory leaks
- **Async Processing**: Use background tasks for heavy operations

## 📈 Cost Management

### Monthly Cost Estimates

#### MVP Stack
```
Lambda Functions:    $5-20
DynamoDB:           $10-50
S3 Storage:         $5-25
API Gateway:        $10-40
Total:              $30-135/month
```

#### Production Stack
```
ECS Fargate:        $150-500
RDS PostgreSQL:     $200-800
ElastiCache:        $50-200
ALB:               $25-50
S3 Storage:        $25-100
Data Transfer:     $50-200
Total:             $500-1,850/month
```

### Cost Optimization Strategies
1. **Reserved Instances**: 1-year commitments for predictable workloads
2. **Spot Instances**: Development and testing environments
3. **Auto Scaling**: Scale down during off-peak hours
4. **Resource Monitoring**: Regular review of unused resources
5. **S3 Lifecycle**: Move old data to cheaper storage classes

---

For specific deployment issues or questions, please refer to the troubleshooting section or create an issue in the repository.