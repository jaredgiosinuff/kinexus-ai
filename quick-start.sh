#!/bin/bash
# Kinexus AI Quick Start Script
# Automated setup for development and production environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE=".env"
POETRY_LOCK="poetry.lock"

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                     🚀 KINEXUS AI                           ║"
    echo "║            AI-Driven Document Management System              ║"
    echo "║                  Quick Start Deployment                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
    fi

    # Check Poetry
    if ! command -v poetry &> /dev/null; then
        print_warning "Poetry not found. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
    fi

    print_success "All prerequisites met"
}

setup_environment() {
    print_step "Setting up environment..."

    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Creating .env file from template..."
        cat > "$ENV_FILE" << EOF
# Kinexus AI Environment Configuration
ENVIRONMENT=development

# Database Configuration
DB_NAME=kinexus_dev
DB_USER=kinexus_user
DB_PASSWORD=kinexus_secure_pass_2024

# AWS Configuration (for production)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# API Keys (replace with actual keys)
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key

# Security
JWT_SECRET_KEY=$(openssl rand -base64 32)

# Logging
LOG_LEVEL=INFO
EOF
        print_warning "Please update .env file with your actual credentials"
    else
        print_success "Environment file exists"
    fi
}

generate_poetry_lock() {
    print_step "Generating Poetry lock file..."

    if [ ! -f "$POETRY_LOCK" ]; then
        print_warning "Poetry lock file not found. Generating..."
        poetry lock --no-update
        print_success "Poetry lock file generated"
    else
        print_success "Poetry lock file exists"
    fi
}

build_base_images() {
    print_step "Building base Docker images..."

    # Build agent base image first (used by multiple services)
    docker build -f docker/Dockerfile.agent-base -t kinexus-ai-agent-base:latest .

    print_success "Base images built successfully"
}

start_development() {
    print_step "Starting development environment..."

    print_step "Building and starting all services..."
    docker-compose up --build -d

    print_step "Waiting for services to be healthy..."
    sleep 10

    # Check service health
    echo -e "\n${BLUE}Service Status:${NC}"
    docker-compose ps

    echo -e "\n${GREEN}🎉 Kinexus AI is running!${NC}"
    echo -e "\n${BLUE}Available Services:${NC}"
    echo "🌐 Frontend:              http://localhost:3107"
    echo "🚀 API:                   http://localhost:3105"
    echo "🎯 Orchestrator:          http://localhost:8010"
    echo "🔍 Change Analyzer:       http://localhost:8011"
    echo "📝 Content Creator:       http://localhost:8012"
    echo "✅ Quality Controller:    http://localhost:8013"
    echo "🌐 Web Automator:         http://localhost:8014"
    echo "📊 GraphRAG:              http://localhost:3111"
    echo ""
    echo "🛠️  Admin Tools:"
    echo "📋 Database Admin:        http://localhost:3108"
    echo "🔴 Redis Commander:       http://localhost:3109"
    echo "🔍 OpenSearch Dashboards: http://localhost:3110"
    echo ""
    echo -e "${YELLOW}💡 Tip: Use './quick-start.sh logs [service]' to view logs${NC}"
}

start_production() {
    print_step "Starting production environment..."

    if [ ! -f ".env" ]; then
        print_error "Production requires .env file with actual credentials"
    fi

    # Validate production environment
    if grep -q "your_" .env; then
        print_error "Please update .env file with actual credentials before production deployment"
    fi

    print_step "Building production images..."
    docker-compose -f docker-compose.prod.yml build

    print_step "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d

    print_step "Waiting for services to be healthy..."
    sleep 15

    echo -e "\n${GREEN}🎉 Kinexus AI Production is running!${NC}"
    echo -e "\n${BLUE}Production Services:${NC}"
    echo "🌐 Frontend:              http://localhost:80"
    echo "🚀 API:                   http://localhost:8000"
    echo "🎯 Orchestrator:          http://localhost:8010"
    echo "🔍 Change Analyzer:       http://localhost:8011"
    echo "📝 Content Creator:       http://localhost:8012"
    echo "✅ Quality Controller:    http://localhost:8013"
    echo "🌐 Web Automator:         http://localhost:8014"
}

stop_services() {
    print_step "Stopping all services..."

    if [ "$1" = "prod" ]; then
        docker-compose -f docker-compose.prod.yml down
    else
        docker-compose down
    fi

    print_success "All services stopped"
}

cleanup() {
    print_step "Cleaning up Docker resources..."

    # Stop and remove containers
    docker-compose down --remove-orphans
    docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

    # Remove images
    docker rmi $(docker images "kinexus*" -q) 2>/dev/null || true

    # Prune unused resources
    docker system prune -f

    print_success "Cleanup completed"
}

run_tests() {
    print_step "Running tests in containerized environment..."

    # Ensure services are running
    docker-compose up -d postgres redis

    # Wait for database
    sleep 5

    # Run tests
    docker-compose exec api poetry run pytest tests/ --cov=src --cov-report=term-missing

    print_success "Tests completed"
}

show_logs() {
    local service=${1:-""}

    if [ -z "$service" ]; then
        print_step "Showing logs for all services..."
        docker-compose logs -f
    else
        print_step "Showing logs for $service..."
        docker-compose logs -f "$service"
    fi
}

show_usage() {
    echo -e "\n${BLUE}Usage: $0 [command]${NC}"
    echo ""
    echo "Commands:"
    echo "  dev         Start development environment (default)"
    echo "  prod        Start production environment"
    echo "  stop        Stop development services"
    echo "  stop-prod   Stop production services"
    echo "  restart     Restart development services"
    echo "  build       Build all Docker images"
    echo "  test        Run tests"
    echo "  logs        Show logs for all services"
    echo "  logs <svc>  Show logs for specific service"
    echo "  cleanup     Clean up Docker resources"
    echo "  status      Show service status"
    echo "  help        Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0              # Start development environment"
    echo "  $0 dev          # Start development environment"
    echo "  $0 prod         # Start production environment"
    echo "  $0 logs api     # Show API service logs"
    echo "  $0 test         # Run test suite"
    echo ""
}

# Main execution
main() {
    print_banner

    case "${1:-dev}" in
        "dev"|"development"|"")
            check_prerequisites
            setup_environment
            generate_poetry_lock
            build_base_images
            start_development
            ;;
        "prod"|"production")
            check_prerequisites
            setup_environment
            generate_poetry_lock
            build_base_images
            start_production
            ;;
        "stop")
            stop_services
            ;;
        "stop-prod")
            stop_services prod
            ;;
        "restart")
            stop_services
            sleep 2
            start_development
            ;;
        "build")
            check_prerequisites
            generate_poetry_lock
            build_base_images
            print_success "All images built successfully"
            ;;
        "test")
            check_prerequisites
            run_tests
            ;;
        "logs")
            show_logs "${2:-}"
            ;;
        "cleanup")
            cleanup
            ;;
        "status")
            docker-compose ps
            echo ""
            docker-compose -f docker-compose.prod.yml ps 2>/dev/null || true
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Interrupted by user${NC}"; exit 1' INT

# Run main function with all arguments
main "$@"