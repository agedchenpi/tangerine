# NewYorkFed Schema Organization

The NewYorkFed Markets API integration schema files are now properly organized following Tangerine's schema management patterns.

## File Structure

```
schema/
├── init.sh                                          # Updated to source NewYorkFed files
├── dba/
│   ├── tables/
│   │   └── timportconfig.sql                       # Updated with API columns
│   └── data/
│       ├── newyorkfed_reference_data.sql           # Data source + dataset types
│       └── newyorkfed_scheduler_jobs.sql           # Scheduler job configurations
└── feeds/
    ├── newyorkfed_reference_rates.sql              # SOFR, EFFR, OBFR, TGCR, BGCR
    ├── newyorkfed_soma_holdings.sql                # SOMA holdings
    └── newyorkfed_repo_operations.sql              # Repo/reverse repo operations
```

## Changes Made

### 1. Updated Base Schema

**File**: `schema/dba/tables/timportconfig.sql`

Added 11 API-specific columns to the base `timportconfig` table:
- `import_mode` - 'file' or 'api'
- `api_base_url` - Base URL for API
- `api_endpoint_path` - Endpoint path
- `api_http_method` - HTTP method (GET, POST, etc.)
- `api_response_format` - Response format (json, xml, csv)
- `api_query_params` - Query parameters (JSONB)
- `api_request_headers` - Custom headers (JSONB)
- `api_auth_type` - Auth type (none, api_key, oauth, bearer)
- `api_auth_credentials` - Auth credentials (JSONB)
- `api_rate_limit_rpm` - Rate limit
- `api_response_root_path` - JSON extraction path

Updated constraints:
- `valid_directories` - Modified to allow API imports (no directories required)
- `valid_api_config` - Ensures API imports have base_url and endpoint_path

All columns are nullable for backward compatibility with existing file-based imports.

### 2. Reference Data

**File**: `schema/dba/data/newyorkfed_reference_data.sql`

Inserts into:
- `dba.tdatasource` - NewYorkFed data source
- `dba.tdatasettype` - 10 dataset types:
  - ReferenceRates
  - AgencyMBS
  - FXSwaps
  - GuideSheets
  - PDStatistics
  - MarketShare
  - RepoOperations
  - SecuritiesLending
  - SOMAHoldings
  - TreasuryOperations

### 3. Scheduler Jobs

**File**: `schema/dba/data/newyorkfed_scheduler_jobs.sql`

Configures 11 scheduled jobs in `dba.tscheduler`:
- 4 active jobs (ReferenceRates, Repo, ReverseRepo, SOMA)
- 7 inactive stub jobs (to be activated after implementation)

### 4. Feeds Tables

Three separate table files following the pattern `feeds/newyorkfed_*.sql`:

**File**: `schema/feeds/newyorkfed_reference_rates.sql`
- Table: `feeds.newyorkfed_reference_rates`
- Purpose: SOFR, EFFR, OBFR, TGCR, BGCR rates
- Key columns: rate_type, effective_date, rate_percent, volume_billions
- Indexes: datasetid, effective_date, rate_type

**File**: `schema/feeds/newyorkfed_soma_holdings.sql`
- Table: `feeds.newyorkfed_soma_holdings`
- Purpose: System Open Market Account holdings
- Key columns: as_of_date, security_type, cusip, par_value
- Indexes: datasetid, as_of_date, security_type, cusip

**File**: `schema/feeds/newyorkfed_repo_operations.sql`
- Table: `feeds.newyorkfed_repo_operations`
- Purpose: Repo and reverse repo operations
- Key columns: operation_date, operation_type, amount_accepted, award_rate
- Indexes: datasetid, operation_date, operation_type

### 5. Init Script

**File**: `schema/init.sh`

Added execution of NewYorkFed schema files in proper order:

```bash
# After existing data inserts (line 57-58)
$PSQL -f /app/schema/dba/data/newyorkfed_reference_data.sql
$PSQL -f /app/schema/dba/data/newyorkfed_scheduler_jobs.sql

# After feeds schema creation (line 65)
$PSQL -f /app/schema/feeds/newyorkfed_reference_rates.sql
$PSQL -f /app/schema/feeds/newyorkfed_soma_holdings.sql
$PSQL -f /app/schema/feeds/newyorkfed_repo_operations.sql
```

## Initialization Order

When a new database is initialized, files are sourced in this order:

1. **DBA Tables** - Including updated `timportconfig` with API columns
2. **DBA Functions/Procedures/Indexes/Triggers**
3. **DBA Data Inserts** - Including NewYorkFed reference data
4. **DBA Data** - NewYorkFed scheduler jobs
5. **Feeds Schema**
6. **Feeds Tables** - NewYorkFed tables

This ensures all dependencies are met before NewYorkFed schema is created.

## Benefits of This Organization

1. **Clean Separation**: Each table has its own file following project conventions
2. **Base Schema Updated**: API columns are part of the core schema, not a migration
3. **Proper Sourcing**: All files sourced via `init.sh` for fresh database setups
4. **Easy Maintenance**: Each component can be updated independently
5. **Clear Documentation**: File names clearly indicate purpose
6. **Backward Compatible**: Existing file imports unaffected by API columns

## Future Tables

When implementing stub jobs, add new table files following the pattern:

```bash
schema/feeds/newyorkfed_agency_mbs.sql
schema/feeds/newyorkfed_fx_swaps.sql
schema/feeds/newyorkfed_guide_sheets.sql
schema/feeds/newyorkfed_pd_statistics.sql
schema/feeds/newyorkfed_market_share.sql
schema/feeds/newyorkfed_securities_lending.sql
schema/feeds/newyorkfed_treasury_operations.sql
```

Then add to `init.sh`:
```bash
$PSQL -f /app/schema/feeds/newyorkfed_agency_mbs.sql
# ... etc
```

## Testing Schema Changes

To test schema with a fresh database:

```bash
# Stop and remove existing database
docker compose down -v

# Rebuild and start (will run init.sh)
docker compose up -d db

# Verify NewYorkFed tables created
docker compose exec db psql -U tangerine_admin -d tangerine_db -c "\dt feeds.newyorkfed*"

# Verify data source and dataset types
docker compose exec db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT sourcename FROM dba.tdatasource WHERE sourcename = 'NewYorkFed';"

docker compose exec db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT typename FROM dba.tdatasettype WHERE typename LIKE '%Repo%' OR typename LIKE '%SOMA%';"

# Verify scheduler jobs
docker compose exec db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT job_name, is_active FROM dba.tscheduler WHERE job_name LIKE 'NewYorkFed_%';"

# Verify API columns in timportconfig
docker compose exec db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name = 'timportconfig' AND column_name LIKE 'api_%';"
```

---

**Last Updated**: February 6, 2026
**Status**: Schema properly organized following project patterns
