#!/bin/bash
#
# rebuild_database.sh - Complete database rebuild orchestrator
#
# Provides a single command to drop and rebuild the entire Tangerine database
# from schema files. This ensures reproducible database setup for development
# and testing.
#
# Usage:
#   ./rebuild_database.sh                 # Full rebuild with prompts
#   ./rebuild_database.sh --backup        # Backup before rebuild
#   ./rebuild_database.sh --skip-drop     # Skip drop step (fresh database)
#   ./rebuild_database.sh --verify-only   # Only verify database state
#   ./rebuild_database.sh --dry-run       # Show what would be done
#

set -e  # Exit on any error

# Script directory (for relative paths)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Default flags
DRY_RUN=false
BACKUP=false
SKIP_DROP=false
VERIFY_ONLY=false
AUTO_CONFIRM=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --backup)
            BACKUP=true
            ;;
        --skip-drop)
            SKIP_DROP=true
            ;;
        --verify-only)
            VERIFY_ONLY=true
            ;;
        --yes|-y)
            AUTO_CONFIRM=true
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --backup        Create backup before rebuild"
            echo "  --skip-drop     Skip database drop step"
            echo "  --verify-only   Only verify database state (no rebuild)"
            echo "  --dry-run       Show what would be done without executing"
            echo "  --yes, -y       Auto-confirm (skip prompts)"
            echo "  --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Interactive full rebuild"
            echo "  $0 --backup --yes     # Backup and rebuild without prompts"
            echo "  $0 --verify-only      # Just check database state"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running inside Docker container
if [ -f /.dockerenv ]; then
    IN_DOCKER=true
    print_warning "Running inside Docker container"
else
    IN_DOCKER=false
fi

# Validate environment variables
check_env_vars() {
    print_step "Checking environment variables..."

    local missing=0

    if [ -z "$POSTGRES_USER" ]; then
        print_error "POSTGRES_USER not set"
        missing=1
    fi

    if [ -z "$POSTGRES_DB" ]; then
        print_error "POSTGRES_DB not set"
        missing=1
    fi

    if [ -z "$POSTGRES_PASSWORD" ]; then
        print_warning "POSTGRES_PASSWORD not set (may fail for remote databases)"
    fi

    if [ $missing -eq 1 ]; then
        print_error "Required environment variables missing"
        return 1
    fi

    print_success "Environment variables OK"
    echo "  Database: $POSTGRES_DB"
    echo "  User: $POSTGRES_USER"
    echo "  Host: ${POSTGRES_HOST:-localhost}"
    echo "  Port: ${POSTGRES_PORT:-5432}"
}

# Test database connection
test_connection() {
    print_step "Testing database connection..."

    local psql_cmd="psql -U $POSTGRES_USER -d postgres -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432}"

    if $psql_cmd -c "SELECT 1;" > /dev/null 2>&1; then
        print_success "Database connection OK"
        return 0
    else
        print_error "Cannot connect to database"
        return 1
    fi
}

# Verify database state
verify_database() {
    print_step "Verifying database state..."

    local psql_cmd="psql -U $POSTGRES_USER -d $POSTGRES_DB -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432}"

    # Check if database exists
    if ! psql -U $POSTGRES_USER -d postgres -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432} -lqt | cut -d \| -f 1 | grep -qw "$POSTGRES_DB"; then
        print_warning "Database '$POSTGRES_DB' does not exist"
        return 1
    fi

    # Count schemas
    local schema_count=$($psql_cmd -tAc "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name IN ('dba', 'feeds');")
    echo "  Schemas (dba, feeds): $schema_count/2"

    # Count tables
    local dba_tables=$($psql_cmd -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'dba';")
    local feeds_tables=$($psql_cmd -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'feeds';")
    echo "  DBA tables: $dba_tables (expected: 17)"
    echo "  Feeds tables: $feeds_tables (expected: 8)"

    # Count functions
    local func_count=$($psql_cmd -tAc "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'dba' AND p.prokind = 'f';")
    echo "  Functions: $func_count (expected: 3)"

    # Count procedures
    local proc_count=$($psql_cmd -tAc "SELECT COUNT(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = 'dba' AND p.prokind = 'p';")
    echo "  Procedures: $proc_count (expected: 5)"

    # Count views
    local view_count=$($psql_cmd -tAc "SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'dba';")
    echo "  Views: $view_count (expected: 2)"

    # Check reference data
    local dataset_types=$($psql_cmd -tAc "SELECT COUNT(*) FROM dba.tdatasettype;" 2>/dev/null || echo "0")
    local data_statuses=$($psql_cmd -tAc "SELECT COUNT(*) FROM dba.tdatastatus;" 2>/dev/null || echo "0")
    local import_strategies=$($psql_cmd -tAc "SELECT COUNT(*) FROM dba.timportstrategy;" 2>/dev/null || echo "0")
    echo "  Dataset types: $dataset_types (expected: 15)"
    echo "  Data statuses: $data_statuses (expected: 6)"
    echo "  Import strategies: $import_strategies (expected: 3)"

    # Determine if database is properly initialized
    if [ "$schema_count" -eq 2 ] && [ "$dba_tables" -ge 15 ] && [ "$feeds_tables" -ge 6 ]; then
        print_success "Database appears properly initialized"
        return 0
    else
        print_warning "Database exists but may not be fully initialized"
        return 1
    fi
}

# Drop database
drop_database() {
    print_step "Dropping database objects..."

    if [ "$DRY_RUN" = true ]; then
        "$SCRIPT_DIR/drop_database.sh" --dry-run
    else
        "$SCRIPT_DIR/drop_database.sh" --confirm
    fi
}

# Initialize schema
initialize_schema() {
    print_step "Initializing database schema..."

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN: Would run schema/init.sh"
        return 0
    fi

    if [ "$IN_DOCKER" = true ]; then
        # Already inside Docker, run init.sh directly
        cd "$PROJECT_DIR/schema" && ./init.sh
    else
        # Run init.sh inside Docker container
        docker compose exec -T admin bash -c "cd /app/schema && ./init.sh"
    fi

    print_success "Schema initialized"
}

# Run smoke tests
run_smoke_tests() {
    print_step "Running smoke tests..."

    local psql_cmd="psql -U $POSTGRES_USER -d $POSTGRES_DB -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432}"

    # Test 1: Can insert into tdataset
    print_step "  Test 1: Insert into tdataset..."
    local test_result=$($psql_cmd -tAc "
        INSERT INTO dba.tdataset (datasettypeid, datasetdate, filename, recordcount, datastatusid)
        VALUES (1, CURRENT_DATE, 'smoke_test.csv', 0, 1)
        RETURNING datasetid;
    " 2>&1)

    if [ $? -eq 0 ]; then
        print_success "  Insert test passed (dataset ID: $test_result)"
        # Clean up
        $psql_cmd -c "DELETE FROM dba.tdataset WHERE datasetid = $test_result;" > /dev/null
    else
        print_error "  Insert test failed: $test_result"
        return 1
    fi

    # Test 2: Call a function
    print_step "  Test 2: Call f_dataset_iu function..."
    local func_test=$($psql_cmd -tAc "SELECT dba.f_dataset_iu();" 2>&1)

    if [ $? -eq 0 ]; then
        print_success "  Function call test passed"
    else
        print_error "  Function call test failed: $func_test"
        return 1
    fi

    # Test 3: Query a view
    print_step "  Test 3: Query vdataset view..."
    local view_test=$($psql_cmd -tAc "SELECT COUNT(*) FROM dba.vdataset;" 2>&1)

    if [ $? -eq 0 ]; then
        print_success "  View query test passed (rows: $view_test)"
    else
        print_error "  View query test failed: $view_test"
        return 1
    fi

    print_success "All smoke tests passed"
}

# Main execution
main() {
    echo "============================================"
    echo "Tangerine Database Rebuild"
    echo "============================================"
    echo ""

    # Check environment
    check_env_vars || exit 1
    echo ""

    # Test connection
    test_connection || exit 1
    echo ""

    # Verify-only mode
    if [ "$VERIFY_ONLY" = true ]; then
        verify_database
        exit $?
    fi

    # Check current state
    if verify_database; then
        if [ "$SKIP_DROP" = false ] && [ "$AUTO_CONFIRM" = false ]; then
            print_warning "Database appears to be already initialized"
            read -p "Continue with rebuild? This will DROP all data (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Rebuild cancelled"
                exit 0
            fi
        fi
    fi
    echo ""

    # Backup if requested
    if [ "$BACKUP" = true ] && [ "$DRY_RUN" = false ]; then
        print_step "Creating backup..."
        BACKUP_FILE="$PROJECT_DIR/backups/backup_${POSTGRES_DB}_$(date +%Y%m%d_%H%M%S).sql"
        mkdir -p "$PROJECT_DIR/backups"
        pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432} > "$BACKUP_FILE"
        print_success "Backup created: $BACKUP_FILE"
        echo ""
    fi

    # Drop database (unless skipped)
    if [ "$SKIP_DROP" = false ]; then
        drop_database
        echo ""
    fi

    # Initialize schema
    initialize_schema
    echo ""

    # Verify rebuild
    if [ "$DRY_RUN" = false ]; then
        verify_database
        echo ""

        # Run smoke tests
        run_smoke_tests
        echo ""
    fi

    echo "============================================"
    if [ "$DRY_RUN" = true ]; then
        echo "DRY RUN COMPLETE"
    else
        echo "REBUILD COMPLETE"
    fi
    echo "============================================"
}

# Run main
main
