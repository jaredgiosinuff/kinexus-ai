#!/bin/bash

# Development Environment Setup Script for Kinexus AI
# This script sets up the local development environment

set -e

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."

    local missing_deps=()

    if ! command_exists python3; then
        missing_deps+=("python3")
    fi

    if ! command_exists pip; then
        missing_deps+=("pip")
    fi

    if ! command_exists node; then
        missing_deps+=("node")
    fi

    if ! command_exists npm; then
        missing_deps+=("npm")
    fi

    if ! command_exists docker; then
        missing_deps+=("docker")
    fi

    if ! command_exists docker-compose; then
        missing_deps+=("docker-compose")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        print_error "Please install them before running this script"
        exit 1
    fi

    print_success "All prerequisites found"
}

# Setup Python environment
setup_python_env() {
    print_status "Setting up Python environment..."

    # Check Python version
    python_version=$(python3 --version | cut -d' ' -f2)
    required_version="3.9"

    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python $required_version or higher is required. Found: $python_version"
        exit 1
    fi

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install requirements
    if [ -f "requirements.txt" ]; then
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt
    fi

    if [ -f "requirements-dev.txt" ]; then
        print_status "Installing development dependencies..."
        pip install -r requirements-dev.txt
    fi

    print_success "Python environment setup complete"
}

# Setup Node.js environment
setup_node_env() {
    print_status "Setting up Node.js environment..."

    # Check Node version
    node_version=$(node --version | sed 's/v//')
    required_version="16.0.0"

    if [ "$(printf '%s\n' "$required_version" "$node_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Node.js $required_version or higher is required. Found: $node_version"
        exit 1
    fi

    # Install frontend dependencies
    if [ -d "frontend" ]; then
        print_status "Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
    fi

    print_success "Node.js environment setup complete"
}

# Setup local services with Docker
setup_local_services() {
    print_status "Setting up local services with Docker..."

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi

    # Start services
    print_status "Starting PostgreSQL, Redis, and LocalStack..."
    docker-compose up -d postgres redis localstack

    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10

    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Local services started successfully"
    else
        print_error "Failed to start local services"
        docker-compose logs
        exit 1
    fi
}

# Setup database
setup_database() {
    print_status "Setting up database..."

    # Activate virtual environment
    source venv/bin/activate

    # Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    max_attempts=30
    attempt=1

    while [ $attempt -le $max_attempts ]; do
        if python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='kinexus_dev',
        user='kinexus_user',
        password='kinexus_pass'
    )
    conn.close()
    print('Database connection successful')
    exit(0)
except:
    print('Database not ready yet...')
    exit(1)
" 2>/dev/null; then
            break
        fi

        print_status "Attempt $attempt/$max_attempts: Database not ready yet..."
        sleep 2
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        print_error "Database failed to become ready"
        exit 1
    fi

    # Run database migrations
    if [ -f "alembic.ini" ]; then
        print_status "Running database migrations..."
        alembic upgrade head
    fi

    # Seed development data
    if [ -f "scripts/seed_dev_data.py" ]; then
        print_status "Seeding development data..."
        python scripts/seed_dev_data.py
    fi

    print_success "Database setup complete"
}

# Create environment files
create_env_files() {
    print_status "Creating environment files..."

    # Backend .env file
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://kinexus_user:kinexus_pass@localhost:5432/kinexus_dev
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kinexus_dev
DB_USER=kinexus_user
DB_PASSWORD=kinexus_pass

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# AWS Configuration (LocalStack)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_DEFAULT_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566

# JWT Configuration
JWT_SECRET_KEY=your-dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# WebSocket Configuration
WS_HOST=0.0.0.0
WS_PORT=8001

# Frontend Configuration
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
EOF
        print_success "Created .env file"
    else
        print_warning ".env file already exists, skipping creation"
    fi

    # Frontend .env file
    if [ ! -f "frontend/.env.local" ]; then
        cat > frontend/.env.local << EOF
# API Configuration
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000/api/ws

# Environment
VITE_NODE_ENV=development
EOF
        print_success "Created frontend/.env.local file"
    else
        print_warning "frontend/.env.local file already exists, skipping creation"
    fi
}

# Main setup function
main() {
    print_status "Starting Kinexus AI development environment setup..."

    check_prerequisites
    create_env_files
    setup_python_env
    setup_node_env
    setup_local_services
    setup_database

    print_success "Development environment setup complete!"
    print_status ""
    print_status "Next steps:"
    print_status "1. Start the API server: ./scripts/start-api.sh"
    print_status "2. Start the frontend: ./scripts/start-frontend.sh"
    print_status "3. Visit http://localhost:3000 to access the application"
    print_status ""
    print_status "To stop local services: docker-compose down"
    print_status "To view logs: docker-compose logs -f"
}

# Run main function
main "$@"