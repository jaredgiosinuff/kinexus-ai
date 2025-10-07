#!/bin/bash
set -e

# Kinexus AI Development Environment Teardown
echo "🛑 Stopping Kinexus AI Development Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check for podman first, then docker
CONTAINER_CMD=""
if command -v podman &> /dev/null; then
    CONTAINER_CMD="podman-compose"
    print_status "Using Podman"
elif command -v docker &> /dev/null; then
    CONTAINER_CMD="docker-compose"
    print_status "Using Docker"
else
    echo -e "${RED}[ERROR]${NC} Neither podman nor docker found!"
    exit 1
fi

# Stop all services
print_status "Stopping all services..."
$CONTAINER_CMD down --remove-orphans

# Optional: Remove volumes (ask user)
if [ "$1" = "--volumes" ] || [ "$1" = "-v" ]; then
    print_status "Removing volumes..."
    $CONTAINER_CMD down -v
    print_success "Volumes removed"
fi

# Optional: Remove images (ask user)
if [ "$1" = "--images" ] || [ "$1" = "-i" ]; then
    print_status "Removing custom images..."
    if command -v podman &> /dev/null; then
        podman rmi $(podman images --filter "reference=kinexusai*" -q) 2>/dev/null || true
    else
        docker rmi $(docker images --filter "reference=kinexusai*" -q) 2>/dev/null || true
    fi
    print_success "Images removed"
fi

print_success "🛑 Environment stopped"
echo ""
echo "Usage:"
echo "  ./scripts/dev-down.sh           # Stop services only"
echo "  ./scripts/dev-down.sh --volumes  # Stop and remove volumes"
echo "  ./scripts/dev-down.sh --images   # Stop and remove custom images"