#!/bin/bash

# Start API Server Script
# This script starts the FastAPI development server

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Virtual environment not found. Running setup..."
    ./scripts/setup-dev.sh
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

print_status "Starting Kinexus AI API server..."
print_status "Server will be available at: http://localhost:${API_PORT:-8000}"
print_status "API documentation will be available at: http://localhost:${API_PORT:-8000}/docs"
print_status ""
print_status "Press Ctrl+C to stop the server"
print_status ""

# Start the API server with auto-reload
uvicorn src.api.main:app \
    --host ${API_HOST:-0.0.0.0} \
    --port ${API_PORT:-8000} \
    --reload \
    --reload-dir src \
    --log-level ${LOG_LEVEL:-info}