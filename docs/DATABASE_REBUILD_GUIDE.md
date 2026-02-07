# Database Rebuild Guide

Complete guide for dropping and rebuilding the Tangerine database from schema files.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Rebuild](#quick-rebuild)
- [Manual Rebuild](#manual-rebuild)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Schema Structure](#schema-structure)
- [Dependency Order](#dependency-order)

---

## Prerequisites

### Required Environment Variables

The following environment variables must be set (typically via `.env` or `docker-compose.yml`):

```bash
POSTGRES_USER=postgres        # Database superuser
POSTGRES_PASSWORD=yourpass    # Database password
POSTGRES_DB=tangerine        # Database name
POSTGRES_HOST=localhost      # Database host (default: localhost)
POSTGRES_PORT=5432          # Database port (default: 5432)

# Additional users (for init.sh)
ETL_USER_PASSWORD=etl_pass
ADMIN_PASSWORD=admin_pass
```

### Required Services

- PostgreSQL 18+ running
- Docker and Docker Compose (for containerized rebuild)
- `psql` client installed
- Sufficient disk space for backups (if using `--backup`)

### File Structure

Ensure all schema files are present:

```
/opt/tangerine/
├── schema/
│   ├── init.sh                    # Master initialization script
│   ├── dba/
│   │   ├── schema.sql
│   │   ├── tables/               # 17 table definitions
│   │   ├── functions/            # 3 functions
│   │   ├── procedures/           # 5 procedures
│   │   ├── views/                # 2 views
│   │   ├── indexes/              # 6 indexes
│   │   ├── triggers/             # 2 triggers
│   │   └── data/                 # 8 seed data files
│   └── feeds/
│       └── *.sql                 # 8 feed table definitions
└── scripts/
    ├── drop_database.sh          # Database cleanup script
    └── rebuild_database.sh       # Master rebuild orchestrator
```

---

## Quick Rebuild

### Full Rebuild (Drop + Recreate)

```bash
# Interactive rebuild with prompts
./scripts/rebuild_database.sh

# Auto-confirm without prompts
./scripts/rebuild_database.sh --yes

# With backup before rebuild
./scripts/rebuild_database.sh --backup --yes
```

### Verify Only (No Changes)

```bash
# Check database state without rebuilding
./scripts/rebuild_database.sh --verify-only
```

### Preview Changes (Dry Run)

```bash
# See what would be done without executing
./scripts/rebuild_database.sh --dry-run
```

---

## Manual Rebuild

For troubleshooting or step-by-step execution:

### Step 1: Drop Existing Database

```bash
# Preview what will be dropped
./scripts/drop_database.sh --dry-run

# Drop all objects with confirmation
./scripts/drop_database.sh --confirm

# Drop with backup first
./scripts/drop_database.sh --backup --confirm
```

**What gets dropped:**
1. Views (depend on tables)
2. Event triggers (highest level)
3. Table triggers
4. Procedures
5. Functions
6. Feeds tables (no dependencies)
7. DBA tables (reverse dependency order)
8. Schemas (`dba`, `feeds`)
9. Roles (`app_rw`, `app_ro`, `etl_user`)

### Step 2: Initialize Schema

**Option A: Using Docker Compose**

```bash
# Run init.sh inside admin container
docker compose exec admin bash -c "cd /app/schema && ./init.sh"
```

**Option B: Direct Execution**

```bash
# From host (requires psql and correct POSTGRES_* env vars)
cd /opt/tangerine/schema
./init.sh
```

**What gets created:**
1. Roles (`etl_user`, `admin`, `app_rw`, `app_ro`)
2. DBA schema and tables (17 tables)
3. DBA functions (3), procedures (5), views (2)
4. DBA indexes (6) and triggers (2)
5. DBA seed data (dataset types, statuses, strategies, holidays, calendar days)
6. Feeds schema and tables (8 tables)
7. Permissions (`GRANT` statements)

### Step 3: Verify Rebuild

```bash
# Check schema object counts
psql -U postgres -d tangerine -c "
SELECT
    schemaname,
    COUNT(*) as table_count
FROM pg_tables
WHERE schemaname IN ('dba', 'feeds')
GROUP BY schemaname
ORDER BY schemaname;
"
```

Expected output:
```
 schemaname | table_count
------------+-------------
 dba        |          17
 feeds      |           8
```

---

## Verification

### Automated Verification

The `rebuild_database.sh` script includes built-in verification:

```bash
./scripts/rebuild_database.sh --verify-only
```

### Manual Verification Checklist

#### 1. Schema Existence

```sql
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('dba', 'feeds')
ORDER BY schema_name;
```

Expected: 2 rows (`dba`, `feeds`)

#### 2. Table Counts

```sql
SELECT
    schemaname,
    COUNT(*) as table_count
FROM pg_tables
WHERE schemaname IN ('dba', 'feeds')
GROUP BY schemaname;
```

Expected:
- `dba`: 17 tables
- `feeds`: 8 tables

#### 3. Functions

```sql
SELECT
    routine_schema,
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_schema = 'dba'
ORDER BY routine_type, routine_name;
```

Expected:
- 3 functions: `fenforcesingleactivedataset`, `f_dataset_iu`, `flogddlchanges`
- 5 procedures: `pimportconfig_iu`, `pinboxconfig_iu`, `ppubsub_iu`, `preportmanager_iu`, `pscheduler_iu`

#### 4. Views

```sql
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'dba'
ORDER BY table_name;
```

Expected: `vdataset`, `vregressiontest_summary`

#### 5. Reference Data

```sql
-- Dataset types (should have NewYorkFed types)
SELECT COUNT(*) FROM dba.tdatasettype;
-- Expected: 15 rows

-- Data statuses
SELECT COUNT(*) FROM dba.tdatastatus;
-- Expected: 6 rows

-- Import strategies
SELECT COUNT(*) FROM dba.timportstrategy;
-- Expected: 3 rows

-- Holidays
SELECT COUNT(*) FROM dba.tholidays;
-- Expected: 24 rows (3 years of US federal holidays)

-- Calendar days
SELECT COUNT(*) FROM dba.tcalendardays;
-- Expected: 3653 rows (10 years: 2020-2030)
```

#### 6. Triggers

```sql
-- Table triggers
SELECT
    trigger_schema,
    trigger_name,
    event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'dba';

-- Event triggers
SELECT evtname, evtevent
FROM pg_event_trigger;
```

Expected:
- 1 table trigger: `ttriggerenforcesingleactivedataset` on `tdataset`
- 1 event trigger: `logddl_event_trigger` on `ddl_command_end`

#### 7. Permissions

```sql
-- Check role existence
SELECT rolname FROM pg_roles
WHERE rolname IN ('etl_user', 'admin', 'app_rw', 'app_ro')
ORDER BY rolname;
```

Expected: 4 rows

#### 8. Smoke Test - Insert Record

```sql
-- Test insert into tdataset
INSERT INTO dba.tdataset (datasettypeid, datasetdate, filename, recordcount, datastatusid)
VALUES (1, CURRENT_DATE, 'smoke_test.csv', 0, 1)
RETURNING datasetid;

-- Verify trigger enforces single active dataset
UPDATE dba.tdataset SET isactive = TRUE WHERE datasetid = <returned_id>;

-- Clean up
DELETE FROM dba.tdataset WHERE datasetid = <returned_id>;
```

---

## Troubleshooting

### Common Errors

#### Error: "POSTGRES_USER not set"

**Cause:** Environment variables not loaded

**Solution:**
```bash
# Load from .env file
export $(cat .env | xargs)

# Or set manually
export POSTGRES_USER=postgres
export POSTGRES_DB=tangerine
export POSTGRES_PASSWORD=yourpass
```

#### Error: "cannot connect to database"

**Cause:** PostgreSQL not running or wrong connection parameters

**Solution:**
```bash
# Check if PostgreSQL is running
docker compose ps

# Start PostgreSQL
docker compose up -d db

# Test connection
psql -U postgres -d tangerine -c "SELECT 1;"
```

#### Error: "file not found: /app/schema/..."

**Cause:** Running outside Docker but paths expect Docker mount

**Solution:**
```bash
# Run inside Docker
docker compose exec admin bash
cd /app/schema
./init.sh

# Or update init.sh to use relative paths
```

#### Error: "relation does not exist"

**Cause:** Schema not fully initialized or partial rebuild

**Solution:**
```bash
# Drop everything and start fresh
./scripts/drop_database.sh --confirm
./scripts/rebuild_database.sh --yes
```

#### Error: "tholidays_inserts.sql not found"

**Cause:** Missing seed data file (should be resolved)

**Solution:**
```bash
# Verify file exists
ls -la /opt/tangerine/schema/dba/data/tholidays_inserts.sql

# If missing, recreate (see implementation plan)
```

#### Error: "newyorkfed_pd_statistics.sql not found"

**Cause:** Old reference in init.sh (should be resolved)

**Solution:**
```bash
# Verify init.sh has been fixed (lines 74-75 removed)
grep -n "pd_statistics" /opt/tangerine/schema/init.sh
# Should return no results
```

### Debugging Tips

#### Enable Verbose Output

```bash
# Set verbose psql output in init.sh
export PSQL="psql -U $POSTGRES_USER -d $POSTGRES_DB -v ON_ERROR_STOP=1 -a"
```

#### Check Logs

```bash
# Docker logs for database errors
docker compose logs db

# Admin container logs
docker compose logs admin
```

#### Validate All Schema Files

```bash
# Check all SQL files for syntax errors (dry run)
cd /opt/tangerine/schema
for file in $(find . -name "*.sql"); do
    echo "Checking: $file"
    psql -U postgres -d tangerine --single-transaction --set ON_ERROR_STOP=1 --dry-run -f "$file" 2>&1 | grep -i error
done
```

#### Verify File References

```bash
# Check that all files referenced in init.sh exist
grep -oP '(?<=-f /app/schema/)[^ ]+' /opt/tangerine/schema/init.sh | while read file; do
    if [ ! -f "/opt/tangerine/schema/$file" ]; then
        echo "MISSING: $file"
    fi
done
```

---

## Schema Structure

### DBA Schema

Core administrative and metadata tables:

| Table | Purpose | Dependencies |
|-------|---------|--------------|
| `tdatasettype` | Dataset type registry | None |
| `tdatasource` | Data source registry | None |
| `tdatastatus` | Dataset status codes | None |
| `timportstrategy` | Import strategy configs | None |
| `tholidays` | Holiday calendar | None |
| `tdataset` | Dataset metadata | `tdatasettype`, `tdatasource`, `tdatastatus` |
| `tcalendardays` | Business day calendar | `tholidays` |
| `timportconfig` | Import job configs | `tdatasettype`, `timportstrategy` |
| `tscheduler` | Job scheduler configs | `timportconfig` |
| `tinboxconfig` | Inbox processor configs | `timportconfig` |
| `treportmanager` | Report generator configs | None |
| `tregressiontest` | Regression test results | `tdataset` |
| `tlogentry` | ETL job logs | None |
| `tddllogs` | DDL change audit log | None |
| `tpubsub_events` | PubSub event definitions | None |
| `tpubsub_subscribers` | PubSub subscriptions | `tpubsub_events` |

### Feeds Schema

External data source tables:

| Table | Purpose | Source |
|-------|---------|--------|
| `newyorkfed_reference_rates` | Reference rate data | NY Fed |
| `newyorkfed_soma_holdings` | SOMA holdings data | NY Fed |
| `newyorkfed_repo_operations` | Repo operation data | NY Fed |
| `newyorkfed_agency_mbs` | Agency MBS data | NY Fed |
| `newyorkfed_fx_swaps` | FX swap data | NY Fed |
| `newyorkfed_guide_sheets` | Guide sheet data | NY Fed |
| `newyorkfed_securities_lending` | Securities lending data | NY Fed |
| `newyorkfed_treasury_operations` | Treasury operation data | NY Fed |

---

## Dependency Order

### Why Order Matters

SQL schema objects have dependencies:
- Tables with foreign keys depend on referenced tables
- Views depend on underlying tables
- Triggers depend on functions
- Functions may depend on tables/views

**Creation Order:** Dependencies first (bottom-up)
**Deletion Order:** Dependents first (top-down)

### Creation Dependency Graph

```
Roles
  ↓
Schemas (dba, feeds)
  ↓
Base Tables (no FKs)
  ├─ tdatasettype
  ├─ tdatasource
  ├─ tdatastatus
  ├─ timportstrategy
  ├─ tholidays
  └─ tpubsub_events
  ↓
Dependent Tables (with FKs)
  ├─ tdataset (→ tdatasettype, tdatasource, tdatastatus)
  ├─ tcalendardays (→ tholidays)
  ├─ timportconfig (→ tdatasettype, timportstrategy)
  ├─ tscheduler (→ timportconfig)
  ├─ tinboxconfig (→ timportconfig)
  ├─ tregressiontest (→ tdataset)
  └─ tpubsub_subscribers (→ tpubsub_events)
  ↓
Independent Tables
  ├─ tlogentry
  ├─ tddllogs
  └─ treportmanager
  ↓
Functions
  ├─ fenforcesingleactivedataset
  ├─ f_dataset_iu
  └─ flogddlchanges
  ↓
Procedures
  ├─ pimportconfig_iu
  ├─ pscheduler_iu
  ├─ pinboxconfig_iu
  ├─ preportmanager_iu
  └─ ppubsub_iu
  ↓
Indexes
  ↓
Triggers (use functions)
  ├─ ttriggerenforcesingleactivedataset (table trigger)
  └─ logddl_event_trigger (event trigger)
  ↓
Seed Data
  ↓
Views (use tables)
  ├─ vdataset
  └─ vregressiontest_summary
  ↓
Feeds Tables (independent)
  └─ newyorkfed_* (8 tables)
  ↓
Permissions (GRANT statements)
```

### Deletion Dependency Graph

Reverse of creation order:

```
Permissions (revoked automatically with objects)
  ↓
Views
  ↓
Event Triggers
  ↓
Table Triggers
  ↓
Procedures
  ↓
Functions
  ↓
Feeds Tables
  ↓
DBA Tables (reverse FK order)
  ├─ tpubsub_subscribers
  ├─ tregressiontest
  ├─ tinboxconfig
  ├─ tscheduler
  ├─ timportconfig
  ├─ tdataset
  ├─ tcalendardays
  └─ base tables
  ↓
Schemas
  ↓
Roles
```

---

## Best Practices

### 1. Always Backup Before Rebuild

```bash
./scripts/rebuild_database.sh --backup --yes
```

### 2. Use Dry Run First

```bash
# Preview changes
./scripts/drop_database.sh --dry-run
./scripts/rebuild_database.sh --dry-run
```

### 3. Verify After Rebuild

```bash
# Run verification
./scripts/rebuild_database.sh --verify-only
```

### 4. Keep Schema Files in Sync

- Never manually create database objects
- Always update schema files first
- Use migrations for production changes
- Test rebuild after schema changes

### 5. Document Schema Changes

- Update this guide when adding new objects
- Maintain dependency graph
- Update expected counts in verification

---

## Quick Reference

### Environment Setup

```bash
# Load environment
export $(cat .env | xargs)

# Or use Docker Compose
docker compose up -d
```

### Common Commands

```bash
# Full rebuild
./scripts/rebuild_database.sh --yes

# Verify state
./scripts/rebuild_database.sh --verify-only

# Drop only
./scripts/drop_database.sh --confirm

# Initialize only
cd schema && ./init.sh
```

### Database Connection

```bash
# From host
psql -U postgres -d tangerine

# From Docker
docker compose exec db psql -U postgres -d tangerine
```

### Quick Health Check

```sql
-- Table counts
SELECT schemaname, COUNT(*)
FROM pg_tables
WHERE schemaname IN ('dba', 'feeds')
GROUP BY schemaname;

-- Reference data
SELECT 'dataset_types' as table, COUNT(*) FROM dba.tdatasettype
UNION ALL
SELECT 'data_statuses', COUNT(*) FROM dba.tdatastatus
UNION ALL
SELECT 'import_strategies', COUNT(*) FROM dba.timportstrategy
UNION ALL
SELECT 'holidays', COUNT(*) FROM dba.tholidays;
```

---

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review schema files in `/opt/tangerine/schema/`
- Check Docker logs: `docker compose logs db`
- Consult main `README.md` for project context
