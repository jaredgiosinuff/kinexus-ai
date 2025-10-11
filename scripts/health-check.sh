#!/bin/bash
# Health Check Script for Kinexus AI Services
# Validates all services are running and healthy

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}🏥 Kinexus AI Health Check${NC}\n"
}

check_url() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    echo -n "🔍 Checking $name... "

    if response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null); then
        if [ "$response" = "$expected_code" ]; then
            echo -e "${GREEN}✅ OK ($response)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Unexpected response ($response)${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ Failed (no response)${NC}"
        return 1
    fi
}

check_docker_service() {
    local service="$1"
    local compose_file="${2:-docker-compose.yml}"

    echo -n "🐳 Checking Docker service $service... "

    if docker-compose -f "$compose_file" ps "$service" | grep -q "Up.*healthy"; then
        echo -e "${GREEN}✅ Healthy${NC}"
        return 0
    elif docker-compose -f "$compose_file" ps "$service" | grep -q "Up"; then
        echo -e "${YELLOW}⚠️  Running (not healthy)${NC}"
        return 1
    else
        echo -e "${RED}❌ Not running${NC}"
        return 1
    fi
}

main() {
    print_header

    local failed=0
    local env="${1:-dev}"
    local compose_file="docker-compose.yml"

    if [ "$env" = "prod" ]; then
        compose_file="docker-compose.prod.yml"
    fi

    echo -e "${BLUE}Environment: $env${NC}\n"

    # Check Docker services
    echo -e "${BLUE}📦 Docker Services:${NC}"
    check_docker_service "postgres" "$compose_file" || ((failed++))
    check_docker_service "redis" "$compose_file" || ((failed++))
    check_docker_service "opensearch" "$compose_file" || ((failed++))

    if [ "$env" = "dev" ]; then
        check_docker_service "localstack" "$compose_file" || ((failed++))
    fi

    echo ""

    # Check HTTP endpoints
    echo -e "${BLUE}🌐 HTTP Endpoints:${NC}"

    if [ "$env" = "prod" ]; then
        # Production endpoints
        check_url "Frontend" "http://localhost:80" || ((failed++))
        check_url "API Health" "http://localhost:8000/health" || ((failed++))
        check_url "API Docs" "http://localhost:8000/docs" || ((failed++))
        check_url "Orchestrator" "http://localhost:8010/health" || ((failed++))
        check_url "Change Analyzer" "http://localhost:8011/health" || ((failed++))
        check_url "Content Creator" "http://localhost:8012/health" || ((failed++))
        check_url "Quality Controller" "http://localhost:8013/health" || ((failed++))
        check_url "Web Automator" "http://localhost:8014/health" || ((failed++))
    else
        # Development endpoints
        check_url "Frontend" "http://localhost:3107" || ((failed++))
        check_url "API Health" "http://localhost:3105/health" || ((failed++))
        check_url "API Docs" "http://localhost:3105/docs" || ((failed++))
        check_url "Orchestrator" "http://localhost:8010/health" || ((failed++))
        check_url "Change Analyzer" "http://localhost:8011/health" || ((failed++))
        check_url "Content Creator" "http://localhost:8012/health" || ((failed++))
        check_url "Quality Controller" "http://localhost:8013/health" || ((failed++))
        check_url "Web Automator" "http://localhost:8014/health" || ((failed++))
        check_url "GraphRAG" "http://localhost:3111/health" || ((failed++))

        echo ""
        echo -e "${BLUE}🛠️  Admin Tools:${NC}"
        check_url "Database Admin" "http://localhost:3108" || ((failed++))
        check_url "Redis Commander" "http://localhost:3109" || ((failed++))
        check_url "OpenSearch Dashboards" "http://localhost:3110" || ((failed++))
    fi

    echo ""

    # Summary
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}🎉 All services are healthy!${NC}"
        exit 0
    else
        echo -e "${RED}❌ $failed service(s) failed health checks${NC}"
        echo -e "${YELLOW}💡 Try: ./quick-start.sh logs [service-name]${NC}"
        exit 1
    fi
}

# Show usage
if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 [dev|prod]"
    echo ""
    echo "Check health of all Kinexus AI services"
    echo ""
    echo "Arguments:"
    echo "  dev     Check development environment (default)"
    echo "  prod    Check production environment"
    echo ""
    exit 0
fi

main "$@"