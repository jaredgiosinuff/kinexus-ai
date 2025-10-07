#!/bin/bash

# Start Frontend Development Server Script
# This script starts the Vite development server for the React frontend

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

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    print_error "Frontend directory not found!"
    exit 1
fi

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    print_status "Node modules not found. Installing dependencies..."
    npm install
fi

print_status "Starting Kinexus AI frontend development server..."
print_status "Frontend will be available at: http://localhost:3000"
print_status ""
print_status "Press Ctrl+C to stop the server"
print_status ""

# Start the development server
npm run dev