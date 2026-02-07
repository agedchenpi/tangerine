# Drop Docker Volume and Rebuild Database from Scratch

## Context

We've created database rebuild scripts:
- ✅ `scripts/drop_database.sh` - Database cleanup
- ✅ `scripts/rebuild_database.sh` - Rebuild orchestrator
- ✅ `schema/init.sh` - Schema initialization (fixed, no broken references)
- ✅ `schema/dba/data/tholidays_inserts.sql` - Holiday data (created)

But we only tested incremental rebuild (IF NOT EXISTS). User wants to test a **complete fresh start** by dropping the Docker volume and rebuilding from scratch.

## Goal

1. Verify rebuild scripts are ready
2. Provide simple commands to drop Docker volume and start fresh
3. Verify clean rebuild works

## Plan

### Step 1: Verify Rebuild Scripts Are Ready

**Files to check:**
- `schema/init.sh` - Should have no references to pd_statistics, market_share
- `schema/dba/data/tholidays_inserts.sql` - Should exist
- All SQL files referenced in init.sh should exist

**Verification:**
```bash
# Check no broken references in init.sh
grep -n "pd_statistics\|market_share" schema/init.sh
# Expected: No output

# Check tholidays file exists
ls -lh schema/dba/data/tholidays_inserts.sql
# Expected: File exists

# Count SQL files
find schema -name "*.sql" | wc -l
# Expected: 55 files
```

### Step 2: Drop Docker Volume and Recreate Database

**User commands:**
```bash
# Stop containers
docker compose down

# Remove the database volume (DESTRUCTIVE!)
docker volume rm tangerine_db_data

# Start fresh with clean database
docker compose up -d db

# Wait for database to be ready
docker compose logs -f db | grep "ready to accept"
# Press Ctrl+C when you see "ready"

# Run init.sh to create all objects
docker compose exec -T db bash /app/schema/init.sh
```

### Step 3: Verify Clean Rebuild

**User commands:**
```bash
# Check schemas exist
docker compose exec db psql -U tangerine_admin -d tangerine_db -c "\dn"
# Expected: dba, feeds schemas

# Check table counts
docker compose exec db psql -U tangerine_admin -d tangerine_db -c "
SELECT schemaname, COUNT(*)
FROM pg_tables
WHERE schemaname IN ('dba', 'feeds')
GROUP BY schemaname;"
# Expected: dba=16, feeds=9

# Check reference data loaded
docker compose exec db psql -U tangerine_admin -d tangerine_db -c "
SELECT COUNT(*) FROM dba.tholidays;"
# Expected: 24 rows
```

### Step 4: Restart All Services

```bash
# Start all services
docker compose up -d

# Check all services healthy
docker compose ps
# Expected: All services "Up" and "healthy"
```

## Success Criteria

- ✅ Database volume dropped and recreated
- ✅ init.sh runs without errors
- ✅ All schemas, tables, functions created
- ✅ Reference data loaded (including 24 holidays)
- ✅ All services running and healthy

## Commands Summary (Copy-Paste)

```bash
# Full fresh rebuild
docker compose down
docker volume rm tangerine_db_data
docker compose up -d db
sleep 10  # Wait for db ready
docker compose exec -T db bash /app/schema/init.sh
docker compose up -d
docker compose ps
```
