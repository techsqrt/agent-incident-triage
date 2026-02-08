#!/bin/bash
# Health check script for agent-incident-triage
# Run locally to verify deployment readiness

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default to production URLs
API_URL="${API_URL:-https://agent-incident-triage-production.up.railway.app}"
WEB_URL="${WEB_URL:-https://agent-incident-triage.vercel.app}"

echo "========================================"
echo "Health Check for Agent Incident Triage"
echo "========================================"
echo ""
echo "API: $API_URL"
echo "Web: $WEB_URL"
echo ""

ERRORS=0

# Helper function
check() {
    local name="$1"
    local url="$2"
    local expected="$3"

    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" == "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗${NC} $name - Expected $expected, got $http_code"
        echo "  Response: $body"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

check_contains() {
    local name="$1"
    local url="$2"
    local contains="$3"

    response=$(curl -s "$url" 2>/dev/null)

    if echo "$response" | grep -q "$contains"; then
        echo -e "${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "${RED}✗${NC} $name - Response doesn't contain '$contains'"
        echo "  Response: $response"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo "--- API Health Checks ---"
check "API /health" "$API_URL/health" "200"
check "API /api/triage/domains" "$API_URL/api/triage/domains" "200"
check "API /api/triage/recaptcha/status" "$API_URL/api/triage/recaptcha/status" "200"

echo ""
echo "--- API Response Validation ---"
check_contains "Domains returns medical" "$API_URL/api/triage/domains" "medical"
check_contains "Health returns ok" "$API_URL/health" "ok"

echo ""
echo "--- Web Health Checks ---"
check "Web homepage" "$WEB_URL" "200"
check "Web /triage" "$WEB_URL/triage" "200"

echo ""
echo "--- Database Migration Check ---"
# Check if verified_ips table exists by calling the endpoint
recaptcha_response=$(curl -s "$API_URL/api/triage/recaptcha/status" 2>/dev/null)
if echo "$recaptcha_response" | grep -q "verified"; then
    echo -e "${GREEN}✓${NC} verified_ips table exists (migration applied)"
else
    echo -e "${RED}✗${NC} verified_ips table missing - migration not applied"
    echo "  Response: $recaptcha_response"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS check(s) failed${NC}"
    exit 1
fi
