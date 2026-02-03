#!/bin/bash
# Run UI regression tests for Streamlit pages
#
# This script runs the UI regression test suite that simulates
# user interactions with Streamlit pages using AppTest framework.
#
# Usage:
#   ./run_ui_regression.sh [smoke|e2e|all]
#
# Options:
#   smoke - Run only smoke tests (rendering verification, no database writes)
#   e2e   - Run only end-to-end tests (full workflows with database verification)
#   all   - Run all UI tests (default)

set -e

# Parse arguments
TEST_TYPE="${1:-all}"

echo "🧪 Starting Streamlit UI Regression Tests"
echo "=========================================="

# Ensure containers are running
echo "🚀 Starting containers..."
docker compose up -d db admin

# Wait for database to be healthy
echo "⏳ Waiting for database..."
MAX_RETRIES=30
RETRY_COUNT=0

until docker compose exec db pg_isready -U tangerine > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Database failed to become ready after $MAX_RETRIES attempts"
        exit 1
    fi
    sleep 1
done

echo "✅ Database ready"
echo ""

# Run appropriate tests based on type
case "$TEST_TYPE" in
    smoke)
        echo "🚀 Running UI smoke tests (rendering only)..."
        echo ""
        docker compose exec admin pytest /app/tests/ui/ -v -m "ui and not e2e" \
            --tb=short \
            --color=yes \
            --no-cov
        ;;
    e2e)
        echo "🚀 Running end-to-end UI tests (full workflows)..."
        echo ""
        docker compose exec admin pytest /app/tests/ui/ -v -m e2e \
            --tb=short \
            --color=yes \
            --no-cov
        ;;
    all)
        echo "🚀 Running all UI tests..."
        echo ""
        docker compose exec admin pytest /app/tests/ui/ -v -m ui \
            --tb=short \
            --color=yes \
            --no-cov
        ;;
    *)
        echo "❌ Invalid test type: $TEST_TYPE"
        echo ""
        echo "Usage: $0 [smoke|e2e|all]"
        echo ""
        echo "Options:"
        echo "  smoke - Run only smoke tests (rendering verification)"
        echo "  e2e   - Run only end-to-end tests (full workflows with database)"
        echo "  all   - Run all UI tests (default)"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All UI regression tests passed!"
else
    echo "❌ Some UI regression tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
