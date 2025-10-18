#!/bin/bash
# Run the same code quality checks that GitHub Actions CI runs
# This ensures your code will pass CI before you push

set -e

echo "======================================"
echo "  Running CI Validation Checks"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must be run from kinexus-ai root directory${NC}"
    exit 1
fi

# Use Docker to match CI environment exactly
DOCKER_CMD="docker run --rm -v \"$(pwd):/code\" -w /code python:3.11-slim bash -c"

# Track failures
FAILED=0

# Black formatting check
echo -e "${YELLOW}[1/3] Running black formatter check...${NC}"
OUTPUT=$(docker run --rm -v "$(pwd):/code" -w /code python:3.11-slim bash -c "pip install -q black==25.9.0 && black --check src/ tests/" 2>&1)
if echo "$OUTPUT" | grep -q "would reformat"; then
    echo -e "${RED}❌ Black check failed - files need formatting${NC}"
    echo "$OUTPUT" | grep "would reformat"
    echo -e "${YELLOW}Fix: docker run --rm -v \"\$(pwd):/code\" -w /code python:3.11-slim bash -c \"pip install -q black==25.9.0 && black src/ tests/\"${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Black check passed${NC}"
fi
echo ""

# Isort import ordering check
echo -e "${YELLOW}[2/3] Running isort import check...${NC}"
OUTPUT=$(docker run --rm -v "$(pwd):/code" -w /code python:3.11-slim bash -c "pip install -q isort==5.* && isort --check-only src/ tests/" 2>&1)
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Isort check failed - imports need sorting${NC}"
    echo "$OUTPUT" | grep -E "would reformat|Fixing"
    echo -e "${YELLOW}Fix: docker run --rm -v \"\$(pwd):/code\" -w /code python:3.11-slim bash -c \"pip install -q isort==5.* && isort src/ tests/\"${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Isort check passed${NC}"
fi
echo ""

# Ruff linting check
echo -e "${YELLOW}[3/3] Running ruff linter...${NC}"
OUTPUT=$(docker run --rm -v "$(pwd):/code" -w /code python:3.11-slim bash -c "pip install -q ruff==0.1.* && ruff check src/ tests/" 2>&1)
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ruff check failed - linting issues found${NC}"
    echo "$OUTPUT" | grep -v "^WARNING:" | grep -v "notice"
    echo -e "${YELLOW}Fix: docker run --rm -v \"\$(pwd):/code\" -w /code python:3.11-slim bash -c \"pip install -q ruff==0.1.* && ruff check src/ tests/ --fix\"${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Ruff check passed${NC}"
fi
echo ""

# Summary
echo "======================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All CI checks passed!${NC}"
    echo -e "${GREEN}Your code is ready to push.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some CI checks failed${NC}"
    echo -e "${YELLOW}Fix the issues above before pushing${NC}"
    exit 1
fi
