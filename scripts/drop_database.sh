#!/bin/bash
#
# drop_database.sh - Complete database cleanup script
#
# Drops all Tangerine database objects in reverse dependency order
# for a clean rebuild. This script is designed to be safe and requires
# explicit confirmation.
#
# Usage:
#   ./drop_database.sh --confirm          # Drop all database objects
#   ./drop_database.sh --dry-run          # Show what would be dropped
#   ./drop_database.sh --backup           # Backup before dropping
#

set -e  # Exit on any error

# Default flags
DRY_RUN=false
CONFIRM=false
BACKUP=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        --confirm)
            CONFIRM=true
            ;;
        --backup)
            BACKUP=true
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --confirm     Actually drop the database (required for execution)"
            echo "  --dry-run     Show what would be dropped without executing"
            echo "  --backup      Create backup before dropping"
            echo "  --help        Show this help message"
            echo ""
            echo "Example:"
            echo "  $0 --dry-run              # Preview what will be dropped"
            echo "  $0 --backup --confirm     # Backup then drop"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required flags
if [ "$DRY_RUN" = false ] && [ "$CONFIRM" = false ]; then
    echo "ERROR: Must specify either --dry-run or --confirm"
    echo "Use --help for usage information"
    exit 1
fi

# Database connection settings (from environment or defaults)
export PGHOST="${POSTGRES_HOST:-localhost}"
export PGPORT="${POSTGRES_PORT:-5432}"
export PGDATABASE="${POSTGRES_DB:-tangerine}"
export PGUSER="${POSTGRES_USER:-postgres}"
export PGPASSWORD="${POSTGRES_PASSWORD}"

PSQL="psql -U $PGUSER -d $PGDATABASE -h $PGHOST -p $PGPORT"

echo "============================================"
echo "Tangerine Database Drop Script"
echo "============================================"
echo "Database: $PGDATABASE"
echo "Host: $PGHOST:$PGPORT"
echo "User: $PGUSER"
echo "Mode: $([ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "LIVE")"
echo "============================================"
echo ""

# Backup if requested
if [ "$BACKUP" = true ] && [ "$DRY_RUN" = false ]; then
    BACKUP_FILE="backup_${PGDATABASE}_$(date +%Y%m%d_%H%M%S).sql"
    echo "Creating backup: $BACKUP_FILE"
    pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" > "$BACKUP_FILE"
    echo "Backup created successfully: $BACKUP_FILE"
    echo ""
fi

# Function to execute SQL or just print for dry-run
execute_sql() {
    local sql="$1"
    local description="$2"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] $description"
        echo "  SQL: $sql"
    else
        echo "Executing: $description"
        $PSQL -c "$sql" || echo "  Warning: Command may have failed (object might not exist)"
    fi
}

echo "Step 1: Dropping views (depend on tables)..."
execute_sql "DROP VIEW IF EXISTS dba.vdataset CASCADE;" "Drop vdataset view"
execute_sql "DROP VIEW IF EXISTS dba.vregressiontest_summary CASCADE;" "Drop vregressiontest_summary view"
echo ""

echo "Step 2: Dropping event triggers (highest level)..."
execute_sql "DROP EVENT TRIGGER IF EXISTS logddl_event_trigger CASCADE;" "Drop DDL logging event trigger"
echo ""

echo "Step 3: Dropping table triggers..."
execute_sql "DROP TRIGGER IF EXISTS ttriggerenforcesingleactivedataset ON dba.tdataset CASCADE;" "Drop enforce single active dataset trigger"
echo ""

echo "Step 4: Dropping procedures..."
execute_sql "DROP PROCEDURE IF EXISTS dba.pimportconfig_iu CASCADE;" "Drop import config procedure"
execute_sql "DROP PROCEDURE IF EXISTS dba.pscheduler_iu CASCADE;" "Drop scheduler procedure"
execute_sql "DROP PROCEDURE IF EXISTS dba.pinboxconfig_iu CASCADE;" "Drop inbox config procedure"
execute_sql "DROP PROCEDURE IF EXISTS dba.preportmanager_iu CASCADE;" "Drop report manager procedure"
execute_sql "DROP PROCEDURE IF EXISTS dba.ppubsub_iu CASCADE;" "Drop pubsub procedure"
echo ""

echo "Step 5: Dropping functions..."
execute_sql "DROP FUNCTION IF EXISTS dba.fenforcesingleactivedataset CASCADE;" "Drop enforce single active dataset function"
execute_sql "DROP FUNCTION IF EXISTS dba.f_dataset_iu CASCADE;" "Drop dataset insert/update function"
execute_sql "DROP FUNCTION IF EXISTS dba.flogddlchanges CASCADE;" "Drop DDL logging function"
echo ""

echo "Step 6: Dropping feeds tables (no dependencies on dba tables)..."
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_reference_rates CASCADE;" "Drop reference rates table"
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_soma_holdings CASCADE;" "Drop SOMA holdings table"
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_repo_operations CASCADE;" "Drop repo operations table"
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_agency_mbs CASCADE;" "Drop agency MBS table"
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_fx_swaps CASCADE;" "Drop FX swaps table"
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_guide_sheets CASCADE;" "Drop guide sheets table"
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_securities_lending CASCADE;" "Drop securities lending table"
execute_sql "DROP TABLE IF EXISTS feeds.newyorkfed_treasury_operations CASCADE;" "Drop treasury operations table"
echo ""

echo "Step 7: Dropping dba tables (in reverse dependency order)..."
# Tables with FK dependencies must be dropped before referenced tables
execute_sql "DROP TABLE IF EXISTS dba.tpubsub_subscribers CASCADE;" "Drop pubsub subscribers table"
execute_sql "DROP TABLE IF EXISTS dba.tpubsub_events CASCADE;" "Drop pubsub events table"
execute_sql "DROP TABLE IF EXISTS dba.treportmanager CASCADE;" "Drop report manager table"
execute_sql "DROP TABLE IF EXISTS dba.tinboxconfig CASCADE;" "Drop inbox config table"
execute_sql "DROP TABLE IF EXISTS dba.tscheduler CASCADE;" "Drop scheduler table"
execute_sql "DROP TABLE IF EXISTS dba.tregressiontest CASCADE;" "Drop regression test table"
execute_sql "DROP TABLE IF EXISTS dba.timportconfig CASCADE;" "Drop import config table"
execute_sql "DROP TABLE IF EXISTS dba.tdataset CASCADE;" "Drop dataset table (has FKs)"
execute_sql "DROP TABLE IF EXISTS dba.tlogentry CASCADE;" "Drop log entry table"
execute_sql "DROP TABLE IF EXISTS dba.tddllogs CASCADE;" "Drop DDL logs table"
execute_sql "DROP TABLE IF EXISTS dba.tcalendardays CASCADE;" "Drop calendar days table"
execute_sql "DROP TABLE IF EXISTS dba.tholidays CASCADE;" "Drop holidays table"
execute_sql "DROP TABLE IF EXISTS dba.timportstrategy CASCADE;" "Drop import strategy table"
execute_sql "DROP TABLE IF EXISTS dba.tdatastatus CASCADE;" "Drop data status table"
execute_sql "DROP TABLE IF EXISTS dba.tdatasource CASCADE;" "Drop data source table"
execute_sql "DROP TABLE IF EXISTS dba.tdatasettype CASCADE;" "Drop dataset type table"
echo ""

echo "Step 8: Dropping schemas..."
execute_sql "DROP SCHEMA IF EXISTS feeds CASCADE;" "Drop feeds schema"
execute_sql "DROP SCHEMA IF EXISTS dba CASCADE;" "Drop dba schema"
echo ""

echo "Step 9: Dropping roles (except owner)..."
execute_sql "DROP ROLE IF EXISTS app_rw;" "Drop app_rw role"
execute_sql "DROP ROLE IF EXISTS app_ro;" "Drop app_ro role"
execute_sql "DROP ROLE IF EXISTS etl_user;" "Drop etl_user role"
# Note: Not dropping 'admin' role as it may be the database owner
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "============================================"
    echo "DRY RUN COMPLETE"
    echo "No changes were made to the database"
    echo "Run with --confirm to actually drop objects"
    echo "============================================"
else
    echo "============================================"
    echo "DATABASE DROP COMPLETE"
    echo "All Tangerine objects have been removed"
    echo "Run init.sh or rebuild_database.sh to recreate"
    echo "============================================"
fi
