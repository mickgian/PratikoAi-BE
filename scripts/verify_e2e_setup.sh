#!/bin/bash
# Verification script for E2E test setup
# Run this script to verify E2E testing infrastructure is configured correctly

set -e  # Exit on error

echo "=========================================="
echo "E2E Test Setup Verification Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: PostgreSQL is running
echo "1. Checking PostgreSQL connection..."
if psql -U postgres -c "SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not running or not accessible${NC}"
    echo "  Start PostgreSQL or check connection settings"
    exit 1
fi

# Check 2: Test database exists
echo ""
echo "2. Checking test database exists..."
if psql -U postgres -lqt | cut -d \| -f 1 | grep -qw pratiko_ai_test; then
    echo -e "${GREEN}✓ Test database 'pratiko_ai_test' exists${NC}"
else
    echo -e "${YELLOW}⚠ Test database 'pratiko_ai_test' does not exist${NC}"
    echo "  Creating test database..."
    psql -U postgres -c "CREATE DATABASE pratiko_ai_test;" || {
        echo -e "${RED}✗ Failed to create test database${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Test database created${NC}"
fi

# Check 3: Python dependencies installed
echo ""
echo "3. Checking Python dependencies..."
if uv run python -c "import pytest; import httpx; import sqlalchemy" 2>/dev/null; then
    echo -e "${GREEN}✓ Required Python packages installed${NC}"
else
    echo -e "${RED}✗ Missing required Python packages${NC}"
    echo "  Run: uv sync"
    exit 1
fi

# Check 4: Database migrations applied
echo ""
echo "4. Checking database migrations..."
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/pratiko_ai_test"
if uv run alembic current &> /dev/null; then
    echo -e "${GREEN}✓ Database migrations applied${NC}"
    uv run alembic current
else
    echo -e "${YELLOW}⚠ Database migrations not applied${NC}"
    echo "  Applying migrations..."
    uv run alembic upgrade head || {
        echo -e "${RED}✗ Failed to apply migrations${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Migrations applied${NC}"
fi

# Check 5: E2E test files exist
echo ""
echo "5. Checking E2E test files..."
if [ -f "tests/e2e/test_expert_feedback_e2e.py" ]; then
    echo -e "${GREEN}✓ E2E test files exist${NC}"
else
    echo -e "${RED}✗ E2E test files not found${NC}"
    echo "  Expected: tests/e2e/test_expert_feedback_e2e.py"
    exit 1
fi

# Check 6: Run E2E tests (dry run)
echo ""
echo "6. Running E2E tests (verification)..."
echo "  This may take 15-30 seconds..."
if uv run pytest tests/e2e/ -v --collect-only &> /dev/null; then
    TEST_COUNT=$(uv run pytest tests/e2e/ --collect-only -q | grep -c "test_e2e" || echo "0")
    echo -e "${GREEN}✓ E2E tests collected: ${TEST_COUNT} tests${NC}"
else
    echo -e "${RED}✗ Failed to collect E2E tests${NC}"
    exit 1
fi

# Check 7: Actually run tests (optional - can be slow)
echo ""
echo "7. Running E2E tests (actual execution)..."
echo -e "${YELLOW}⚠ This may take 15-30 seconds...${NC}"

if uv run pytest tests/e2e/test_expert_feedback_e2e.py -v; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✓ ALL E2E TESTS PASSED!"
    echo "==========================================${NC}"
else
    echo ""
    echo -e "${RED}=========================================="
    echo "✗ SOME E2E TESTS FAILED"
    echo "==========================================${NC}"
    echo ""
    echo "Check the output above for error details."
    echo "Common issues:"
    echo "  - Database connection errors (check DATABASE_URL)"
    echo "  - Missing tables (run: alembic upgrade head)"
    echo "  - Fixture errors (check conftest.py)"
    exit 1
fi

# Success summary
echo ""
echo -e "${GREEN}=========================================="
echo "E2E Test Setup Verification COMPLETE"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review test output above"
echo "  2. Implement remaining E2E tests (E2E-03, 06, 08, 09, 10)"
echo "  3. Add E2E tests to CI/CD pipeline"
echo ""
echo "Documentation:"
echo "  - Strategy: docs/testing/E2E_EXPERT_FEEDBACK_TESTING_STRATEGY.md"
echo "  - Guide: E2E_TESTING_IMPLEMENTATION_GUIDE.md"
echo "  - README: tests/e2e/README.md"
echo ""
