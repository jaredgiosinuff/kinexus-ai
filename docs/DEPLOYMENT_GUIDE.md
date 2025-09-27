# Kinexus AI: Deployment Guide

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Deployment](#quick-deployment)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Environment Setup](#environment-setup)
- [Monitoring & Observability](#monitoring--observability)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

## Overview

This guide provides comprehensive instructions for deploying Kinexus AI in various environments, from development to production. The deployment leverages AWS services and Infrastructure as Code (IaC) principles for consistent, reproducible deployments.

### Deployment Options
- **1-Click AWS Deployment**: Automated CloudFormation deployment
- **Terraform Deployment**: Full infrastructure control
- **AWS CDK Deployment**: Code-based infrastructure definition
- **Container Deployment**: Docker/Kubernetes for hybrid environments

## Prerequisites

### AWS Account Requirements
- AWS Account with appropriate permissions
- AWS CLI v2.0+ installed and configured
- Access to AWS Bedrock with Claude 4 and Nova models enabled
- Minimum $100 AWS credits for deployment testing

### Required AWS Services Access
```bash
# Check AWS Bedrock model access
aws bedrock list-foundation-models --region us-east-1

# Required models:
# - anthropic.claude-4-opus-4.1-v1:0
# - anthropic.claude-4-sonnet-v1:0
# - amazon.nova-pro-v1:0
# - amazon.nova-act-v1:0
# - amazon.nova-canvas-v1:0
```

### Local Development Tools
- **Docker**: v20.0+ for containerization
- **Node.js**: v18+ for build tools and CDK
- **Python**: v3.11+ for Lambda functions
- **Terraform**: v1.5+ (optional, for Terraform deployment)
- **AWS CDK**: v2.90+ (for CDK deployment)

### Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:*",
        "lambda:*",
        "apigateway:*",
        "dynamodb:*",
        "s3:*",
        "opensearch:*",
        "iam:*",
        "cloudformation:*",
        "events:*",
        "secretsmanager:*",
        "kms:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Quick Deployment

### 1-Click AWS Deployment

The fastest way to deploy Kinexus AI for evaluation:

```bash
# Clone repository
git clone https://github.com/kinexusai/kinexus-ai.git
cd kinexus-ai

# Run quick deployment script
./scripts/quick-deploy.sh

# This will:
# 1. Validate AWS credentials and permissions
# 2. Deploy CloudFormation stack
# 3. Configure basic integrations
# 4. Set up monitoring
# 5. Provide access URLs
```

**Deployment Time:** ~20 minutes
**Cost:** ~$50-100/month for development workloads

### Quick Deploy Script
```bash
#!/bin/bash
# scripts/quick-deploy.sh

set -e

echo "🚀 Starting Kinexus AI Quick Deployment..."

# Validate prerequisites
echo "📋 Validating prerequisites..."
./scripts/validate-prerequisites.sh

# Set deployment parameters
STACK_NAME="kinexus-ai-dev"
REGION="us-east-1"
TEMPLATE_URL="https://kinexus-templates.s3.amazonaws.com/quick-deploy.yaml"

# Deploy CloudFormation stack
echo "☁️ Deploying CloudFormation stack..."
aws cloudformation create-stack \
  --stack-name $STACK_NAME \
  --template-url $TEMPLATE_URL \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=Environment,ParameterValue=development \
    ParameterKey=InstanceSize,ParameterValue=small \
  --region $REGION

# Wait for stack completion
echo "⏳ Waiting for stack deployment (this may take 15-20 minutes)..."
aws cloudformation wait stack-create-complete \
  --stack-name $STACK_NAME \
  --region $REGION

# Get outputs
echo "📋 Retrieving deployment information..."
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs')

# Extract key URLs
API_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="ApiUrl") | .OutputValue')
DASHBOARD_URL=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="DashboardUrl") | .OutputValue')
API_KEY=$(echo $OUTPUTS | jq -r '.[] | select(.OutputKey=="ApiKey") | .OutputValue')

echo "✅ Deployment Complete!"
echo ""
echo "🔗 Access URLs:"
echo "   Dashboard: $DASHBOARD_URL"
echo "   API Endpoint: $API_URL"
echo "   API Key: $API_KEY"
echo ""
echo "📚 Next Steps:"
echo "   1. Access dashboard: $DASHBOARD_URL"
echo "   2. Review integration guide: docs/INTEGRATION_GUIDE.md"
echo "   3. Configure your first integration"
```

## Production Deployment

### AWS CDK Deployment (Recommended)

Production-grade deployment with full customization:

```bash
# Install dependencies
npm install -g aws-cdk
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT-NUMBER/us-east-1

# Configure environment
cp .env.example .env.prod
# Edit .env.prod with your settings

# Deploy infrastructure
cdk deploy --profile production --context env=production

# Deploy application code
./scripts/deploy-application.sh production
```

### CDK Stack Definition
```python
# infrastructure/kinexus_stack.py
from aws_cdk import (
    Stack, Duration, RemovalPolicy,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_opensearch as opensearch,
    aws_events as events,
    aws_iam as iam,
    aws_kms as kms
)

class KinexusProductionStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # KMS Key for encryption
        self.encryption_key = kms.Key(
            self, "KinexusEncryptionKey",
            description="Kinexus AI encryption key",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # S3 Buckets
        self.document_bucket = s3.Bucket(
            self, "DocumentBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # DynamoDB Tables
        self.documents_table = dynamodb.Table(
            self, "DocumentsTable",
            partition_key=dynamodb.Attribute(
                name="document_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="version",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.ON_DEMAND,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # OpenSearch for vector search
        self.search_domain = opensearch.Domain(
            self, "SearchDomain",
            version=opensearch.EngineVersion.OPENSEARCH_2_9,
            capacity=opensearch.CapacityConfig(
                master_nodes=3,
                master_node_instance_type="m6g.medium.search",
                data_nodes=3,
                data_node_instance_type="r6g.large.search"
            ),
            ebs=opensearch.EbsOptions(
                volume_size=100,
                volume_type=ec2.EbsDeviceVolumeType.GP3
            ),
            encryption_at_rest=opensearch.EncryptionAtRestOptions(
                enabled=True,
                kms_key=self.encryption_key
            ),
            node_to_node_encryption=True,
            enforce_https=True,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # Lambda functions for agents
        self.create_agent_functions()
        
        # API Gateway
        self.api = apigateway.RestApi(
            self, "KinexusAPI",
            rest_api_name="Kinexus AI Production API",
            description="Production API for Kinexus AI",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["https://dashboard.kinexusai.com"],
                allow_methods=["GET", "POST", "PUT", "DELETE"],
                allow_headers=["Content-Type", "Authorization"]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="v1",
                throttling_rate_limit=1000,
                throttling_burst_limit=2000,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            )
        )
        
        # EventBridge for agent coordination
        self.event_bus = events.EventBus(
            self, "KinexusEventBus",
            event_bus_name="kinexus-ai-production"
        )
        
        # Setup monitoring and alarms
        self.setup_monitoring()
    
    def create_agent_functions(self):
        """Create Lambda functions for each AI agent"""
        agents = [
            ("DocumentOrchestrator", "agents.orchestrator"),
            ("ChangeAnalyzer", "agents.change_analyzer"),
            ("ContentCreator", "agents.content_creator"),
            ("WebAutomator", "agents.web_automator"),
            ("QualityController", "agents.quality_controller")
        ]
        
        for agent_name, handler_path in agents:
            function = _lambda.Function(
                self, f"{agent_name}Function",
                runtime=_lambda.Runtime.PYTHON_3_11,
                handler=f"{handler_path}.handler",
                code=_lambda.Code.from_asset("src"),
                timeout=Duration.minutes(15),
                memory_size=3008,  # Maximum for optimal performance
                environment={
                    "DOCUMENTS_TABLE": self.documents_table.table_name,
                    "DOCUMENT_BUCKET": self.document_bucket.bucket_name,
                    "SEARCH_DOMAIN": self.search_domain.domain_endpoint,
                    "EVENT_BUS": self.event_bus.event_bus_name,
                    "KMS_KEY_ID": self.encryption_key.key_id,
                    "ENVIRONMENT": "production"
                },
                dead_letter_queue_enabled=True,
                reserved_concurrent_executions=50
            )
            
            # Grant permissions
            self.documents_table.grant_read_write_data(function)
            self.document_bucket.grant_read_write(function)
            self.encryption_key.grant_encrypt_decrypt(function)
            
            # EventBridge permissions
            self.event_bus.grant_put_events_to(function)
```

### Terraform Deployment (Alternative)

For organizations preferring Terraform:

```hcl
# infrastructure/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "kinexus-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "KinexusAI"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# KMS Key
resource "aws_kms_key" "kinexus" {
  description             = "Kinexus AI encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

# S3 Bucket for documents
resource "aws_s3_bucket" "documents" {
  bucket        = "kinexus-documents-${var.environment}-${random_id.bucket_suffix.hex}"
  force_destroy = var.environment != "production"
}

resource "aws_s3_bucket_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.kinexus.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# DynamoDB Table
resource "aws_dynamodb_table" "documents" {
  name           = "kinexus-documents-${var.environment}"
  billing_mode   = "ON_DEMAND"
  hash_key       = "document_id"
  range_key      = "version"
  
  attribute {
    name = "document_id"
    type = "S"
  }
  
  attribute {
    name = "version"
    type = "N"
  }
  
  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.kinexus.arn
  }
  
  point_in_time_recovery {
    enabled = true
  }
}

# Lambda functions
module "agent_functions" {
  source = "./modules/lambda"
  
  for_each = toset([
    "document-orchestrator",
    "change-analyzer", 
    "content-creator",
    "web-automator",
    "quality-controller"
  ])
  
  function_name = each.key
  environment   = var.environment
  
  environment_variables = {
    DOCUMENTS_TABLE = aws_dynamodb_table.documents.name
    DOCUMENT_BUCKET = aws_s3_bucket.documents.bucket
    KMS_KEY_ID      = aws_kms_key.kinexus.key_id
  }
}
```

## Configuration

### Environment Variables

#### Core Configuration
```bash
# .env.production
ENVIRONMENT=production
AWS_REGION=us-east-1
LOG_LEVEL=INFO

# AWS Services
DOCUMENTS_TABLE=kinexus-documents-prod
DOCUMENT_BUCKET=kinexus-documents-prod-abc123
SEARCH_DOMAIN=https://kinexus-search-prod.us-east-1.es.amazonaws.com
EVENT_BUS=kinexus-ai-production

# AI Models
CLAUDE_4_OPUS_MODEL=anthropic.claude-4-opus-4.1-v1:0
CLAUDE_4_SONNET_MODEL=anthropic.claude-4-sonnet-v1:0
NOVA_PRO_MODEL=amazon.nova-pro-v1:0
NOVA_ACT_MODEL=amazon.nova-act-v1:0

# Security
KMS_KEY_ID=arn:aws:kms:us-east-1:123456789:key/abc123
JWT_SECRET_KEY=stored-in-secrets-manager
API_RATE_LIMIT=1000

# External Integrations
JIRA_BASE_URL=https://company.atlassian.net
CONFLUENCE_BASE_URL=https://company.atlassian.net/wiki
SLACK_BOT_TOKEN=xoxb-stored-in-secrets-manager
```

#### Integration Configuration
```yaml
# config/integrations.yaml
integrations:
  jira:
    enabled: true
    base_url: "${JIRA_BASE_URL}"
    auth_type: "bearer_token"
    projects: ["PROJ", "DEV", "OPS"]
    webhook_events: ["issue_created", "issue_updated"]
    
  confluence:
    enabled: true
    base_url: "${CONFLUENCE_BASE_URL}"
    auth_type: "personal_access_token"
    spaces:
      - key: "DEV"
        auto_publish: true
        review_required: false
      - key: "OPS"
        auto_publish: false
        review_required: true
        
  git:
    providers:
      - type: "github"
        org: "company"
        repositories: ["api-service", "web-app", "mobile-app"]
      - type: "gitlab"
        group: "platform"
        repositories: ["infrastructure", "monitoring"]
        
  slack:
    enabled: true
    channels: ["#development", "#operations", "#architecture"]
    notifications:
      document_updates: true
      quality_alerts: true
      change_completions: true
```

### Quality Standards Configuration
```yaml
# config/quality_standards.yaml
quality_standards:
  minimum_scores:
    overall: 80
    accuracy: 85
    completeness: 75
    readability: 70
    freshness: 90
    
  compliance_rules:
    - name: "accessibility"
      required: true
      checks:
        - alt_text_present
        - heading_structure
        - color_contrast
        
    - name: "security_review"
      required: true
      trigger_on: ["security", "authentication", "authorization"]
      reviewers: ["security-team@company.com"]
      
    - name: "style_guide"
      required: true
      checks:
        - consistent_terminology
        - proper_formatting
        - link_validation
        
  auto_approval_thresholds:
    quality_score: 95
    no_security_content: true
    trusted_authors: ["tech-writing-team@company.com"]
```

## Environment Setup

### Development Environment
```bash
# Development deployment with minimal resources
./scripts/deploy.sh --environment development \
  --instance-size small \
  --enable-debug-logging \
  --skip-production-features
```

### Staging Environment
```bash
# Staging deployment with production-like setup
./scripts/deploy.sh --environment staging \
  --instance-size medium \
  --enable-performance-testing \
  --load-test-data
```

### Production Environment
```bash
# Production deployment with full features
./scripts/deploy.sh --environment production \
  --instance-size large \
  --enable-multi-region \
  --backup-retention 30 \
  --monitoring-level detailed
```

## Monitoring & Observability

### CloudWatch Dashboard Setup
```python
# scripts/setup_monitoring.py
import boto3

def create_kinexus_dashboard():
    cloudwatch = boto3.client('cloudwatch')
    
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Duration", "FunctionName", "KinexusAI-DocumentOrchestrator"],
                        [".", "Errors", ".", "."],
                        [".", "Invocations", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1",
                    "title": "Agent Performance"
                }
            },
            {
                "type": "metric", 
                "properties": {
                    "metrics": [
                        ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "kinexus-documents-prod"],
                        [".", "ConsumedWriteCapacityUnits", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "Database Performance"
                }
            }
        ]
    }
    
    cloudwatch.put_dashboard(
        DashboardName='KinexusAI-Production',
        DashboardBody=json.dumps(dashboard_body)
    )
```

### Custom Metrics
```python
# src/utils/metrics.py
import boto3
import time
from contextlib import contextmanager

cloudwatch = boto3.client('cloudwatch')

@contextmanager
def track_agent_performance(agent_name, operation):
    start_time = time.time()
    try:
        yield
        success = True
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start_time
        
        # Send custom metrics
        cloudwatch.put_metric_data(
            Namespace='KinexusAI/Agents',
            MetricData=[
                {
                    'MetricName': 'OperationDuration',
                    'Dimensions': [
                        {'Name': 'Agent', 'Value': agent_name},
                        {'Name': 'Operation', 'Value': operation}
                    ],
                    'Value': duration,
                    'Unit': 'Seconds'
                },
                {
                    'MetricName': 'OperationSuccess',
                    'Dimensions': [
                        {'Name': 'Agent', 'Value': agent_name},
                        {'Name': 'Operation', 'Value': operation}
                    ],
                    'Value': 1 if success else 0,
                    'Unit': 'Count'
                }
            ]
        )

# Usage in agent code
def process_change(change_data):
    with track_agent_performance('change-analyzer', 'process_change'):
        # Agent processing logic
        return analyze_change(change_data)
```

## Backup & Recovery

### Automated Backup Configuration
```yaml
# config/backup.yaml
backup_configuration:
  documents_table:
    continuous_backup: true
    point_in_time_recovery: true
    backup_retention: 35  # days
    
  document_bucket:
    versioning: true
    cross_region_replication:
      destination_bucket: "kinexus-documents-backup-us-west-2"
      storage_class: "STANDARD_IA"
      
  search_domain:
    automated_snapshots: true
    snapshot_retention: 14  # days
    snapshot_schedule: "0 2 * * *"  # Daily at 2 AM
```

### Disaster Recovery Script
```bash
#!/bin/bash
# scripts/disaster_recovery.sh

set -e

BACKUP_REGION="us-west-2"
PRIMARY_REGION="us-east-1"
ENVIRONMENT="production"

echo "🚨 Starting disaster recovery procedure..."

# 1. Assess damage and determine recovery strategy
echo "📊 Assessing system state..."
./scripts/health_check.sh --region $PRIMARY_REGION

# 2. Switch to backup region if primary is down
if [ $? -ne 0 ]; then
    echo "⚠️ Primary region unhealthy, switching to backup..."
    
    # Update Route 53 to point to backup region
    aws route53 change-resource-record-sets \
        --hosted-zone-id Z123456789 \
        --change-batch file://scripts/failover-dns.json
    
    # Scale up backup region infrastructure
    aws application-autoscaling register-scalable-target \
        --service-namespace lambda \
        --resource-id function:KinexusAI-DocumentOrchestrator-Backup \
        --scalable-dimension lambda:function:provisioned-concurrency \
        --min-capacity 10 \
        --max-capacity 100 \
        --region $BACKUP_REGION
fi

# 3. Restore data from backups if needed
echo "💾 Checking data integrity..."
./scripts/validate_data_integrity.sh

# 4. Verify system functionality
echo "✅ Running smoke tests..."
./scripts/smoke_tests.sh --region $BACKUP_REGION

echo "🎉 Disaster recovery complete!"
```

## Troubleshooting

### Common Issues

#### Agent Function Timeouts
```bash
# Check function logs
aws logs tail /aws/lambda/KinexusAI-DocumentOrchestrator --follow

# Increase timeout if needed
aws lambda update-function-configuration \
    --function-name KinexusAI-DocumentOrchestrator \
    --timeout 900  # 15 minutes
```

#### DynamoDB Throttling
```bash
# Check table metrics
aws dynamodb describe-table \
    --table-name kinexus-documents-prod \
    --query 'Table.ProvisionedThroughput'

# Enable auto-scaling if not already enabled
aws application-autoscaling register-scalable-target \
    --service-namespace dynamodb \
    --resource-id table/kinexus-documents-prod \
    --scalable-dimension dynamodb:table:ReadCapacityUnits \
    --min-capacity 5 \
    --max-capacity 1000
```

#### Bedrock Model Access Issues
```bash
# Check model access
aws bedrock list-foundation-models \
    --query 'modelSummaries[?contains(modelId, `claude-4`)]'

# Request model access if needed
echo "Request access via AWS Bedrock console for production use"
```

### Debug Commands
```bash
# Check all service health
./scripts/health_check.sh --verbose

# Validate configuration
./scripts/validate_config.sh --environment production

# Test external integrations
./scripts/test_integrations.sh --integration all

# Monitor real-time logs
./scripts/tail_logs.sh --agent all --level ERROR

# Performance analysis
./scripts/performance_report.sh --period 24h
```

### Emergency Procedures
```bash
# Emergency stop all agents
./scripts/emergency_stop.sh

# Scale down to minimal resources
./scripts/scale_down.sh --environment production

# Enable maintenance mode
./scripts/maintenance_mode.sh --enable

# Rollback to previous version
./scripts/rollback.sh --version previous --confirm
```

This deployment guide provides everything needed to successfully deploy and operate Kinexus AI in production environments, with comprehensive monitoring, backup, and recovery procedures to ensure reliable operation.