#!/bin/bash
#
# Phase 9 Test Suite Runner
#
# Runs all Phase 9 tests with appropriate markers and budgets.
# Can be used in CI/CD or locally.
#
# Usage:
#   ./scripts/run_phase9_tests.sh [OPTIONS]
#
# Options:
#   --parity         Run only parity tests
#   --lane           Run only lane integration tests
#   --failure        Run only failure injection tests
#   --perf           Run only performance tests
#   --skip-perf      Skip performance tests (same as RAG_SKIP_PERF=1)
#   --budget-llm N   Set LLM budget to N milliseconds
#   --budget-cache N Set cache budget to N milliseconds
#   --verbose        Verbose output (-vv)
#   --fast           Fast mode (less durations output)
#   --help           Show this help
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_MARKER=""
VERBOSE=""
SKIP_PERF=""
BUDGET_ARGS=""
DURATIONS_ARG="--durations=10"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --parity)
            TEST_MARKER="-m parity"
            shift
            ;;
        --lane)
            TEST_MARKER="-m lane"
            shift
            ;;
        --failure)
            TEST_MARKER="-m failure"
            shift
            ;;
        --perf)
            TEST_MARKER="-m perf"
            shift
            ;;
        --skip-perf)
            SKIP_PERF="1"
            shift
            ;;
        --budget-llm)
            BUDGET_ARGS="$BUDGET_ARGS --budget-llm=$2"
            shift 2
            ;;
        --budget-cache)
            BUDGET_ARGS="$BUDGET_ARGS --budget-cache=$2"
            shift 2
            ;;
        --budget-tools)
            BUDGET_ARGS="$BUDGET_ARGS --budget-tools=$2"
            shift 2
            ;;
        --budget-stream)
            BUDGET_ARGS="$BUDGET_ARGS --budget-stream=$2"
            shift 2
            ;;
        --budget-provider)
            BUDGET_ARGS="$BUDGET_ARGS --budget-provider=$2"
            shift 2
            ;;
        --budget-privacy)
            BUDGET_ARGS="$BUDGET_ARGS --budget-privacy=$2"
            shift 2
            ;;
        --budget-golden)
            BUDGET_ARGS="$BUDGET_ARGS --budget-golden=$2"
            shift 2
            ;;
        --verbose)
            VERBOSE="-vv"
            shift
            ;;
        --fast)
            DURATIONS_ARG=""
            shift
            ;;
        --help)
            grep "^#" "$0" | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set environment variables
if [ -n "$SKIP_PERF" ]; then
    export RAG_SKIP_PERF=1
fi

# Default budgets (can be overridden by CLI args or env vars)
export RAG_BUDGET_P95_CACHE_MS=${RAG_BUDGET_P95_CACHE_MS:-25}
export RAG_BUDGET_P95_LLM_MS=${RAG_BUDGET_P95_LLM_MS:-400}
export RAG_BUDGET_P95_TOOLS_MS=${RAG_BUDGET_P95_TOOLS_MS:-200}
export RAG_BUDGET_P95_STREAM_MS=${RAG_BUDGET_P95_STREAM_MS:-150}
export RAG_BUDGET_P95_PROVIDER_MS=${RAG_BUDGET_P95_PROVIDER_MS:-50}
export RAG_BUDGET_P95_PRIVACY_MS=${RAG_BUDGET_P95_PRIVACY_MS:-30}
export RAG_BUDGET_P95_GOLDEN_MS=${RAG_BUDGET_P95_GOLDEN_MS:-40}

# Print configuration
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 9 Test Suite Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Test marker: ${TEST_MARKER:-all tests}"
echo "  Verbose: ${VERBOSE:-no}"
echo "  Skip perf: ${SKIP_PERF:-no}"
echo ""
echo -e "${YELLOW}Performance Budgets (P95):${NC}"
echo "  Cache:    ${RAG_BUDGET_P95_CACHE_MS}ms"
echo "  LLM:      ${RAG_BUDGET_P95_LLM_MS}ms"
echo "  Tools:    ${RAG_BUDGET_P95_TOOLS_MS}ms"
echo "  Stream:   ${RAG_BUDGET_P95_STREAM_MS}ms"
echo "  Provider: ${RAG_BUDGET_P95_PROVIDER_MS}ms"
echo "  Privacy:  ${RAG_BUDGET_P95_PRIVACY_MS}ms"
echo "  Golden:   ${RAG_BUDGET_P95_GOLDEN_MS}ms"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""

# Build pytest command
PYTEST_CMD="pytest"

# Add test paths
if [ -z "$TEST_MARKER" ]; then
    # Run all Phase 9 tests
    PYTEST_CMD="$PYTEST_CMD tests/phase9_parity tests/phase9_lane_integration tests/phase9_failures"
    if [ -z "$SKIP_PERF" ]; then
        PYTEST_CMD="$PYTEST_CMD tests/phase9_perf"
    fi
else
    # Run specific marker across all Phase 9 directories
    PYTEST_CMD="$PYTEST_CMD $TEST_MARKER"
fi

# Add options
if [ -n "$VERBOSE" ]; then
    PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

if [ -n "$DURATIONS_ARG" ]; then
    PYTEST_CMD="$PYTEST_CMD $DURATIONS_ARG"
fi

if [ -n "$BUDGET_ARGS" ]; then
    PYTEST_CMD="$PYTEST_CMD $BUDGET_ARGS"
fi

# Run tests
echo -e "${GREEN}Running: $PYTEST_CMD${NC}"
echo ""

$PYTEST_CMD

# Capture exit code
EXIT_CODE=$?

# Print summary
echo ""
echo -e "${BLUE}========================================${NC}"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed (exit code: $EXIT_CODE)${NC}"
fi
echo -e "${BLUE}========================================${NC}"

exit $EXIT_CODE
