#!/bin/bash
# Code Quality Check Script
#
# This script runs all code quality checks:
# - Ruff linter (catches errors, unused imports, code smells)
# - Ruff formatter (enforces consistent style)
# - MyPy type checker (catches type errors)
# - Pytest (runs test suite)
#
# Usage:
#   ./scripts/check_code.sh           # Run all checks
#   ./scripts/check_code.sh --fix     # Auto-fix issues
#   ./scripts/check_code.sh --no-test # Skip tests

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
AUTO_FIX=false
RUN_TESTS=true

for arg in "$@"; do
    case $arg in
        --fix)
            AUTO_FIX=true
            shift
            ;;
        --no-test)
            RUN_TESTS=false
            shift
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔍 Running Code Quality Checks${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Step 1: Ruff Linter
echo -e "${YELLOW}📝 Step 1/4: Running Ruff linter...${NC}"
if [ "$AUTO_FIX" = true ]; then
    uv run ruff check . --fix
else
    uv run ruff check .
fi
echo -e "${GREEN}✅ Ruff linter passed${NC}\n"

# Step 2: Ruff Formatter
echo -e "${YELLOW}🎨 Step 2/4: Running Ruff formatter...${NC}"
if [ "$AUTO_FIX" = true ]; then
    uv run ruff format .
else
    uv run ruff format . --check
fi
echo -e "${GREEN}✅ Ruff formatter passed${NC}\n"

# Step 3: MyPy Type Checker
echo -e "${YELLOW}🔬 Step 3/4: Running MyPy type checker...${NC}"
uv run mypy app/ || {
    echo -e "${YELLOW}⚠️  MyPy found type issues (non-blocking)${NC}\n"
}

# Step 4: Tests (optional)
if [ "$RUN_TESTS" = true ]; then
    echo -e "${YELLOW}✅ Step 4/4: Running tests...${NC}"
    uv run pytest || {
        echo -e "${RED}❌ Tests failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ All tests passed${NC}\n"
else
    echo -e "${YELLOW}⏭️  Step 4/4: Skipping tests (--no-test flag)${NC}\n"
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✨ All code quality checks complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

if [ "$AUTO_FIX" = true ]; then
    echo -e "${GREEN}Code has been automatically fixed.${NC}"
    echo -e "${YELLOW}Review changes and commit:${NC}"
    echo -e "  git diff"
    echo -e "  git add ."
    echo -e "  git commit -m \"style: apply code quality fixes\""
else
    echo -e "${YELLOW}To auto-fix issues, run:${NC}"
    echo -e "  ./scripts/check_code.sh --fix"
fi
