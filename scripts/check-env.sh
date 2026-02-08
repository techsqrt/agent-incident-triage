#!/bin/bash
# Check that all required environment variables are set
# Run before deployment to catch missing config

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Environment Variable Check"
echo "========================================"
echo ""

ERRORS=0
WARNINGS=0

check_required() {
    local var_name="$1"
    local description="$2"

    if [ -n "${!var_name}" ]; then
        echo -e "${GREEN}✓${NC} $var_name is set"
    else
        echo -e "${RED}✗${NC} $var_name is NOT set - $description"
        ERRORS=$((ERRORS + 1))
    fi
}

check_optional() {
    local var_name="$1"
    local description="$2"

    if [ -n "${!var_name}" ]; then
        echo -e "${GREEN}✓${NC} $var_name is set"
    else
        echo -e "${YELLOW}○${NC} $var_name is not set (optional) - $description"
        WARNINGS=$((WARNINGS + 1))
    fi
}

echo "--- Backend (Railway) ---"
check_required "DATABASE_URL" "PostgreSQL connection string"
check_required "OPENAI_API_KEY" "Required for voice pipeline"
check_optional "RECAPTCHA_SECRET_KEY" "Required for bot protection"

echo ""
echo "--- Frontend (Vercel) ---"
check_required "NEXT_PUBLIC_API_URL" "Backend API URL"
check_optional "NEXT_PUBLIC_RECAPTCHA_SITE_KEY" "Required for bot protection"

echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}$WARNINGS optional variable(s) not set${NC}"
    fi
    echo -e "${GREEN}All required variables are set!${NC}"
    exit 0
else
    echo -e "${RED}$ERRORS required variable(s) missing${NC}"
    exit 1
fi
