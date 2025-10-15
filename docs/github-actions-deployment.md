# GitHub Actions AWS Deployment Guide

Complete guide for setting up automated AWS deployment using GitHub Actions for Kinexus AI.

## Overview

The `.github/workflows/dev.yaml` workflow provides automated deployment to AWS with the following features:

- **Automated Testing**: Runs full test suite before deployment
- **Multi-Environment Support**: Deploy to development, staging, or production
- **Dual Deployment Types**:
  - **MVP**: Serverless using Lambda, API Gateway, DynamoDB (fast, cost-effective)
  - **Production**: ECS Fargate, RDS, ElastiCache, ALB (scalable, enterprise-grade)
- **Docker Build & Push**: Automated container builds to ECR
- **CDK Infrastructure**: Infrastructure-as-code deployment
- **Health Checks**: Post-deployment validation
- **PR Previews**: Deploy preview environments for pull requests

## Workflow Triggers

### Automatic Deployments

- **Push to `main`** → Production environment (production stack)
- **Push to `develop`** → Development environment (MVP stack)
- **Push to `release/*`** → Staging environment (production stack)
- **Pull Request to `main`** → Preview environment (build only, validate)

### Manual Deployments

Use the "Run workflow" button in GitHub Actions to deploy manually:

1. Go to Actions → Deploy to AWS
2. Click "Run workflow"
3. Select:
   - Environment (development/staging/production)
   - Deployment type (mvp/production)
   - Whether to skip tests

## Prerequisites

### 1. AWS Account Setup

Run the permissions setup script to create necessary IAM resources:

```bash
./scripts/aws-setup-permissions.sh
```

This creates:
- IAM user: `kinexus-ai-deployer`
- Deployment policy with necessary permissions
- Lambda execution role
- ECS execution role

### 2. GitHub OIDC Provider (Recommended)

For secure, keyless authentication using OIDC:

```bash
# Create OIDC provider in AWS
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create IAM role for GitHub Actions
aws iam create-role \
  --role-name GitHubActionsDeploymentRole \
  --assume-role-policy-document file://github-actions-trust-policy.json

# Attach deployment policy
aws iam attach-role-policy \
  --role-name GitHubActionsDeploymentRole \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/KinexusAI-Deployment-Policy
```

**github-actions-trust-policy.json**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/kinexus-ai:*"
        }
      }
    }
  ]
}
```

### 3. Create ECR Repositories

For production deployments, create ECR repositories for each service:

```bash
# Array of service names
services=(
  "kinexus-ai-api"
  "kinexus-ai-orchestrator"
  "kinexus-ai-change-analyzer"
  "kinexus-ai-content-creator"
  "kinexus-ai-quality-controller"
  "kinexus-ai-web-automator"
)

# Create repositories
for service in "${services[@]}"; do
  aws ecr create-repository \
    --repository-name "$service" \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    --region us-east-1
done
```

## GitHub Secrets Configuration

Configure the following secrets in your GitHub repository:

### Go to: Settings → Secrets and variables → Actions → New repository secret

### Required Secrets

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ROLE_ARN` | ARN of the IAM role for OIDC | `arn:aws:iam::123456789012:role/GitHubActionsDeploymentRole` |
| `AWS_ACCOUNT_ID` | Your AWS account ID | `123456789012` |

### Optional Secrets (if not using OIDC)

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID | `AKIA****************` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `********************************` |

### Setting Secrets via CLI

```bash
# Using GitHub CLI
gh secret set AWS_ROLE_ARN --body "arn:aws:iam::123456789012:role/GitHubActionsDeploymentRole"
gh secret set AWS_ACCOUNT_ID --body "123456789012"
```

## Environment Configuration

Configure environment-specific settings in GitHub:

### Go to: Settings → Environments

Create three environments:

### 1. Development Environment

- **Name**: `development`
- **Protection rules**: None (auto-deploy)
- **Secrets**: None needed (uses repository secrets)

### 2. Staging Environment

- **Name**: `staging`
- **Protection rules**:
  - ✅ Required reviewers: 1
  - ✅ Wait timer: 0 minutes
- **Secrets**: None needed (uses repository secrets)

### 3. Production Environment

- **Name**: `production`
- **Protection rules**:
  - ✅ Required reviewers: 2
  - ✅ Wait timer: 5 minutes
  - ✅ Deployment branches: `main` only
- **Secrets**:
  - Can override with production-specific credentials if needed

## Workflow Jobs

### 1. Configure

Determines deployment configuration based on branch/trigger:

- **main** → production environment
- **develop** → development environment
- **release/*** → staging environment
- **PR** → validation only (no deployment)

### 2. Test

Runs comprehensive test suite:

- Code linting (black, isort, ruff)
- Type checking (mypy)
- Security scanning (bandit)
- Unit & integration tests (pytest with coverage)
- Uploads coverage to Codecov

### 3. Build

Two different build paths:

#### Production Deployment (ECS):
- Builds 6 Docker images for microservices
- Pushes to Amazon ECR
- Uses multi-stage builds for optimization
- Implements layer caching for faster builds

#### MVP Deployment (Lambda):
- Builds Lambda layer with dependencies
- Creates `lambda_layer.zip` artifact
- Uses `scripts/build-layer.sh`

### 4. Deploy

Deploys infrastructure using AWS CDK:

1. **CDK Bootstrap**: Ensures CDK is set up in region
2. **CDK Synth**: Generates CloudFormation templates
3. **CDK Deploy**: Deploys infrastructure
4. **Health Check**: Validates deployment
5. **Outputs**: Saves deployment outputs as artifacts

### 5. Validate

Post-deployment validation:

- Runs smoke tests against deployed environment
- Validates health endpoints
- Checks service availability

### 6. Comment PR

For pull requests:
- Comments deployment details
- Shows CloudFormation outputs
- Provides quick links to resources

## Deployment Types

### MVP Deployment (Serverless)

**Use When:**
- Quick demos and prototypes
- Development and testing
- Cost-sensitive environments
- Low to medium traffic

**Stack Includes:**
- AWS Lambda functions
- API Gateway
- DynamoDB tables
- S3 buckets
- EventBridge
- CloudWatch Logs

**Cost:** ~$20-50/month

### Production Deployment (Containerized)

**Use When:**
- Production workloads
- High availability required
- Scalable infrastructure needed
- Enterprise requirements

**Stack Includes:**
- ECS Fargate cluster (2-10 tasks)
- Application Load Balancer
- RDS PostgreSQL (Multi-AZ)
- ElastiCache Redis
- Cognito User Pool
- CloudWatch monitoring & alarms
- Automated backups
- Auto-scaling

**Cost:** ~$300-800/month (scales with usage)

## Triggering Deployments

### Automatic Deployment

```bash
# Deploy to development
git checkout develop
git commit -am "feat: new feature"
git push origin develop

# Deploy to production
git checkout main
git merge develop
git push origin main
```

### Manual Deployment

1. Go to GitHub Actions
2. Select "Deploy to AWS" workflow
3. Click "Run workflow"
4. Select options:
   - Environment: `production`
   - Deployment type: `production`
   - Skip tests: `false`
5. Click "Run workflow"

## Monitoring Deployments

### GitHub Actions UI

View deployment progress:
1. Go to Actions tab
2. Click on the running workflow
3. Monitor each job's progress

### AWS Console

Monitor AWS resources:

- **CloudFormation**: View stack status and events
- **ECS**: Monitor service health and task count
- **CloudWatch**: View logs and metrics
- **RDS**: Check database performance
- **ECR**: View pushed container images

### Deployment Outputs

After successful deployment, outputs are available:

```bash
# Download outputs artifact from GitHub Actions
# Or view in CDK deployment logs

Example outputs:
- API Endpoint: https://xxx.execute-api.us-east-1.amazonaws.com/prod/
- Load Balancer DNS: kinexus-alb-xxx.us-east-1.elb.amazonaws.com
- Database Endpoint: kinexus-db.xxx.us-east-1.rds.amazonaws.com
- Webhook URLs: https://xxx/webhooks/github
```

## Troubleshooting

### Deployment Failures

**Build Failures:**
```bash
# Check build logs in GitHub Actions
# Common issues:
# - Poetry dependency conflicts
# - Docker layer cache issues
# - ECR authentication problems

# Solutions:
# - Clear GitHub Actions cache
# - Rebuild Docker images locally
# - Verify AWS credentials
```

**CDK Deployment Failures:**
```bash
# View CloudFormation events in AWS Console
# Common issues:
# - Resource limits exceeded
# - Insufficient permissions
# - Resource name conflicts

# Solutions:
# - Check AWS service quotas
# - Verify IAM permissions
# - Destroy conflicting stacks
```

**Health Check Failures:**
```bash
# Check application logs
aws logs tail /ecs/kinexus-api --follow

# Verify security groups allow traffic
# Check database connectivity
# Verify environment variables
```

### Rollback Failed Deployment

**For MVP (Lambda):**
```bash
# Rollback to previous version via AWS Console
# Or redeploy previous commit
git revert HEAD
git push origin develop
```

**For Production (ECS):**
```bash
# ECS auto-rollback is enabled via circuit breaker
# Or manually update service to previous task definition

aws ecs update-service \
  --cluster kinexus-production \
  --service api-service \
  --task-definition kinexus-api:PREVIOUS_VERSION
```

### Common Errors

**Error: "No ECR repository found"**
```bash
# Create ECR repositories
./scripts/create-ecr-repos.sh
```

**Error: "Insufficient permissions"**
```bash
# Verify IAM role has deployment policy attached
aws iam list-attached-role-policies \
  --role-name GitHubActionsDeploymentRole
```

**Error: "Stack already exists"**
```bash
# Either destroy existing stack or use update
cdk deploy --force
```

## Security Best Practices

### 1. Use OIDC Instead of Access Keys

✅ **Recommended**: OIDC with IAM roles (no long-lived credentials)
❌ **Avoid**: Access keys in GitHub secrets

### 2. Least Privilege Permissions

- Only grant necessary permissions
- Use resource-specific policies
- Enable MFA for production changes

### 3. Secrets Management

- Never commit secrets to repository
- Use AWS Secrets Manager for application secrets
- Rotate credentials regularly

### 4. Branch Protection

- Require reviews for production deployments
- Require status checks to pass
- Require branches to be up to date

### 5. Environment Isolation

- Use separate AWS accounts for prod/non-prod
- Tag resources by environment
- Implement cost allocation tags

## Cost Optimization

### Development Environment

- Use MVP deployment (serverless)
- Enable auto-shutdown for non-working hours
- Use smaller instance types

### Production Environment

- Use Reserved Instances for predictable workload
- Enable auto-scaling
- Implement lifecycle policies for logs and backups
- Monitor and right-size resources

## Next Steps

1. **Set up AWS infrastructure**:
   ```bash
   ./scripts/aws-setup-permissions.sh
   ```

2. **Configure GitHub secrets**:
   ```bash
   gh secret set AWS_ROLE_ARN --body "arn:aws:iam::123456789012:role/GitHubActionsDeploymentRole"
   gh secret set AWS_ACCOUNT_ID --body "123456789012"
   ```

3. **Create ECR repositories** (for production deployments)

4. **Test workflow**:
   - Create a PR to trigger validation
   - Merge to `develop` for development deployment
   - Merge to `main` for production deployment

5. **Monitor deployment**:
   - Check GitHub Actions for workflow status
   - Verify resources in AWS Console
   - Run health checks

## Support

For issues or questions:

- **GitHub Issues**: [kinexus-ai/issues](https://github.com/jaredgiosinuff/kinexus-ai/issues)
- **Documentation**: [docs/](../docs/)
- **AWS Deployment Setup**: [docs/aws-deployment-setup.md](./aws-deployment-setup.md)

---

**Related Documentation:**
- [AWS Deployment Setup Guide](./aws-deployment-setup.md)
- [Development Guide](./development.md)
- [Deployment Guide](./deployment.md)
- [Architecture Overview](./architecture.md)
