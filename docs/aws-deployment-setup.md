# AWS Deployment Setup Guide

This guide provides step-by-step instructions for setting up AWS permissions and deploying Kinexus AI to Amazon Web Services.

## 🎯 Overview

Kinexus AI requires specific AWS permissions and resources to operate. This guide covers:

1. **Prerequisites** - Required tools and access
2. **Automated Setup** - One-command permission setup
3. **Manual Setup** - Step-by-step instructions
4. **Resource Details** - IAM roles, policies, and permissions
5. **Deployment** - Deploying the application
6. **Troubleshooting** - Common issues and solutions

---

## 📋 Prerequisites

### Required Tools
```bash
# AWS CLI v2 (latest)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# jq for JSON processing
sudo apt-get install jq  # Ubuntu/Debian
brew install jq          # macOS
```

### AWS Account Requirements
- **Admin access** to AWS account (or sufficient IAM permissions)
- **AWS CLI configured** with administrator credentials
- **Account verification** and billing setup completed

### Initial AWS Configuration
```bash
# Configure AWS CLI with admin credentials
aws configure

# Test access
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDACKCEVSQ6C2EXAMPLE",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-admin-user"
# }
```

---

## 🚀 Automated Setup (Recommended)

### One-Command Setup
```bash
# Run the automated setup script
./scripts/aws-setup-permissions.sh

# With custom region
./scripts/aws-setup-permissions.sh --region us-west-2

# With specific account ID
./scripts/aws-setup-permissions.sh --account-id 123456789012 --region us-east-1
```

### What the Script Creates

#### 👤 **IAM User**
- **Name**: `kinexus-ai-deployer`
- **Purpose**: Dedicated deployment user with minimal required permissions
- **Access**: Programmatic access only (no console)

#### 📜 **IAM Policy**
- **Name**: `KinexusAI-Deployment-Policy`
- **Scope**: Comprehensive permissions for all Kinexus AI services
- **Principle**: Least privilege with resource-specific restrictions

#### 🔧 **Execution Roles**
1. **Lambda Role**: `KinexusAI-Lambda-Execution-Role`
   - For serverless function execution
   - Includes basic Lambda execution permissions

2. **ECS Role**: `KinexusAI-ECS-Task-Execution-Role`
   - For container task execution
   - Includes ECS task execution permissions

#### 🔑 **Access Keys**
- Programmatic access credentials for deployment user
- Securely generated and displayed once

---

## 📖 Manual Setup (Alternative)

If you prefer manual setup or need to understand each step:

### Step 1: Create IAM Deployment User

```bash
# Create the deployment user
aws iam create-user \
  --user-name kinexus-ai-deployer \
  --path "/" \
  --tags Key=Project,Value=KinexusAI Key=Purpose,Value=Deployment

# Verify user creation
aws iam get-user --user-name kinexus-ai-deployer
```

### Step 2: Create Deployment Policy

Create a file `kinexus-deployment-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3DocumentStorage",
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:PutBucketVersioning",
                "s3:GetBucketEncryption",
                "s3:PutBucketEncryption",
                "s3:GetBucketPublicAccessBlock",
                "s3:PutBucketPublicAccessBlock",
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::kinexus-*",
                "arn:aws:s3:::kinexus-*/*"
            ]
        },
        {
            "Sid": "DynamoDBDataPersistence",
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "dynamodb:DescribeTable",
                "dynamodb:UpdateTable",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:ACCOUNT_ID:table/kinexus-*",
                "arn:aws:dynamodb:*:ACCOUNT_ID:table/kinexus-*/index/*"
            ]
        }
        /* ... Additional permissions (see full policy in script) ... */
    ]
}
```

Apply the policy:
```bash
# Create the policy
aws iam create-policy \
  --policy-name KinexusAI-Deployment-Policy \
  --policy-document file://kinexus-deployment-policy.json \
  --description "Comprehensive deployment policy for Kinexus AI"

# Attach to user
aws iam attach-user-policy \
  --user-name kinexus-ai-deployer \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/KinexusAI-Deployment-Policy
```

### Step 3: Create Execution Roles

**Lambda Execution Role:**
```bash
# Create trust policy
cat > lambda-trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create role
aws iam create-role \
  --role-name KinexusAI-Lambda-Execution-Role \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --description "Lambda execution role for Kinexus AI"

# Attach policies
aws iam attach-role-policy \
  --role-name KinexusAI-Lambda-Execution-Role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name KinexusAI-Lambda-Execution-Role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/KinexusAI-Deployment-Policy
```

**ECS Execution Role:**
```bash
# Create trust policy
cat > ecs-trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "ecs-tasks.amazonaws.com",
                    "ecs.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create role
aws iam create-role \
  --role-name KinexusAI-ECS-Task-Execution-Role \
  --assume-role-policy-document file://ecs-trust-policy.json \
  --description "ECS task execution role for Kinexus AI"

# Attach policies
aws iam attach-role-policy \
  --role-name KinexusAI-ECS-Task-Execution-Role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam attach-role-policy \
  --role-name KinexusAI-ECS-Task-Execution-Role \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/KinexusAI-Deployment-Policy
```

### Step 4: Generate Access Keys

```bash
# Generate access keys for deployment user
aws iam create-access-key --user-name kinexus-ai-deployer

# Save the output securely - it's only shown once!
```

---

## 🔐 Resource Details

### IAM User: kinexus-ai-deployer

**Purpose**: Dedicated service account for Kinexus AI deployment operations

**Permissions**: Only the minimum required for deployment and operation

**Access Type**: Programmatic only (no AWS Console access)

**Tags**:
- `Project`: KinexusAI
- `Purpose`: Deployment

### IAM Policy: KinexusAI-Deployment-Policy

**Comprehensive AWS service permissions for:**

#### Core Infrastructure
- **S3**: Document storage buckets (`kinexus-*`)
- **DynamoDB**: Data persistence tables (`kinexus-*`)
- **Lambda**: Serverless function deployment (`kinexus-*`)
- **API Gateway**: REST API endpoint management

#### Container Services
- **ECS**: Container orchestration (`kinexus-*` clusters)
- **ECR**: Container image registry (`kinexus-*` repositories)

#### AI & Analytics
- **Bedrock**: AI model access (all foundation models)
- **EventBridge**: Event orchestration (`kinexus-*` rules)

#### Data Services
- **RDS**: PostgreSQL database instances (`kinexus-*`)
- **ElastiCache**: Redis caching clusters (`kinexus-*`)

#### Security & Identity
- **Cognito**: User authentication pools
- **Secrets Manager**: Credential storage (`kinexus-*`)

#### Monitoring & Logging
- **CloudWatch**: Metrics and log management
- **Route 53**: DNS management
- **Certificate Manager**: SSL/TLS certificates

#### Networking
- **VPC**: Virtual Private Cloud resources
- **EC2**: Security groups, subnets, gateways

### Execution Roles

#### KinexusAI-Lambda-Execution-Role
**Purpose**: Allows Lambda functions to execute and access AWS services

**Trust Policy**: lambda.amazonaws.com

**Attached Policies**:
- `AWSLambdaBasicExecutionRole` (AWS managed)
- `KinexusAI-Deployment-Policy` (custom)

#### KinexusAI-ECS-Task-Execution-Role
**Purpose**: Allows ECS tasks to pull images and write logs

**Trust Policy**: ecs-tasks.amazonaws.com, ecs.amazonaws.com

**Attached Policies**:
- `AmazonECSTaskExecutionRolePolicy` (AWS managed)
- `KinexusAI-Deployment-Policy` (custom)

---

## 🚀 Deployment Process

### Environment Configuration

```bash
# Set deployment credentials (replace with your actual values)
export AWS_ACCESS_KEY_ID="AKIA****************"
export AWS_SECRET_ACCESS_KEY="********************************"
export AWS_DEFAULT_REGION="us-east-1"

# Verify credentials
aws sts get-caller-identity
```

### Deploy to AWS

```bash
# Production deployment
./quick-start.sh prod

# Deploy to AWS infrastructure
./scripts/deploy-aws.sh

# Monitor deployment
aws cloudformation describe-stacks --stack-name kinexus-ai
```

---

## 🔧 Post-Deployment Configuration

### Domain and SSL Setup

```bash
# Create hosted zone (if using custom domain)
aws route53 create-hosted-zone \
  --name kinexusai.com \
  --caller-reference $(date +%s)

# Request SSL certificate
aws acm request-certificate \
  --domain-name kinexusai.com \
  --subject-alternative-names *.kinexusai.com \
  --validation-method DNS
```

### Secrets Configuration

```bash
# Store integration credentials
aws secretsmanager create-secret \
  --name kinexus-confluence-credentials \
  --description "Confluence integration credentials" \
  --secret-string '{"username":"user@company.com","api_token":"token_here"}'

aws secretsmanager create-secret \
  --name kinexus-jira-credentials \
  --description "Jira integration credentials" \
  --secret-string '{"username":"user@company.com","api_token":"token_here"}'
```

### Monitoring Setup

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name KinexusAI-Operations \
  --dashboard-body file://monitoring/cloudwatch-dashboard.json

# Set up alarms
aws cloudwatch put-metric-alarm \
  --alarm-name kinexus-api-errors \
  --alarm-description "API error rate alarm" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Permission Denied Errors
```bash
# Check user permissions
aws iam list-attached-user-policies --user-name kinexus-ai-deployer

# Verify policy is attached
aws iam get-policy --policy-arn arn:aws:iam::ACCOUNT_ID:policy/KinexusAI-Deployment-Policy
```

#### 2. Role Assumption Failures
```bash
# Test role assumption
aws sts assume-role \
  --role-arn arn:aws:iam::ACCOUNT_ID:role/KinexusAI-Lambda-Execution-Role \
  --role-session-name test-session

# Check trust relationships
aws iam get-role --role-name KinexusAI-Lambda-Execution-Role
```

#### 3. Resource Creation Failures
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name kinexus-ai

# View specific resource status
aws cloudformation describe-stack-resources --stack-name kinexus-ai
```

#### 4. Access Key Issues
```bash
# List existing access keys
aws iam list-access-keys --user-name kinexus-ai-deployer

# Rotate access keys if needed
aws iam create-access-key --user-name kinexus-ai-deployer
aws iam delete-access-key --user-name kinexus-ai-deployer --access-key-id OLD_KEY_ID
```

### Validation Commands

```bash
# Test S3 access
aws s3 ls

# Test DynamoDB access
aws dynamodb list-tables

# Test Lambda access
aws lambda list-functions

# Test ECS access
aws ecs list-clusters

# Test Bedrock access
aws bedrock list-foundation-models
```

### Debug Mode

```bash
# Enable AWS CLI debug output
export AWS_CLI_DEBUG=1

# Run deployment with verbose output
./scripts/deploy-aws.sh --verbose
```

---

## 📊 Cost Optimization

### Resource Sizing Recommendations

#### Development Environment
- **Lambda**: 512MB memory, 30s timeout
- **RDS**: db.t3.micro (PostgreSQL)
- **ElastiCache**: cache.t3.micro (Redis)
- **ECS**: 1 vCPU, 2GB memory

#### Production Environment
- **Lambda**: 1024MB memory, 5min timeout
- **RDS**: db.t3.small with Multi-AZ
- **ElastiCache**: cache.t3.small with clustering
- **ECS**: 2 vCPU, 4GB memory with auto-scaling

### Cost Monitoring

```bash
# Set up billing alarms
aws cloudwatch put-metric-alarm \
  --alarm-name kinexus-billing-alert \
  --alarm-description "Monthly billing alert" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

---

## 🔄 Maintenance

### Regular Tasks

#### Weekly
- Review CloudWatch logs and metrics
- Check integration sync status
- Monitor API response times

#### Monthly
- Rotate access keys
- Review and optimize resource usage
- Update dependencies and security patches

#### Quarterly
- Review IAM permissions and policies
- Conduct security audit
- Performance optimization review

### Backup Strategy

```bash
# Automated DynamoDB backups
aws dynamodb put-backup-policy \
  --table-name kinexus-documents \
  --backup-policy BackupEnabled=true

# S3 cross-region replication
aws s3api put-bucket-replication \
  --bucket kinexus-documents \
  --replication-configuration file://s3-replication-config.json
```

---

## 📚 Additional Resources

### Documentation
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Lambda Security](https://docs.aws.amazon.com/lambda/latest/dg/lambda-security.html)
- [ECS Security Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security.html)

### Kinexus AI Specific
- [Integration Configuration Guide](integration-configuration.md)
- [Deployment Guide](deployment.md)
- [Monitoring Guide](monitoring.md)

### Support
- **Technical Issues**: Create GitHub issue
- **AWS-Specific Questions**: AWS Support or community forums
- **Security Concerns**: Follow responsible disclosure process

---

This comprehensive setup ensures secure, scalable deployment of Kinexus AI on AWS with proper permissions and resource isolation.