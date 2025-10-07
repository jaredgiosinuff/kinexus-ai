#!/bin/bash
set -e

# Kinexus AI Development Environment Test Script
echo "🧪 Testing Kinexus AI Development Environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Check for container runtime
COMPOSE_CMD=""
if command -v podman-compose &> /dev/null; then
    COMPOSE_CMD="podman-compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    print_error "Neither podman-compose nor docker-compose found"
    exit 1
fi

# Test counter
tests_passed=0
tests_failed=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"

    print_status "Running: $test_name"

    if eval "$test_command" > /dev/null 2>&1; then
        print_success "$test_name"
        ((tests_passed++))
    else
        print_error "$test_name"
        ((tests_failed++))
    fi
}

# Service health tests
echo ""
echo "🏥 Health Checks:"

run_test "PostgreSQL Connection" "curl -f http://localhost:3100/health || pg_isready -h localhost -p 3100 -U kinexus_user"
run_test "Redis Connection" "redis-cli -h localhost -p 3101 ping | grep -q PONG"
run_test "LocalStack Health" "curl -f http://localhost:3102/_localstack/health"
run_test "OpenSearch Health" "curl -f http://localhost:3103/_cluster/health"
run_test "API Health" "curl -f http://localhost:3105/health"
run_test "Mock Bedrock Health" "curl -f http://localhost:3106/health"
run_test "Frontend Accessibility" "curl -f http://localhost:3107/"

# API endpoint tests
echo ""
echo "🔌 API Endpoint Tests:"

run_test "API Documentation" "curl -f http://localhost:3105/docs"
run_test "API OpenAPI Spec" "curl -f http://localhost:3105/openapi.json"

# Mock Bedrock tests
echo ""
echo "🤖 Mock AI Service Tests:"

run_test "List Mock Agents" "curl -f http://localhost:3106/agents"
run_test "Agent Capabilities" "curl -f 'http://localhost:3106/' | grep -q 'anthropic.claude-4'"

# Database connectivity tests
echo ""
echo "💾 Database Tests:"

run_test "Database Migration Status" "$COMPOSE_CMD exec -T api alembic current"
run_test "Database Connection" "$COMPOSE_CMD exec -T postgres psql -U kinexus_user -d kinexus_dev -c 'SELECT 1;'"

# Container status tests
echo ""
echo "📦 Container Status Tests:"

services=("postgres" "redis" "localstack" "opensearch" "api" "mock-bedrock" "frontend")
for service in "${services[@]}"; do
    run_test "$service Container Running" "$COMPOSE_CMD ps $service | grep -q Up"
done

# Integration tests
echo ""
echo "🔗 Integration Tests:"

# Test mock AI agent invocation
test_agent_payload='{"agentId":"document-orchestrator","agentAliasId":"TSTALIASID","sessionId":"test-session-123","inputText":"Test document analysis request"}'
run_test "Mock Agent Invocation" "curl -f -X POST 'http://localhost:3106/agents/document-orchestrator/invoke' -H 'Content-Type: application/json' -d '$test_agent_payload'"

# Test database with API
run_test "API Database Integration" "curl -f 'http://localhost:3105/health' | grep -q 'database'"

# Performance tests
echo ""
echo "⚡ Performance Tests:"

run_test "API Response Time < 2s" "timeout 2s curl -f http://localhost:3105/health"
run_test "Mock Bedrock Response Time < 1s" "timeout 1s curl -f http://localhost:3106/health"

# Summary
echo ""
echo "📊 Test Summary:"
echo "Tests Passed: $tests_passed"
echo "Tests Failed: $tests_failed"
echo "Total Tests: $((tests_passed + tests_failed))"

if [ $tests_failed -eq 0 ]; then
    print_success "🎉 All tests passed! Development environment is ready."
    echo ""
    echo "🚀 Quick Commands:"
    echo "   • View logs:     $COMPOSE_CMD logs -f [service]"
    echo "   • Shell access:  $COMPOSE_CMD exec [service] bash"
    echo "   • Run tests:     $COMPOSE_CMD exec api pytest"
    echo "   • Stop all:      ./scripts/dev-down.sh"
    echo ""
    exit 0
else
    print_error "❌ $tests_failed test(s) failed. Check the services above."
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   • Check logs:    $COMPOSE_CMD logs [failed-service]"
    echo "   • Restart:       $COMPOSE_CMD restart [failed-service]"
    echo "   • Rebuild:       $COMPOSE_CMD build [failed-service]"
    echo ""
    exit 1
fi