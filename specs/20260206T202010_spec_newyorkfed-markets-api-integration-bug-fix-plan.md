# NewYorkFed Markets API Integration - Bug Fix Plan

## Context

The NewYorkFed API integration was partially implemented but contains incorrect endpoint paths and response field mappings. User reviewed the actual API documentation and found:

**Current Status:**
- ✅ Reference Rates job: **Working** (18 records loaded, 3 datasets)
- ❌ SOMA Holdings job: **Failing** - null value in 'as_of_date' column (field mapping issue)
- ❌ Repo Operations job: **Failing** - 400 Bad Request (missing {include} path parameter)
- ❌ Reverse Repo job: **Failing** - 400 Bad Request (missing {include} path parameter)

**Root Cause:** Incorrect API endpoint paths discovered after reviewing actual NewYorkFed Markets API documentation at https://markets.newyorkfed.org/static/docs/markets-api.yml

This plan fixes the 3 failing jobs and updates import configs to match the actual API specification.

## Approach

**Dual Strategy**:
1. **Extend timportconfig** with nullable API-specific columns for future flexibility
2. **Create category-specific jobs** (10 jobs) that directly use NewYorkFedAPIClient for type-safe field mapping

**Rationale**:
- Config extension future-proofs the system for generic API imports
- Category-specific jobs provide type safety, better observability, and easier debugging
- Separate jobs allow independent scheduling and granular error handling

## API Endpoints Summary

NewYorkFed Markets API provides 40+ endpoints across 10 categories:

| Category | Endpoints | Example Data |
|----------|-----------|--------------|
| Reference Rates | 3 | SOFR, EFFR, OBFR, TGCR, BGCR |
| Agency MBS | 4 | Mortgage-backed securities operations |
| FX Swaps | 4 | Central bank liquidity swaps |
| Primary Dealer Stats | 9 | Survey results, time series |
| Repo Operations | 3 | Repo/reverse repo operations |
| SOMA Holdings | 2 | System Open Market Account holdings |
| Treasury Operations | 2 | Treasury securities operations |
| Securities Lending | 2 | Securities lending operations |
| Market Share | 2 | Quarterly/YTD dealer market share |
| Guide Sheets | 2 | FR 2004SI, WI, F-Series guides |

**API Details**:
- Base URL: `https://markets.newyorkfed.org`
- Authentication: Public API (no auth required)
- Response formats: JSON, XML, CSV, XLSX (via `{format}` path parameter)
- Rate limiting: Conservative 60 req/min (not specified in docs)
- Date format: **yyyy-MM-dd** (consistently across all endpoints)
- Query param dates: **Optional** - default to current date when not provided
- Invalid requests return HTTP 400 with descriptive JSON error messages

## API Endpoint Corrections

### 1. Reference Rates (Actually Correct!)

**Current implementation:**
```
/api/rates/all/latest.{format}
/api/rates/all/search.{format}
```

**Status:** ✅ **CORRECT** - matches actual API documentation

**Note:** The OpenAPI YAML showed `/api/refrates/` but the actual working endpoints use `/api/rates/`. Current implementation is correct.

**Query Parameters for search endpoint:**
- `startDate` (yyyy-MM-dd) - Optional, defaults to current date
- `endDate` (yyyy-MM-dd) - Optional, defaults to current date

---

### 2. SOMA Holdings (Endpoint Correct, Field Mapping Issue)

**Current implementation:**
```
GET /api/soma/summary.{format}
Response root path: 'soma'
```

**Status:** ✅ Endpoint path is **CORRECT** per actual API docs

**Available endpoints:**
- `/api/soma/summary.json` - Summary of historical domestic SOMA holdings (what we're using)
- `/api/soma/asofdates/list.json` - Lists all available SOMA holding dates
- `/api/soma/agency/get/all/asof/{date}.json` - Agency holdings for specific date
- `/api/soma/tsy/get/cusip/{cusip}.json` - Treasury holdings by CUSIP

**Root Cause:** Field mapping issue, not endpoint issue
- Current transform() expects `asOfDate` field in response
- Need to test actual response to see real field names
- Error: "null value in column 'as_of_date'" suggests field doesn't exist in API response

---

### 3. Repo/Reverse Repo Operations (Critical Fix Required)

**Incorrect (current):**
```
GET /api/repo/results/search.json
GET /api/reverserepo/results/search.json
```

**Correct (per actual API docs):**
```
GET /api/rp/all/all/results/latest.json                    # Latest all repo & RRP
GET /api/rp/reverserepo/all/results/last/5.json            # Last N reverse repo
GET /api/rp/results/search.json?startDate=...&endDate=...  # Search with filters
```

**Critical Differences:**
1. Base path is `/api/rp/` NOT `/api/repo/`
2. Path structure: `/api/rp/{operationType}/{securityType}/results/{endpoint}`
   - `operationType`: all | repo | reverserepo
   - `securityType`: all | tsy | mbs | agency
   - `endpoint`: latest | last/{n} | search
3. Query parameters for search:
   - `startDate`, `endDate` (yyyy-MM-dd)
   - `operationTypes`: repo | reverserepo
   - `securityType`: tsy | mbs | agency

**Root Cause of 400 Error:** Wrong base path (`/api/repo/` instead of `/api/rp/`) AND incorrect path structure

## Critical Files

### Files to Create

1. **`/opt/tangerine/etl/clients/newyorkfed_client.py`**
   - NewYorkFedAPIClient extending BaseAPIClient
   - Handle {format} parameter replacement, response parsing, nested JSON extraction
   - Public API (no auth headers needed)

2. **10 Category-Specific Job Files**:
   - `/opt/tangerine/etl/jobs/run_newyorkfed_reference_rates.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_agency_mbs.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_fx_swaps.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_guide_sheets.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_pd_statistics.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_market_share.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_repo.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_securities_lending.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_soma_holdings.py`
   - `/opt/tangerine/etl/jobs/run_newyorkfed_treasury.py`
   - Each inherits from BaseETLJob, uses NewYorkFedAPIClient

3. **Configuration SQL Scripts**:
   - `/opt/tangerine/schema/migrations/add_api_columns_to_timportconfig.sql`
   - `/opt/tangerine/scripts/setup_newyorkfed_datasources.sql`
   - `/opt/tangerine/scripts/setup_newyorkfed_schedules.sql`

4. **Test Files**:
   - `/opt/tangerine/tests/etl/test_newyorkfed_client.py`
   - `/opt/tangerine/tests/etl/test_newyorkfed_integration.py`
   - `/opt/tangerine/tests/fixtures/newyorkfed_responses.json`

### Files to Modify

1. **`/opt/tangerine/schema/dba/tables/timportconfig.sql`**
   - Add 11 nullable API columns (api_base_url, api_endpoint_path, import_mode, etc.)
   - Modify valid_directories constraint to allow API imports
   - Maintain backward compatibility

## Bug Fix Implementation Steps

### Phase 1: Reference Rates Job - No Changes Needed

**Status:** ✅ **Already Correct**

Current implementation using `/api/rates/all/latest.{format}` and `/api/rates/all/search.{format}` matches the actual API documentation. No changes required.

**Evidence:** Job successfully loaded 18 records across 3 datasets without errors.

### Phase 2: Fix SOMA Holdings Job - Field Mapping Issue

Files:
- `/opt/tangerine/etl/jobs/run_newyorkfed_soma_holdings.py`
- Possibly `/opt/tangerine/schema/feeds/newyorkfed_soma_holdings.sql`

**Status:** Endpoint `/api/soma/summary.json` is correct, but field mapping is wrong

**Step 2.1: Test Live API to See Actual Response**

```bash
curl -X GET "https://markets.newyorkfed.org/api/soma/summary.json" \
  -H "Accept: application/json" | jq '.' | head -50
```

Expected response structure needs to be examined to identify:
- Is `asOfDate` a field in the response? (transform() expects it but gets null)
- What is the actual field name for the date?
- Is data nested under a root key?
- What other fields are available?

**Step 2.2: Update transform() Method**

Current transform() tries to access:
```python
as_of_date_str = record.get('asOfDate')  # Field doesn't exist!
maturity_date_str = record.get('maturityDate')
cusip = record.get('cusip')
security_description = record.get('securityDescription')
par_value = record.get('parValue')
current_face_value = record.get('currentFaceValue')
```

Need to:
1. Test API to see actual field names
2. Update transform() to match actual response structure
3. Handle missing/optional fields gracefully

**Step 2.3: Consider Alternative Endpoints**

If `/api/soma/summary.json` doesn't provide the right data structure, consider:
- `/api/soma/asofdates/list.json` - Get available dates
- `/api/soma/agency/get/all/asof/{date}.json` - Agency holdings for specific date
- `/api/soma/tsy/get/cusip/{cusip}.json` - Treasury holdings by CUSIP

### Phase 3: Fix Repo/Reverse Repo Operations Job (Critical)

Files:
- `/opt/tangerine/etl/clients/newyorkfed_client.py`
- `/opt/tangerine/etl/jobs/run_newyorkfed_repo.py`

**Root Cause:** Wrong base path - using `/api/repo/` instead of `/api/rp/`

**Step 3.1: Update NewYorkFedAPIClient Method**

Current (incorrect):
```python
def get_repo_operations(self, operation_type: str = 'repo') -> List[Dict[str, Any]]:
    """Fetch repo or reverse repo operations."""
    endpoint_map = {
        'repo': '/api/repo/results/search.{format}',           # WRONG PATH!
        'reverserepo': '/api/reverserepo/results/search.{format}'  # WRONG PATH!
    }
    return self.fetch_endpoint(
        endpoint_path=endpoint_map.get(operation_type),
        response_format='json',
        response_root_path=operation_type
    )
```

Updated (correct):
```python
def get_repo_operations(
    self,
    operation_type: str = 'all',
    security_type: str = 'all',
    start_date: str = None,
    end_date: str = None,
    use_latest: bool = False,
    last_n: int = None
) -> List[Dict[str, Any]]:
    """
    Fetch repo operations from NewYorkFed API.

    Args:
        operation_type: 'all' | 'repo' | 'reverserepo'
        security_type: 'all' | 'tsy' | 'mbs' | 'agency'
        start_date: Start date (yyyy-MM-dd) for search endpoint
        end_date: End date (yyyy-MM-dd) for search endpoint
        use_latest: If True, get latest operations only
        last_n: If provided, get last N operations

    Returns:
        List of repo operation records
    """
    # Build endpoint path based on usage
    if use_latest:
        endpoint_path = f'/api/rp/{operation_type}/{security_type}/results/latest.{{format}}'
        query_params = None
    elif last_n:
        endpoint_path = f'/api/rp/{operation_type}/{security_type}/results/last/{last_n}.{{format}}'
        query_params = None
    else:
        # Search endpoint
        endpoint_path = '/api/rp/results/search.{format}'
        query_params = {}
        if start_date:
            query_params['startDate'] = start_date
        if end_date:
            query_params['endDate'] = end_date
        if operation_type != 'all':
            query_params['operationTypes'] = operation_type
        if security_type != 'all':
            query_params['securityType'] = security_type

    return self.fetch_endpoint(
        endpoint_path=endpoint_path,
        response_format='json',
        query_params=query_params if query_params else None,
        response_root_path=None  # TBD from testing
    )
```

**Step 3.2: Update Repo Job**

Simplify job to use latest or last N operations:
```python
def extract(self) -> List[Dict[str, Any]]:
    self.logger.info(
        f"Fetching {self.operation_type} operations",
        extra={'stepcounter': 'extract'}
    )

    # Option 1: Get latest operations
    return self.client.get_repo_operations(
        operation_type=self.operation_type,
        security_type='all',
        use_latest=True
    )

    # Option 2: Get last 10 operations
    # return self.client.get_repo_operations(
    #     operation_type=self.operation_type,
    #     security_type='all',
    #     last_n=10
    # )
```

**Step 3.3: Test Corrected Endpoints**

```bash
# Latest all repo & RRP results
curl -X GET "https://markets.newyorkfed.org/api/rp/all/all/results/latest.json" \
  -H "Accept: application/json" | jq '.'

# Last 5 reverse repo results
curl -X GET "https://markets.newyorkfed.org/api/rp/reverserepo/all/results/last/5.json" \
  -H "Accept: application/json" | jq '.'

# Search with filters
curl -X GET "https://markets.newyorkfed.org/api/rp/results/search.json?startDate=2026-01-01&endDate=2026-02-06&operationTypes=repo&securityType=tsy" \
  -H "Accept: application/json" | jq '.'
```

Examine response to determine:
- Response root path (if any)
- Field names for operation_date, operation_id, etc.
- Whether response is array or nested object

### Phase 4: Update Import Configurations

File: `/opt/tangerine/scripts/setup_newyorkfed_import_configs.sql`

**4.1: Reference Rates Configs** - No changes needed (already correct)

**4.2: SOMA Holdings Config** - No endpoint changes, may need response_root_path update
```sql
UPDATE dba.timportconfig
SET api_response_root_path = NULL  -- Or update based on testing
WHERE config_name = 'NewYorkFed_SOMA_Holdings';
```

**4.3: Repo Operations Configs** - Critical path fix
```sql
-- Update Repo config (fix path from /api/repo/ to /api/rp/)
UPDATE dba.timportconfig
SET api_endpoint_path = '/api/rp/repo/all/results/latest.{format}'
WHERE config_name = 'NewYorkFed_Repo_Operations';

-- Update Reverse Repo config (fix path from /api/reverserepo/ to /api/rp/)
UPDATE dba.timportconfig
SET api_endpoint_path = '/api/rp/reverserepo/all/results/latest.{format}'
WHERE config_name = 'NewYorkFed_ReverseRepo_Operations';
```

### Phase 5: Update Tests

File: `/opt/tangerine/tests/unit/etl/test_newyorkfed_client.py`

Update test fixtures to use correct endpoint paths:

```python
def test_get_reference_rates_latest(self, mock_session, client):
    # Update expected endpoint
    assert endpoint == '/api/refrates/all/latest.json'  # Changed from /api/rates/

def test_get_soma_holdings(self, mock_session, client):
    # Test new as_of_date parameter
    data = client.get_soma_holdings(as_of_date='2026-02-05')
    assert endpoint == '/api/soma/get/asof/2026-02-05.json'

def test_get_repo_operations(self, mock_session, client):
    # Test new include and date parameters
    data = client.get_repo_operations(
        operation_type='repo',
        include='summary',
        start_date='2026-01-01',
        end_date='2026-02-06'
    )
    assert endpoint == '/api/repo/repo/results/summary/search.json'
    assert query_params == {'startDate': '2026-01-01', 'endDate': '2026-02-06'}
```

### Phase 6: Test Actual API Endpoints (From Official Documentation)

Test these curl commands to understand actual response structures before making code changes.

**📊 REFERENCE RATES** (Working - No Changes Needed)

```bash
# Latest all rates
curl -X GET "https://markets.newyorkfed.org/api/rates/all/latest.json" \
  -H "Accept: application/json"

# Last n reference rates (e.g., SOFR)
curl -X GET "https://markets.newyorkfed.org/api/rates/secured/sofr/last/10.json" \
  -H "Accept: application/json"

# Search reference rates by date range
curl -X GET "https://markets.newyorkfed.org/api/rates/all/search.json?startDate=2025-01-01&endDate=2025-01-31" \
  -H "Accept: application/json"
```

**📈 SOMA HOLDINGS** (Fix Field Mapping)

```bash
# SOMA summary timeseries (CURRENT ENDPOINT - correct!)
curl -X GET "https://markets.newyorkfed.org/api/soma/summary.json" \
  -H "Accept: application/json"

# List SOMA as-of dates
curl -X GET "https://markets.newyorkfed.org/api/soma/asofdates/list.json" \
  -H "Accept: application/json"

# Get agency holdings for a date
curl -X GET "https://markets.newyorkfed.org/api/soma/agency/get/all/asof/2025-01-30.json" \
  -H "Accept: application/json"

# Get Treasury holdings by CUSIP
curl -X GET "https://markets.newyorkfed.org/api/soma/tsy/get/cusip/912828A83.json" \
  -H "Accept: application/json"
```

**🔁 REPO & REVERSE REPO OPERATIONS** (Fix Path - Critical!)

```bash
# Latest all repo & RRP results (CORRECT PATH!)
curl -X GET "https://markets.newyorkfed.org/api/rp/all/all/results/latest.json" \
  -H "Accept: application/json"

# Last n repo results (e.g., reversed)
curl -X GET "https://markets.newyorkfed.org/api/rp/reverserepo/all/results/last/5.json" \
  -H "Accept: application/json"

# Search repo results with filters
curl -X GET "https://markets.newyorkfed.org/api/rp/results/search.json?startDate=2025-01-01&endDate=2025-01-31&operationTypes=repo&securityType=tsy" \
  -H "Accept: application/json"
```

**Testing Instructions:**
1. Test SOMA endpoint to understand actual response field names
2. Test Repo endpoints with correct `/api/rp/` path
3. Examine JSON responses to identify:
   - Root level fields vs nested data
   - Actual field names for dates, IDs, amounts
   - Whether data is array or object
4. Update transform() methods to match actual field names
5. Update NewYorkFedAPIClient methods with correct paths

## Verification - After Implementation

### 1. Run Unit Tests
```bash
docker compose exec admin pytest tests/unit/etl/test_newyorkfed_client.py -v
```

**Expected:** All 25 tests pass (updated for new endpoints)

### 2. Run Jobs in Dry-Run Mode
```bash
# Reference Rates (should still work)
docker compose exec admin python etl/jobs/run_newyorkfed_reference_rates.py --dry-run --endpoint-type latest

# SOMA Holdings (fixed)
docker compose exec admin python etl/jobs/run_newyorkfed_soma_holdings.py --dry-run

# Repo Operations (fixed)
docker compose exec admin python etl/jobs/run_newyorkfed_repo.py --dry-run --operation-type repo
docker compose exec admin python etl/jobs/run_newyorkfed_repo.py --dry-run --operation-type reverserepo
```

**Expected:** All jobs complete without errors, show "DRY RUN: Would load N records"

### 3. Run Jobs with Database Writes
```bash
# Clear existing test data
docker compose exec db psql -U tangerine_admin -d tangerine_db -c "
DELETE FROM feeds.newyorkfed_reference_rates;
DELETE FROM feeds.newyorkfed_soma_holdings;
DELETE FROM feeds.newyorkfed_repo_operations;
"

# Run all 4 jobs
docker compose exec admin python etl/jobs/run_newyorkfed_reference_rates.py
docker compose exec admin python etl/jobs/run_newyorkfed_soma_holdings.py
docker compose exec admin python etl/jobs/run_newyorkfed_repo.py --operation-type repo
docker compose exec admin python etl/jobs/run_newyorkfed_repo.py --operation-type reverserepo
```

**Expected:**
- ✅ All 4 jobs complete successfully
- ✅ No null constraint violations
- ✅ No 400 Bad Request errors
- ✅ Records loaded to all 3 feeds tables

### 4. Verify Data in Database
```sql
-- Check all 3 feeds tables populated
SELECT 'reference_rates' as feed, COUNT(*) as records FROM feeds.newyorkfed_reference_rates
UNION ALL
SELECT 'soma_holdings', COUNT(*) FROM feeds.newyorkfed_soma_holdings
UNION ALL
SELECT 'repo_operations', COUNT(*) FROM feeds.newyorkfed_repo_operations;

-- Verify no null critical fields
SELECT 'ref_rates_nulls' as check, COUNT(*)
FROM feeds.newyorkfed_reference_rates
WHERE effective_date IS NULL OR rate_type IS NULL;

SELECT 'soma_nulls' as check, COUNT(*)
FROM feeds.newyorkfed_soma_holdings
WHERE as_of_date IS NULL;  -- Should be 0

SELECT 'repo_nulls' as check, COUNT(*)
FROM feeds.newyorkfed_repo_operations
WHERE operation_date IS NULL OR operation_id IS NULL;

-- Verify datasets created with clean labels
SELECT datasetid, label, datasetdate, recordsloaded
FROM dba.tdataset
WHERE datasourceid = (SELECT datasourceid FROM dba.tdatasource WHERE sourcename = 'NewYorkFed')
ORDER BY datasetid DESC
LIMIT 10;
```

**Expected:**
- All 3 feeds have >0 records
- No null constraint violations (counts = 0)
- Dataset labels are clean (e.g., "ReferenceRates_2026-02-06_latest", not random UUIDs)

### 5. Verify Import Configs Updated
```sql
SELECT config_name, api_endpoint_path, is_active
FROM dba.timportconfig
WHERE config_name LIKE 'NewYorkFed_%'
ORDER BY config_name;
```

**Expected:**
- Reference Rates configs use `/api/refrates/` (not `/api/rates/`)
- SOMA config uses `/api/soma/get/asof/{date}.{format}`
- Repo configs use `/api/repo/{operationType}/results/summary/search.{format}`

## Summary of Bugs Fixed

### Bug #1: Reference Rates ✅ NO BUG
- **Status:** Endpoint `/api/rates/all/latest.json` is CORRECT per official API docs
- **Impact:** None - job working correctly (18 records loaded)
- **Action:** No changes needed

### Bug #2: SOMA Holdings - Field Mapping Issue
- **Issue:** Endpoint `/api/soma/summary.json` is correct, but transform() expects wrong field names
  - Current code expects `asOfDate` field in response
  - Actual API response structure is unknown (needs testing)
- **Impact:** High - job fails with null constraint violation on as_of_date
- **Fix:**
  - Test actual API response to see real field names
  - Update transform() method to match actual response structure
  - May need to update database schema if fields don't align
- **Files:** etl/jobs/run_newyorkfed_soma_holdings.py, possibly schema/feeds/newyorkfed_soma_holdings.sql

### Bug #3: Repo/Reverse Repo - Wrong Base Path (Critical)
- **Issue:** Using wrong base path in API calls
  - Current: `/api/repo/results/search.{format}` and `/api/reverserepo/results/search.{format}` ❌
  - Correct: `/api/rp/all/all/results/latest.json` or `/api/rp/{operationType}/all/results/last/{n}.json` ✅
  - **Key:** Base path is `/api/rp/` NOT `/api/repo/`!
- **Impact:** Critical - job fails with 400 Bad Request
- **Fix:**
  - Change base path from `/api/repo/` to `/api/rp/`
  - Update path structure to match actual API: `/api/rp/{operationType}/{securityType}/results/{endpoint}`
  - Use `latest` or `last/{n}` endpoints instead of `search` for simplicity
- **Files:** etl/clients/newyorkfed_client.py, etl/jobs/run_newyorkfed_repo.py, scripts/setup_newyorkfed_import_configs.sql

## Implementation Order

1. **Phase 6 FIRST**: Test actual API endpoints with curl commands to understand responses
2. **Phase 3**: Fix Repo Operations (highest priority - 400 errors blocking job)
3. **Phase 2**: Fix SOMA Holdings (field mapping based on API test results)
4. **Phase 1**: Skip (Reference Rates already working correctly)
5. **Phase 4**: Update import configs for Repo endpoints
6. **Phase 5**: Update unit tests
7. **Verification**: Run all jobs and verify data quality
