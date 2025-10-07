#!/bin/bash
set -e

# Kinexus AI Development Environment Setup
# This script sets up the complete local development environment

echo "🚀 Setting up Kinexus AI Development Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check for container runtime (Podman or Docker)
CONTAINER_CMD=""
COMPOSE_CMD=""

if command -v podman &> /dev/null; then
    if ! podman info > /dev/null 2>&1; then
        print_error "Podman is not running. Please start Podman machine: podman machine start"
        exit 1
    fi
    CONTAINER_CMD="podman"

    # Check for podman-compose
    if command -v podman-compose &> /dev/null; then
        COMPOSE_CMD="podman-compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        export DOCKER_HOST="unix://$(podman machine inspect --format '{{.ConnectionInfo.PodmanSocket.Path}}')"
    else
        print_error "Neither podman-compose nor docker-compose is available"
        exit 1
    fi
    print_success "Podman is running"

elif command -v docker &> /dev/null; then
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    CONTAINER_CMD="docker"
    COMPOSE_CMD="docker-compose"
    print_success "Docker is running"

else
    print_error "Neither Podman nor Docker is available. Please install one and try again."
    exit 1
fi

print_success "$COMPOSE_CMD is available"

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    print_status "Creating .env file..."
    cat > .env << EOF
# Development Environment Variables
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database Configuration
DB_HOST=localhost
DB_PORT=3100
DB_NAME=kinexus_dev
DB_USER=kinexus_user
DB_PASSWORD=kinexus_pass

# Redis Configuration
REDIS_URL=redis://localhost:3101/0

# AWS Mock Configuration (LocalStack)
AWS_ENDPOINT_URL=http://localhost:3102
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1

# OpenSearch Configuration
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=3103

# Mock Bedrock Configuration
BEDROCK_ENDPOINT_URL=http://localhost:3106

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=dev-secret-key-change-in-production

# Frontend Configuration
VITE_API_URL=http://localhost:3105
VITE_WS_URL=ws://localhost:3105
EOF
    print_success "Created .env file"
else
    print_warning ".env file already exists, skipping creation"
fi

# Stop any existing containers
print_status "Stopping any existing containers..."
$COMPOSE_CMD down --remove-orphans

# Pull latest images
print_status "Pulling latest images..."
$COMPOSE_CMD pull

# Build custom images
print_status "Building custom images..."
$COMPOSE_CMD build

# Start infrastructure services first
print_status "Starting infrastructure services..."
$COMPOSE_CMD up -d postgres redis localstack opensearch

# Wait for services to be healthy
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
services=("postgres" "redis" "localstack" "opensearch")
for service in "${services[@]}"; do
    print_status "Checking $service health..."
    if $COMPOSE_CMD ps $service | grep -q "healthy\|Up"; then
        print_success "$service is ready"
    else
        print_warning "$service might not be fully ready yet"
    fi
done

# Start the mock Bedrock service
print_status "Starting mock Bedrock service..."
$COMPOSE_CMD up -d mock-bedrock

# Run database migrations
print_status "Running database migrations..."
sleep 5  # Give postgres a moment to fully start
$COMPOSE_CMD run --rm api alembic upgrade head

# Start the API and frontend
print_status "Starting API and frontend services..."
$COMPOSE_CMD up -d api frontend

# Wait for services to start
sleep 10

# Show service status
print_status "Service Status:"
echo ""
echo "📊 Services and Ports:"
echo "├── PostgreSQL:      localhost:3100"
echo "├── Redis:           localhost:3101"
echo "├── LocalStack:      localhost:3102"
echo "├── OpenSearch:      localhost:3103"
echo "├── OpenSearch UI:   localhost:3104"
echo "├── API Server:      localhost:3105"
echo "├── Mock Bedrock:    localhost:3106"
echo "└── Frontend:        localhost:3107"
echo ""

echo "🛠️  Admin Tools (optional):"
echo "├── Adminer:         localhost:3108 (docker-compose --profile tools up -d)"
echo "├── Redis Commander: localhost:3109 (docker-compose --profile tools up -d)"
echo "└── OpenSearch UI:   localhost:3110 (docker-compose --profile tools up -d)"
echo ""

# Test API health
print_status "Testing API health..."
sleep 5
if curl -f http://localhost:3105/health > /dev/null 2>&1; then
    print_success "API is responding"
else
    print_warning "API might not be ready yet"
fi

# Test Mock Bedrock
print_status "Testing Mock Bedrock service..."
if curl -f http://localhost:3106/health > /dev/null 2>&1; then
    print_success "Mock Bedrock is responding"
else
    print_warning "Mock Bedrock might not be ready yet"
fi

echo ""
print_success "🎉 Development environment setup complete!"
echo ""
echo "🚀 Quick Start:"
echo "   • Frontend:     http://localhost:3107"
echo "   • API Docs:     http://localhost:3105/docs"
echo "   • Database:     postgresql://kinexus_user:kinexus_pass@localhost:3100/kinexus_dev"
echo ""
echo "📝 Useful Commands:"
echo "   • View logs:    docker-compose logs -f [service]"
echo "   • Stop all:     docker-compose down"
echo "   • Restart:      docker-compose restart [service]"
echo "   • Shell access: docker-compose exec [service] bash"
echo ""
echo "🧪 Testing:"
echo "   • Run tests:    docker-compose exec api pytest"
echo "   • API health:   curl http://localhost:3105/health"
echo "   • Mock AI:      curl http://localhost:3106/agents"
echo ""