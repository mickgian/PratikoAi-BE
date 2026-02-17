#!/bin/bash
# =============================================================================
# PratikoAI Post-Deployment Smoke Tests
# =============================================================================
# Validates that a deployed PratikoAI environment is functional.
#
# Usage:
#   ./scripts/smoke_test.sh <api-url> [frontend-url]
#   ./scripts/smoke_test.sh https://api-qa.pratiko.app https://app-qa.pratiko.app
# =============================================================================

set -euo pipefail

API_URL="${1:?Usage: $0 <api-url> [frontend-url]}"
FE_URL="${2:-}"

PASSED=0
FAILED=0
WARNINGS=0

check() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"

    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 15 "$url" 2>/dev/null || echo "000")
    if [ "$STATUS" = "$expected_status" ]; then
        echo "  PASS: $name (HTTP $STATUS)"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $name (expected $expected_status, got $STATUS)"
        FAILED=$((FAILED + 1))
    fi
}

check_json() {
    local name="$1"
    local url="$2"
    local jq_filter="$3"

    RESPONSE=$(curl -sf --max-time 15 "$url" 2>/dev/null || echo "")
    if [ -z "$RESPONSE" ]; then
        echo "  FAIL: $name (no response)"
        FAILED=$((FAILED + 1))
        return
    fi

    # Check if response contains expected field
    if echo "$RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); $jq_filter" 2>/dev/null; then
        echo "  PASS: $name"
        PASSED=$((PASSED + 1))
    else
        echo "  FAIL: $name (unexpected response)"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== PratikoAI Smoke Tests ==="
echo "API: $API_URL"
[ -n "$FE_URL" ] && echo "FE:  $FE_URL"
echo "Time: $(date -u)"
echo ""

# --- Backend Checks ---
echo "Backend:"
check "Health endpoint" "$API_URL/health"
check "Metrics endpoint" "$API_URL/metrics"
check "API docs" "$API_URL/docs"

# Check health response body
check_json "Health body" "$API_URL/health" "assert data.get('status') in ('healthy', 'ok')"

# Auth flow - login should return 422 without body (validation error, not 500)
STATUS=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 15 \
    -X POST "$API_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{}' 2>/dev/null || echo "000")
if [ "$STATUS" = "422" ]; then
    echo "  PASS: Auth endpoint reachable (422 = validation working)"
    PASSED=$((PASSED + 1))
else
    echo "  WARN: Auth endpoint returned $STATUS (expected 422)"
    WARNINGS=$((WARNINGS + 1))
fi

# Billing plans (public endpoint)
check "Billing plans" "$API_URL/api/v1/billing/plans"

echo ""

# --- Frontend Checks ---
if [ -n "$FE_URL" ]; then
    echo "Frontend:"
    check "Home page" "$FE_URL"
    check "Login page" "$FE_URL/login"
    echo ""
fi

# --- Summary ---
TOTAL=$((PASSED + FAILED + WARNINGS))
echo "=== Results ==="
echo "Passed:   $PASSED/$TOTAL"
echo "Failed:   $FAILED/$TOTAL"
echo "Warnings: $WARNINGS/$TOTAL"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo "SMOKE TESTS FAILED"
    exit 1
fi

echo "ALL SMOKE TESTS PASSED"
exit 0
