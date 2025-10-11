#!/bin/bash

# Kinexus AI - AWS Permissions Setup Script
# This script creates all necessary IAM users, roles, and policies for deploying Kinexus AI
#
# Prerequisites:
# - AWS CLI installed and configured with admin permissions
# - jq installed for JSON processing
#
# Usage:
#   ./scripts/aws-setup-permissions.sh [--region us-east-1] [--account-id 123456789012]

set -e

# Configuration
DEFAULT_REGION="us-east-1"
REGION="${1:-$DEFAULT_REGION}"
ACCOUNT_ID="${2:-$(aws sts get-caller-identity --query Account --output text)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it first."
        exit 1
    fi

    # Test AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Create trust policy documents
create_trust_policies() {
    log_info "Creating trust policy documents..."

    # Lambda trust policy
    cat > /tmp/kinexus-lambda-trust-policy.json << 'EOF'
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

    # ECS trust policy
    cat > /tmp/kinexus-ecs-trust-policy.json << 'EOF'
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

    # API Gateway trust policy
    cat > /tmp/kinexus-apigateway-trust-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "apigateway.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    log_success "Trust policy documents created"
}

# Create comprehensive deployment policy
create_deployment_policy() {
    log_info "Creating comprehensive deployment policy..."

    cat > /tmp/kinexus-deployment-policy.json << EOF
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
                "dynamodb:BatchWriteItem",
                "dynamodb:DescribeStream",
                "dynamodb:GetRecords",
                "dynamodb:GetShardIterator",
                "dynamodb:ListStreams"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:${ACCOUNT_ID}:table/kinexus-*",
                "arn:aws:dynamodb:*:${ACCOUNT_ID}:table/kinexus-*/stream/*",
                "arn:aws:dynamodb:*:${ACCOUNT_ID}:table/kinexus-*/index/*"
            ]
        },
        {
            "Sid": "LambdaServerlessFunctions",
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:DeleteFunction",
                "lambda:GetFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:InvokeFunction",
                "lambda:ListFunctions",
                "lambda:TagResource",
                "lambda:UntagResource",
                "lambda:CreateEventSourceMapping",
                "lambda:DeleteEventSourceMapping",
                "lambda:GetEventSourceMapping",
                "lambda:ListEventSourceMappings"
            ],
            "Resource": [
                "arn:aws:lambda:*:${ACCOUNT_ID}:function:kinexus-*",
                "arn:aws:lambda:*:${ACCOUNT_ID}:event-source-mapping:*"
            ]
        },
        {
            "Sid": "APIGatewayEndpoints",
            "Effect": "Allow",
            "Action": [
                "apigateway:*"
            ],
            "Resource": [
                "arn:aws:apigateway:*::/restapis/*",
                "arn:aws:apigateway:*::/apis/*"
            ]
        },
        {
            "Sid": "EventBridgeOrchestration",
            "Effect": "Allow",
            "Action": [
                "events:CreateRule",
                "events:DeleteRule",
                "events:DescribeRule",
                "events:PutRule",
                "events:PutTargets",
                "events:RemoveTargets",
                "events:ListTargetsByRule",
                "events:PutEvents"
            ],
            "Resource": [
                "arn:aws:events:*:${ACCOUNT_ID}:rule/kinexus-*",
                "arn:aws:events:*:${ACCOUNT_ID}:event-bus/kinexus-*"
            ]
        },
        {
            "Sid": "BedrockAIModels",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:GetFoundationModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECSContainerDeployment",
            "Effect": "Allow",
            "Action": [
                "ecs:CreateCluster",
                "ecs:DeleteCluster",
                "ecs:DescribeClusters",
                "ecs:CreateService",
                "ecs:DeleteService",
                "ecs:DescribeServices",
                "ecs:UpdateService",
                "ecs:RegisterTaskDefinition",
                "ecs:DeregisterTaskDefinition",
                "ecs:DescribeTaskDefinition",
                "ecs:RunTask",
                "ecs:StopTask",
                "ecs:DescribeTasks",
                "ecs:ListTasks"
            ],
            "Resource": [
                "arn:aws:ecs:*:${ACCOUNT_ID}:cluster/kinexus-*",
                "arn:aws:ecs:*:${ACCOUNT_ID}:service/kinexus-*/*",
                "arn:aws:ecs:*:${ACCOUNT_ID}:task-definition/kinexus-*:*",
                "arn:aws:ecs:*:${ACCOUNT_ID}:task/kinexus-*/*"
            ]
        },
        {
            "Sid": "ECRContainerRegistry",
            "Effect": "Allow",
            "Action": [
                "ecr:CreateRepository",
                "ecr:DeleteRepository",
                "ecr:DescribeRepositories",
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": [
                "arn:aws:ecr:*:${ACCOUNT_ID}:repository/kinexus-*",
                "*"
            ]
        },
        {
            "Sid": "RDSPostgreSQL",
            "Effect": "Allow",
            "Action": [
                "rds:CreateDBInstance",
                "rds:DeleteDBInstance",
                "rds:DescribeDBInstances",
                "rds:ModifyDBInstance",
                "rds:CreateDBSubnetGroup",
                "rds:DeleteDBSubnetGroup",
                "rds:DescribeDBSubnetGroups",
                "rds:CreateDBParameterGroup",
                "rds:DeleteDBParameterGroup",
                "rds:DescribeDBParameterGroups"
            ],
            "Resource": [
                "arn:aws:rds:*:${ACCOUNT_ID}:db:kinexus-*",
                "arn:aws:rds:*:${ACCOUNT_ID}:subnet-group:kinexus-*",
                "arn:aws:rds:*:${ACCOUNT_ID}:pg:kinexus-*"
            ]
        },
        {
            "Sid": "ElastiCacheRedis",
            "Effect": "Allow",
            "Action": [
                "elasticache:CreateCacheCluster",
                "elasticache:DeleteCacheCluster",
                "elasticache:DescribeCacheClusters",
                "elasticache:ModifyCacheCluster",
                "elasticache:CreateCacheSubnetGroup",
                "elasticache:DeleteCacheSubnetGroup",
                "elasticache:DescribeCacheSubnetGroups"
            ],
            "Resource": [
                "arn:aws:elasticache:*:${ACCOUNT_ID}:cluster:kinexus-*",
                "arn:aws:elasticache:*:${ACCOUNT_ID}:subnetgroup:kinexus-*"
            ]
        },
        {
            "Sid": "CognitoAuthentication",
            "Effect": "Allow",
            "Action": [
                "cognito-idp:CreateUserPool",
                "cognito-idp:DeleteUserPool",
                "cognito-idp:DescribeUserPool",
                "cognito-idp:UpdateUserPool",
                "cognito-idp:CreateUserPoolClient",
                "cognito-idp:DeleteUserPoolClient",
                "cognito-idp:DescribeUserPoolClient",
                "cognito-idp:UpdateUserPoolClient",
                "cognito-identity:CreateIdentityPool",
                "cognito-identity:DeleteIdentityPool",
                "cognito-identity:DescribeIdentityPool",
                "cognito-identity:UpdateIdentityPool"
            ],
            "Resource": [
                "arn:aws:cognito-idp:*:${ACCOUNT_ID}:userpool/*",
                "arn:aws:cognito-identity:*:${ACCOUNT_ID}:identitypool/*"
            ]
        },
        {
            "Sid": "SecretsManagerCredentials",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:CreateSecret",
                "secretsmanager:DeleteSecret",
                "secretsmanager:DescribeSecret",
                "secretsmanager:GetSecretValue",
                "secretsmanager:PutSecretValue",
                "secretsmanager:UpdateSecret",
                "secretsmanager:RotateSecret"
            ],
            "Resource": [
                "arn:aws:secretsmanager:*:${ACCOUNT_ID}:secret:kinexus-*"
            ]
        },
        {
            "Sid": "CloudWatchMonitoring",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData",
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams"
            ],
            "Resource": [
                "arn:aws:cloudwatch:*:${ACCOUNT_ID}:metric/Kinexus/*",
                "arn:aws:logs:*:${ACCOUNT_ID}:log-group:/aws/lambda/kinexus-*",
                "arn:aws:logs:*:${ACCOUNT_ID}:log-group:/ecs/kinexus-*"
            ]
        },
        {
            "Sid": "VPCNetworking",
            "Effect": "Allow",
            "Action": [
                "ec2:CreateVpc",
                "ec2:DeleteVpc",
                "ec2:DescribeVpcs",
                "ec2:CreateSubnet",
                "ec2:DeleteSubnet",
                "ec2:DescribeSubnets",
                "ec2:CreateSecurityGroup",
                "ec2:DeleteSecurityGroup",
                "ec2:DescribeSecurityGroups",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:AuthorizeSecurityGroupEgress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupEgress",
                "ec2:CreateInternetGateway",
                "ec2:DeleteInternetGateway",
                "ec2:AttachInternetGateway",
                "ec2:DetachInternetGateway",
                "ec2:DescribeInternetGateways",
                "ec2:CreateRouteTable",
                "ec2:DeleteRouteTable",
                "ec2:DescribeRouteTables",
                "ec2:CreateRoute",
                "ec2:DeleteRoute",
                "ec2:AssociateRouteTable",
                "ec2:DisassociateRouteTable"
            ],
            "Resource": "*"
        },
        {
            "Sid": "Route53DNS",
            "Effect": "Allow",
            "Action": [
                "route53:CreateHostedZone",
                "route53:DeleteHostedZone",
                "route53:GetHostedZone",
                "route53:ListHostedZones",
                "route53:ChangeResourceRecordSets",
                "route53:GetChange",
                "route53:ListResourceRecordSets"
            ],
            "Resource": [
                "arn:aws:route53:::hostedzone/*",
                "arn:aws:route53:::change/*"
            ]
        },
        {
            "Sid": "CertificateManagerSSL",
            "Effect": "Allow",
            "Action": [
                "acm:RequestCertificate",
                "acm:DeleteCertificate",
                "acm:DescribeCertificate",
                "acm:ListCertificates",
                "acm:GetCertificate"
            ],
            "Resource": [
                "arn:aws:acm:*:${ACCOUNT_ID}:certificate/*"
            ]
        },
        {
            "Sid": "IAMRoleManagement",
            "Effect": "Allow",
            "Action": [
                "iam:PassRole",
                "iam:GetRole",
                "iam:ListRoles"
            ],
            "Resource": [
                "arn:aws:iam::${ACCOUNT_ID}:role/KinexusAI-*"
            ]
        }
    ]
}
EOF

    log_success "Deployment policy document created"
}

# Create IAM deployment user
create_deployment_user() {
    log_info "Creating deployment user..."

    local user_name="kinexus-ai-deployer"

    # Check if user already exists
    if aws iam get-user --user-name "$user_name" &> /dev/null; then
        log_warning "User $user_name already exists, skipping creation"
    else
        aws iam create-user \
            --user-name "$user_name" \
            --path "/" \
            --tags Key=Project,Value=KinexusAI Key=Purpose,Value=Deployment \
            > /tmp/kinexus-user-output.json

        log_success "Deployment user created: $user_name"
    fi
}

# Create IAM deployment policy
create_iam_deployment_policy() {
    log_info "Creating IAM deployment policy..."

    local policy_name="KinexusAI-Deployment-Policy"
    local policy_arn="arn:aws:iam::${ACCOUNT_ID}:policy/${policy_name}"

    # Check if policy already exists
    if aws iam get-policy --policy-arn "$policy_arn" &> /dev/null; then
        log_warning "Policy $policy_name already exists, updating..."
        # Get current policy version
        local version=$(aws iam get-policy --policy-arn "$policy_arn" --query 'Policy.DefaultVersionId' --output text)
        # Create new version
        aws iam create-policy-version \
            --policy-arn "$policy_arn" \
            --policy-document file:///tmp/kinexus-deployment-policy.json \
            --set-as-default > /dev/null
        log_success "Policy $policy_name updated"
    else
        aws iam create-policy \
            --policy-name "$policy_name" \
            --path "/" \
            --policy-document file:///tmp/kinexus-deployment-policy.json \
            --description "Comprehensive deployment policy for Kinexus AI platform" \
            --tags Key=Project,Value=KinexusAI Key=Purpose,Value=Deployment \
            > /tmp/kinexus-policy-output.json

        log_success "Deployment policy created: $policy_name"
    fi

    # Attach policy to user
    aws iam attach-user-policy \
        --user-name "kinexus-ai-deployer" \
        --policy-arn "$policy_arn"

    log_success "Policy attached to deployment user"
}

# Create execution roles
create_execution_roles() {
    log_info "Creating execution roles..."

    # Lambda execution role
    local lambda_role="KinexusAI-Lambda-Execution-Role"
    if aws iam get-role --role-name "$lambda_role" &> /dev/null; then
        log_warning "Lambda role $lambda_role already exists, skipping"
    else
        aws iam create-role \
            --role-name "$lambda_role" \
            --assume-role-policy-document file:///tmp/kinexus-lambda-trust-policy.json \
            --description "Lambda execution role for Kinexus AI functions" \
            --tags Key=Project,Value=KinexusAI Key=Purpose,Value=LambdaExecution \
            > /tmp/kinexus-lambda-role-output.json

        log_success "Lambda execution role created: $lambda_role"
    fi

    # Attach managed policies to Lambda role
    aws iam attach-role-policy \
        --role-name "$lambda_role" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

    aws iam attach-role-policy \
        --role-name "$lambda_role" \
        --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/KinexusAI-Deployment-Policy"

    # ECS execution role
    local ecs_role="KinexusAI-ECS-Task-Execution-Role"
    if aws iam get-role --role-name "$ecs_role" &> /dev/null; then
        log_warning "ECS role $ecs_role already exists, skipping"
    else
        aws iam create-role \
            --role-name "$ecs_role" \
            --assume-role-policy-document file:///tmp/kinexus-ecs-trust-policy.json \
            --description "ECS task execution role for Kinexus AI containers" \
            --tags Key=Project,Value=KinexusAI Key=Purpose,Value=ECSExecution \
            > /tmp/kinexus-ecs-role-output.json

        log_success "ECS execution role created: $ecs_role"
    fi

    # Attach managed policies to ECS role
    aws iam attach-role-policy \
        --role-name "$ecs_role" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

    aws iam attach-role-policy \
        --role-name "$ecs_role" \
        --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/KinexusAI-Deployment-Policy"

    log_success "Execution roles configured with policies"
}

# Generate access keys
generate_access_keys() {
    log_info "Generating access keys for deployment user..."

    local user_name="kinexus-ai-deployer"

    # Check if access keys already exist
    local existing_keys=$(aws iam list-access-keys --user-name "$user_name" --query 'AccessKeyMetadata[?Status==`Active`].AccessKeyId' --output text)

    if [ -n "$existing_keys" ]; then
        log_warning "Active access keys already exist for $user_name:"
        echo "$existing_keys"
        echo ""
        log_warning "To create new keys, first delete existing ones with:"
        echo "aws iam delete-access-key --user-name $user_name --access-key-id <KEY_ID>"
        return
    fi

    aws iam create-access-key --user-name "$user_name" > /tmp/kinexus-access-key-output.json

    local access_key_id=$(jq -r '.AccessKey.AccessKeyId' /tmp/kinexus-access-key-output.json)
    local secret_access_key=$(jq -r '.AccessKey.SecretAccessKey' /tmp/kinexus-access-key-output.json)

    log_success "Access keys generated successfully"

    # Output credentials securely
    echo ""
    echo "=================================="
    echo "🔐 KINEXUS AI DEPLOYMENT CREDENTIALS"
    echo "=================================="
    echo ""
    echo "AWS Account ID: $ACCOUNT_ID"
    echo "Region: $REGION"
    echo "User: $user_name"
    echo ""
    echo "Access Key ID: $access_key_id"
    echo "Secret Access Key: $secret_access_key"
    echo ""
    echo "🔧 Environment Variables:"
    echo "export AWS_ACCESS_KEY_ID=\"$access_key_id\""
    echo "export AWS_SECRET_ACCESS_KEY=\"$secret_access_key\""
    echo "export AWS_DEFAULT_REGION=\"$REGION\""
    echo ""
    echo "=================================="
    echo "⚠️  IMPORTANT: Save these credentials securely!"
    echo "⚠️  They will not be displayed again."
    echo "=================================="
    echo ""
}

# Output summary
output_summary() {
    echo ""
    echo "🎉 KINEXUS AI AWS SETUP COMPLETE!"
    echo ""
    echo "📋 Resources Created:"
    echo "   👤 IAM User: kinexus-ai-deployer"
    echo "   📜 IAM Policy: KinexusAI-Deployment-Policy"
    echo "   🔧 Lambda Role: KinexusAI-Lambda-Execution-Role"
    echo "   🐳 ECS Role: KinexusAI-ECS-Task-Execution-Role"
    echo ""
    echo "🔑 AWS Services Covered:"
    echo "   ☁️  S3 - Document Storage"
    echo "   🗄️  DynamoDB - Data Persistence"
    echo "   ⚡ Lambda - Serverless Functions"
    echo "   🌐 API Gateway - REST Endpoints"
    echo "   📅 EventBridge - Event Orchestration"
    echo "   🤖 Bedrock - AI Model Access"
    echo "   🐳 ECS/ECR - Container Deployment"
    echo "   🗃️  RDS - PostgreSQL Database"
    echo "   🚀 ElastiCache - Redis Caching"
    echo "   🔐 Cognito - Authentication"
    echo "   🗝️  Secrets Manager - Credential Management"
    echo "   📊 CloudWatch - Monitoring & Logging"
    echo "   🌐 VPC - Networking"
    echo "   🌍 Route 53 - DNS Management"
    echo "   🔒 Certificate Manager - SSL/TLS"
    echo ""
    echo "📚 Next Steps:"
    echo "   1. Save the credentials above securely"
    echo "   2. Set environment variables in your deployment environment"
    echo "   3. Run: ./quick-start.sh prod"
    echo "   4. Deploy to AWS using: ./scripts/deploy-aws.sh"
    echo ""
    echo "📖 Documentation: docs/deployment.md"
    echo ""
}

# Main execution
main() {
    echo "🚀 Kinexus AI - AWS Permissions Setup"
    echo "======================================"
    echo ""
    echo "Account ID: $ACCOUNT_ID"
    echo "Region: $REGION"
    echo ""

    check_prerequisites
    create_trust_policies
    create_deployment_policy
    create_deployment_user
    create_iam_deployment_policy
    create_execution_roles
    generate_access_keys
    output_summary

    # Cleanup temporary files
    rm -f /tmp/kinexus-*.json

    log_success "Setup completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        --account-id)
            ACCOUNT_ID="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--region REGION] [--account-id ACCOUNT_ID]"
            echo ""
            echo "Options:"
            echo "  --region REGION        AWS region (default: us-east-1)"
            echo "  --account-id ID        AWS account ID (auto-detected if not provided)"
            echo "  --help                 Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main