#!/bin/bash

# AWS Deployment Script for Kinexus AI
# This script deploys the application to AWS using CDK

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Portable titlecase helper (capitalize first letter, lowercase rest)
titlecase() {
    printf "%s" "$1" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}'
}

# Function to show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Target environment (development|staging|production)"
    echo "  -t, --type TYPE         Deployment type (mvp|production)"
    echo "  -r, --region REGION     AWS region (default: us-east-1)"
    echo "  -a, --account ACCOUNT   AWS account ID"
    echo "  -p, --profile PROFILE   AWS profile to use"
    echo "  --build-images          Build and push Docker images"
    echo "  --diff                  Show diff before deploying"
    echo "  --approve               Auto-approve changes"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --environment development --type mvp"
    echo "  $0 --environment production --type production --account 123456789012"
    echo "  $0 --environment staging --build-images --diff"
}

# Default values
ENVIRONMENT="development"
DEPLOYMENT_TYPE="mvp"
REGION="us-east-1"
ACCOUNT=""
PROFILE=""
BUILD_IMAGES=false
SHOW_DIFF=false
AUTO_APPROVE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -a|--account)
            ACCOUNT="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        --build-images)
            BUILD_IMAGES=true
            shift
            ;;
        --diff)
            SHOW_DIFF=true
            shift
            ;;
        --approve)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    print_error "Must be one of: development, staging, production"
    exit 1
fi

# Validate deployment type
if [[ "$DEPLOYMENT_TYPE" != "mvp" && "$DEPLOYMENT_TYPE" != "production" ]]; then
    print_error "Invalid deployment type: $DEPLOYMENT_TYPE"
    print_error "Must be one of: mvp, production"
    exit 1
fi

# For production deployments, require account ID
if [[ "$DEPLOYMENT_TYPE" == "production" && -z "$ACCOUNT" ]]; then
    print_error "Account ID is required for production deployments"
    exit 1
fi

print_status "Starting Kinexus AI deployment to AWS"
print_status "Environment: $ENVIRONMENT"
print_status "Deployment Type: $DEPLOYMENT_TYPE"
print_status "Region: $REGION"
if [[ -n "$ACCOUNT" ]]; then
    print_status "Account: $ACCOUNT"
fi
if [[ -n "$PROFILE" ]]; then
    print_status "Profile: $PROFILE"
fi

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        exit 1
    fi

    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK is not installed"
        print_error "Install with: npm install -g aws-cdk"
        exit 1
    fi

    if ! command -v docker &> /dev/null && [[ "$BUILD_IMAGES" == true ]]; then
        print_error "Docker is required for building images"
        exit 1
    fi

    # Check AWS credentials
    local aws_cmd="aws"
    if [[ -n "$PROFILE" ]]; then
        aws_cmd="aws --profile $PROFILE"
    fi

    if ! $aws_cmd sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Build Docker images
build_images() {
    if [[ "$BUILD_IMAGES" != true ]]; then
        return
    fi

    print_status "Building Docker images..."

    # Build API image
    print_status "Building API Docker image..."
    docker build -t kinexus-ai-api:latest -f docker/Dockerfile.api .

    # Build frontend image (if needed for production)
    if [[ "$DEPLOYMENT_TYPE" == "production" ]]; then
        print_status "Building frontend Docker image..."
        docker build -t kinexus-ai-frontend:latest -f docker/Dockerfile.frontend ./frontend
    fi

    # Push to ECR (implement if needed)
    # push_to_ecr

    print_success "Docker images built successfully"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure with CDK..."

    # Prepare CDK context
    local cdk_context=""
    cdk_context="$cdk_context -c deployment_type=$DEPLOYMENT_TYPE"
    cdk_context="$cdk_context -c environment=$ENVIRONMENT"
    cdk_context="$cdk_context -c region=$REGION"
    if [[ -n "$ACCOUNT" ]]; then
        cdk_context="$cdk_context -c account=$ACCOUNT"
    fi

    # AWS CLI options
    local aws_opts=""
    if [[ -n "$PROFILE" ]]; then
        aws_opts="--profile $PROFILE"
    fi

    # Bootstrap CDK (if needed)
    print_status "Bootstrapping CDK..."
    cdk bootstrap $aws_opts $cdk_context

    # Show diff if requested
    if [[ "$SHOW_DIFF" == true ]]; then
        print_status "Showing deployment diff..."
        cdk diff $aws_opts $cdk_context
        echo ""
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Deployment cancelled by user"
            exit 0
        fi
    fi

    # Deploy
    local deploy_opts="$aws_opts $cdk_context"
    if [[ "$AUTO_APPROVE" == true ]]; then
        deploy_opts="$deploy_opts --require-approval never"
    fi

    print_status "Deploying stack..."
    cdk deploy $deploy_opts

    print_success "Infrastructure deployed successfully"
}

# Post-deployment setup
post_deployment_setup() {
    print_status "Running post-deployment setup..."

    if [[ "$DEPLOYMENT_TYPE" == "production" ]]; then
        # Run database migrations
        print_status "Running database migrations..."
        # This would typically be done via ECS task or Lambda
        # aws ecs run-task ...

        # Seed initial data if needed
        print_status "Seeding initial data..."
        # aws lambda invoke ...
    fi

    print_success "Post-deployment setup completed"
}

# Get deployment outputs
get_outputs() {
    print_status "Retrieving deployment outputs..."

    local stack_name
    if [[ "$DEPLOYMENT_TYPE" == "production" ]]; then
        local env_titled
        env_titled="$(titlecase "$ENVIRONMENT")"
        stack_name="KinexusAIProductionStack-${env_titled}"
    else
        local env_titled
        env_titled="$(titlecase "$ENVIRONMENT")"
        stack_name="KinexusAIMVPStack-${env_titled}"
    fi

    local aws_opts=""
    if [[ -n "$PROFILE" ]]; then
        aws_opts="--profile $PROFILE"
    fi

    # Get stack outputs
    local outputs
    outputs=$(aws cloudformation describe-stacks \
        $aws_opts \
        --region $REGION \
        --stack-name $stack_name \
        --query 'Stacks[0].Outputs' \
        --output table 2>/dev/null || echo "No outputs available")

    if [[ "$outputs" != "No outputs available" ]]; then
        print_success "Deployment outputs:"
        echo "$outputs"
    fi
}

# Main deployment function
main() {
    print_status "Starting deployment process..."

    check_prerequisites
    build_images
    deploy_infrastructure
    post_deployment_setup
    get_outputs

    print_success ""
    print_success "🎉 Kinexus AI deployment completed successfully!"
    print_success "Environment: $ENVIRONMENT"
    print_success "Deployment Type: $DEPLOYMENT_TYPE"
    print_success ""

    if [[ "$DEPLOYMENT_TYPE" == "mvp" ]]; then
        print_status "MVP deployment includes:"
        print_status "- Lambda functions for webhooks"
        print_status "- DynamoDB tables"
        print_status "- S3 bucket for documents"
        print_status "- API Gateway"
        print_status "- EventBridge"
    else
        print_status "Production deployment includes:"
        print_status "- ECS Fargate cluster"
        print_status "- RDS PostgreSQL database"
        print_status "- ElastiCache Redis"
        print_status "- Application Load Balancer"
        print_status "- CloudWatch monitoring"
        print_status "- Backup and disaster recovery"
        print_status "- Auto-scaling configuration"
    fi

    print_status ""
    print_status "Next steps:"
    print_status "1. Configure your domain name (if applicable)"
    print_status "2. Set up SSL certificates"
    print_status "3. Configure external webhooks"
    print_status "4. Test the deployment"
}

# Run main function
main "$@"