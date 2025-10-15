#!/bin/bash

# Create ECR Repositories for Kinexus AI
# This script creates all necessary ECR repositories for production Docker images

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

# Function to show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -r, --region REGION     AWS region (default: us-east-1)"
    echo "  -p, --profile PROFILE   AWS profile to use"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 --region us-west-2"
    echo "  $0 --profile production"
}

# Default values
REGION="us-east-1"
PROFILE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
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

# AWS CLI options
AWS_OPTS="--region $REGION"
if [[ -n "$PROFILE" ]]; then
    AWS_OPTS="$AWS_OPTS --profile $PROFILE"
fi

print_status "Creating ECR repositories for Kinexus AI"
print_status "Region: $REGION"
if [[ -n "$PROFILE" ]]; then
    print_status "Profile: $PROFILE"
fi
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    print_error "Install from: https://aws.amazon.com/cli/"
    exit 1
fi

# Verify AWS credentials
print_status "Verifying AWS credentials..."
if ! aws sts get-caller-identity $AWS_OPTS &> /dev/null; then
    print_error "AWS credentials not configured or invalid"
    exit 1
fi
print_success "AWS credentials verified"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity $AWS_OPTS --query 'Account' --output text)
print_status "AWS Account ID: $ACCOUNT_ID"
echo ""

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
print_status "Creating ECR repositories..."
echo ""

created_count=0
skipped_count=0
failed_count=0

for service in "${services[@]}"; do
    print_status "Creating repository: $service"

    # Check if repository already exists
    if aws ecr describe-repositories \
        $AWS_OPTS \
        --repository-names "$service" &> /dev/null; then
        print_warning "Repository already exists: $service"
        ((skipped_count++))
        continue
    fi

    # Create repository
    if aws ecr create-repository \
        $AWS_OPTS \
        --repository-name "$service" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        --tags "Key=Project,Value=KinexusAI" "Key=ManagedBy,Value=Script" \
        &> /dev/null; then

        print_success "Created repository: $service"
        ((created_count++))

        # Set lifecycle policy to clean up old images
        LIFECYCLE_POLICY='{
          "rules": [
            {
              "rulePriority": 1,
              "description": "Keep last 10 images",
              "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 10
              },
              "action": {
                "type": "expire"
              }
            },
            {
              "rulePriority": 2,
              "description": "Remove untagged images after 7 days",
              "selection": {
                "tagStatus": "untagged",
                "countType": "sinceImagePushed",
                "countUnit": "days",
                "countNumber": 7
              },
              "action": {
                "type": "expire"
              }
            }
          ]
        }'

        if aws ecr put-lifecycle-policy \
            $AWS_OPTS \
            --repository-name "$service" \
            --lifecycle-policy-text "$LIFECYCLE_POLICY" \
            &> /dev/null; then
            print_success "Set lifecycle policy for: $service"
        else
            print_warning "Failed to set lifecycle policy for: $service"
        fi

    else
        print_error "Failed to create repository: $service"
        ((failed_count++))
    fi

    echo ""
done

# Summary
echo ""
print_status "========================================="
print_status "ECR Repository Creation Summary"
print_status "========================================="
print_success "Created: $created_count repositories"
if [[ $skipped_count -gt 0 ]]; then
    print_warning "Skipped: $skipped_count repositories (already exist)"
fi
if [[ $failed_count -gt 0 ]]; then
    print_error "Failed: $failed_count repositories"
fi
print_status "========================================="
echo ""

# List all repositories
print_status "ECR Repositories:"
aws ecr describe-repositories \
    $AWS_OPTS \
    --query 'repositories[?starts_with(repositoryName, `kinexus-ai`)].{Name:repositoryName,URI:repositoryUri}' \
    --output table

echo ""
print_status "ECR Login Command:"
echo "aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
echo ""

# Show next steps
print_status "Next Steps:"
echo "1. Log in to ECR using the command above"
echo "2. Build Docker images: ./quick-start.sh build"
echo "3. Tag images for ECR:"
echo "   docker tag kinexus-ai-api:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/kinexus-ai-api:latest"
echo "4. Push images to ECR:"
echo "   docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/kinexus-ai-api:latest"
echo "5. Or use GitHub Actions workflow for automated builds and pushes"
echo ""

if [[ $failed_count -eq 0 ]]; then
    print_success "All repositories created successfully!"
    exit 0
else
    print_error "Some repositories failed to create"
    exit 1
fi
