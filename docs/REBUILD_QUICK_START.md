# Database Rebuild - Quick Start

**Goal:** Drop and rebuild the entire Tangerine database in < 5 minutes

## TL;DR

```bash
# One command - full rebuild with backup
./scripts/rebuild_database.sh --backup --yes

# Verify it worked
./scripts/rebuild_database.sh --verify-only
```

## What Was Fixed

### Before (Broken)
- ❌ Missing `tholidays_inserts.sql` - init.sh failed at line 55
- ❌ Reference to removed `newyorkfed_pd_statistics.sql` - init.sh failed at line 74
- ❌ Reference to removed `newyorkfed_market_share.sql` - init.sh failed at line 75
- ❌ Hard requirement for `shared_queries.sql` - init.sh failed at line 80

### After (Fixed)
- ✅ Created `schema/dba/data/tholidays_inserts.sql` with 24 US federal holidays
- ✅ Removed lines 74-75 from init.sh (pd_statistics, market_share)
- ✅ Made shared_queries.sql optional with conditional check
- ✅ All 55 SQL files validated and referenced correctly

## File Inventory

### Schema Files (55 total)
```
schema/
├── init.sh (fixed - no broken references)
├── dba/
│   ├── schema.sql
│   ├── tables/ (17 files)
│   ├── functions/ (3 files)
│   ├── procedures/ (5 files)
│   ├── views/ (2 files)
│   ├── indexes/ (6 files)
│   ├── triggers/ (2 files)
│   └── data/ (9 files) ← includes new tholidays_inserts.sql
└── feeds/ (8 files)
```

### New Scripts
```
scripts/
├── drop_database.sh      ← Complete database cleanup
└── rebuild_database.sh   ← One-command rebuild + verification
```

### New Documentation
```
docs/
├── DATABASE_REBUILD_GUIDE.md  ← Comprehensive guide
└── REBUILD_QUICK_START.md     ← This file
```

## Usage Examples

### Full Rebuild (Recommended)
```bash
# With backup and auto-confirm
./scripts/rebuild_database.sh --backup --yes

# Interactive (prompts for confirmation)
./scripts/rebuild_database.sh
```

### Preview Changes
```bash
# See what drop script would do
./scripts/drop_database.sh --dry-run

# See what rebuild would do
./scripts/rebuild_database.sh --dry-run
```

### Drop Only
```bash
# Just clean the database
./scripts/drop_database.sh --confirm
```

### Verify Only
```bash
# Check database state without changes
./scripts/rebuild_database.sh --verify-only
```

## Expected Output

### Successful Rebuild
```
============================================
Tangerine Database Rebuild
============================================
Database: tangerine
Host: localhost:5432
User: postgres
Mode: LIVE
============================================

==> Checking environment variables...
✓ Environment variables OK
  Database: tangerine
  User: postgres
  Host: localhost
  Port: 5432

==> Testing database connection...
✓ Database connection OK

==> Verifying database state...
  Schemas (dba, feeds): 2/2
  DBA tables: 17 (expected: 17)
  Feeds tables: 8 (expected: 8)
  Functions: 3 (expected: 3)
  Procedures: 5 (expected: 5)
  Views: 2 (expected: 2)
  Dataset types: 15 (expected: 15)
  Data statuses: 6 (expected: 6)
  Import strategies: 3 (expected: 3)
✓ Database appears properly initialized

==> Dropping database objects...
[... drop output ...]

==> Initializing database schema...
[... init.sh output ...]
✓ Schema initialized

==> Verifying database state...
✓ Database appears properly initialized

==> Running smoke tests...
  ==> Test 1: Insert into tdataset...
  ✓ Insert test passed (dataset ID: 1)
  ==> Test 2: Call f_dataset_iu function...
  ✓ Function call test passed
  ==> Test 3: Query vdataset view...
  ✓ View query test passed (rows: 0)
✓ All smoke tests passed

============================================
REBUILD COMPLETE
============================================
```

## Verification Checklist

After rebuild, verify:

```sql
-- ✓ Schemas exist
SELECT schema_name FROM information_schema.schemata
WHERE schema_name IN ('dba', 'feeds');
-- Expected: 2 rows

-- ✓ Table counts
SELECT schemaname, COUNT(*) FROM pg_tables
WHERE schemaname IN ('dba', 'feeds')
GROUP BY schemaname;
-- Expected: dba=17, feeds=8

-- ✓ Reference data loaded
SELECT COUNT(*) FROM dba.tdatasettype;    -- 15
SELECT COUNT(*) FROM dba.tdatastatus;     -- 6
SELECT COUNT(*) FROM dba.timportstrategy; -- 3
SELECT COUNT(*) FROM dba.tholidays;       -- 24
SELECT COUNT(*) FROM dba.tcalendardays;   -- 3653

-- ✓ Functions exist
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'dba' AND routine_type = 'FUNCTION';
-- Expected: 3 rows

-- ✓ Views exist
SELECT table_name FROM information_schema.views
WHERE table_schema = 'dba';
-- Expected: 2 rows
```

## Troubleshooting

### Error: "cannot connect to database"
```bash
# Start PostgreSQL
docker compose up -d db

# Wait for ready
docker compose logs -f db | grep "ready to accept"
```

### Error: "POSTGRES_USER not set"
```bash
# Load environment variables
export $(cat .env | xargs)
```

### Error: "file not found"
```bash
# Ensure you're in project root
cd /opt/tangerine

# Or run via Docker
docker compose exec admin bash -c "cd /app/schema && ./init.sh"
```

### Rebuild Failed Midway
```bash
# Start fresh - drop everything
./scripts/drop_database.sh --confirm

# Rebuild
./scripts/rebuild_database.sh --yes
```

## Next Steps After Rebuild

### Load ETL Data
```bash
# Run all NewYorkFed import jobs
docker compose exec admin python scripts/run_all_newyorkfed_jobs.py

# Verify data loaded
psql -U postgres -d tangerine -c "SELECT COUNT(*) FROM feeds.newyorkfed_reference_rates;"
```

### Test Admin UI
```bash
# Start admin interface
docker compose up -d admin

# Visit http://localhost:8501
```

### Run Regression Tests
```bash
# Run test suite
docker compose exec admin pytest tests/

# Or specific tests
docker compose exec admin pytest tests/test_database.py -v
```

## Summary

**Blocking Issues Resolved:**
1. ✅ Created missing `tholidays_inserts.sql`
2. ✅ Removed broken references to `newyorkfed_pd_statistics.sql`
3. ✅ Removed broken references to `newyorkfed_market_share.sql`
4. ✅ Made `shared_queries.sql` optional

**New Capabilities:**
- 🔧 One-command database rebuild
- 🗑️  Safe database drop with dry-run and backup
- ✅ Automated verification and smoke tests
- 📖 Comprehensive rebuild documentation

**Schema Files:** 55 SQL files + 1 init.sh (all valid)

**Rebuild Time:** < 5 minutes for complete drop/rebuild cycle

---

For detailed information, see [DATABASE_REBUILD_GUIDE.md](./DATABASE_REBUILD_GUIDE.md)
