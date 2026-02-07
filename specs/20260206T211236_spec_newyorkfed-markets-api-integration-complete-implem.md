# NewYorkFed Markets API Integration - Complete Implementation Plan

## Context

The NewYorkFed API integration has 10 category-specific jobs, but only 3 are currently functional. The user has provided the correct API endpoints for all jobs after reviewing the official API documentation.

**Current Status (after initial partial fix):**
- ✅ Reference Rates: **Working** (6 records loaded)
- ✅ SOMA Holdings: **Partially Working** (9,013 agency holdings loaded, but user wants monthly Treasury holdings instead)
- ✅ Repo Operations: **Partially Working** (3 operations loaded, but user wants last two weeks instead of latest)
- ❌ Agency MBS: **Stub** (returns 0 records - not implemented)
- ❌ FX Swaps: **Stub** (returns 0 records - not implemented)
- ❌ Guide Sheets: **Stub** (returns 0 records - not implemented)
- ❌ Market Share: **Stub** (returns 0 records - not implemented)
- ❌ PD Statistics: **Dataset type error** (`PdStatistics` should be `PDStatistics`)
- ❌ Securities Lending: **Stub** (returns 0 records - not implemented)
- ❌ Treasury: **Dataset type error** (`Treasury` should be `TreasuryOperations`)

**Root Cause:** Most jobs were created as stubs and never fully implemented. User has now provided correct endpoints for all jobs.

This plan completes the implementation of all 10 NewYorkFed jobs with correct endpoints and field mappings.

## Approach

**Complete all 10 NewYorkFed jobs** using the user-provided correct endpoints:

1. **Fix 2 dataset type name errors** (PD Statistics, Treasury) - quick 1-line changes
2. **Update 2 existing working jobs** (SOMA Holdings, Repo Operations) to use user-specified endpoints
3. **Implement 5 stub jobs** (Agency MBS, FX Swaps, Guide Sheets, Securities Lending, Treasury) with full extract/transform/load logic
4. **Keep 3 working jobs unchanged** (Reference Rates already using correct endpoint)

**Implementation Strategy:**
- All jobs use the existing `NewYorkFedAPIClient.fetch_endpoint()` method
- Each job follows the BaseETLJob pattern: extract() → transform() → load()
- Database tables and dataset types already exist for all jobs
- Client method updates needed for new endpoints (response root paths)

## Correct API Endpoints (User-Provided)

All 8 endpoints provided by the user with tested response structures:

| Category | Endpoint | Response Root Path | Status |
|----------|----------|-------------------|--------|
| Reference Rates | `/api/rates/all/latest.json` | `refRates` | ✅ Working |
| Agency MBS | `/api/ambs/all/announcements/summary/latest.json` | `ambs` | ⚠️ Stub |
| FX Swaps | `/api/fxs/all/latest.json` | `fxSwaps` | ⚠️ Stub |
| Guide Sheets | `/api/guidesheets/si/latest.json` | `guidesheet` | ⚠️ Stub |
| Repo Operations | `/api/rp/all/all/results/lastTwoWeeks.json` | `repo.operations` | 🔄 Update needed |
| Securities Lending | `/api/seclending/all/results/summary/latest.json` | `seclending.operations` | ⚠️ Stub |
| SOMA Holdings | `/api/soma/tsy/get/monthly.json` | `soma.holdings` | 🔄 Update needed |
| Treasury | `/api/tsy/all/announcements/summary/latest.json` | `treasury` | ⚠️ Stub + Name fix |

**Not provided by user (existing stubs remain):**
- Market Share (not in user's list)
- PD Statistics (not in user's list, name fix needed)

**API Details:**
- Base URL: `https://markets.newyorkfed.org`
- Authentication: Public API (no auth required)
- All responses tested and confirmed working
- All use double-nested JSON structures (e.g., `repo.operations`, `soma.holdings`)

## Implementation Plan by Job Category

### Group 1: Quick Fixes (Dataset Type Name Errors)


#### 1. PD Statistics Job (`run_newyorkfed_pd_statistics.py`)
**File:** `etl/jobs/run_newyorkfed_pd_statistics.py`

**Issue:** `dataset_type='PdStatistics'` should be `'PDStatistics'` (capital D)

**Fix:** Change line in `__init__()`:
```python
# OLD:
dataset_type='PdStatistics',
# NEW:
dataset_type='PDStatistics',
```

**Impact:** Fixes "Dataset type PdStatistics not found" error

#### 2. Treasury Job (`run_newyorkfed_treasury.py`)  
**File:** `etl/jobs/run_newyorkfed_treasury.py`

**Issue:** `dataset_type='Treasury'` should be `'TreasuryOperations'`

**Fix:** Change line in `__init__()`:
```python
# OLD:
dataset_type='Treasury',
# NEW:
dataset_type='TreasuryOperations',
```

**Impact:** Fixes "Dataset type Treasury not found" error

---

### Group 2: Update Existing Working Jobs to New Endpoints

#### 3. SOMA Holdings - Switch to Monthly Treasury Holdings
**File:** `etl/jobs/run_newyorkfed_soma_holdings.py`

**Current:** Fetches agency holdings from `/api/soma/agency/get/all/asof/{date}.json` (9,013 records)

**New:** Fetch monthly Treasury holdings from `/api/soma/tsy/get/monthly.json`

**Changes Needed:**
1. **Client Method:** Update `NewYorkFedAPIClient.get_soma_holdings()` to use new endpoint
2. **Response Path:** Keep as `soma.holdings` 
3. **Transform Method:** May need field mapping updates based on Treasury response structure

**Endpoint Change:**
```python
# OLD (in client):
endpoint_path=f'/api/soma/agency/get/all/asof/{as_of_date}.{{format}}'

# NEW:
endpoint_path='/api/soma/tsy/get/monthly.{format}'
```

#### 4. Repo Operations - Switch to Last Two Weeks
**File:** `etl/jobs/run_newyorkfed_repo.py`

**Current:** Fetches latest or last N operations (flexible pattern)

**New:** Fetch last two weeks of all repo/reverse repo operations

**Changes Needed:**
1. **Client Method:** Update `NewYorkFedAPIClient.get_repo_operations()` to use new endpoint
2. **Response Path:** Keep as `repo.operations`
3. **Job Logic:** Simplify - no need for operation_type parameter

**Endpoint Change:**
```python
# OLD (in client):
endpoint = f'/api/rp/{operation_type}/{security_type}/results/latest.{{format}}'

# NEW:
endpoint = '/api/rp/all/all/results/lastTwoWeeks.{format}'
```

---

### Group 3: Implement 5 Stub Jobs

All 5 stub jobs currently return empty list in extract(). Need to implement full extract/transform/load logic.

#### 5. Agency MBS Job (`run_newyorkfed_agency_mbs.py`)
**Endpoint:** `/api/ambs/all/announcements/summary/latest.json`  
**Response Root Path:** `ambs`

**Implementation:**
1. **Client Method:** Create `get_agency_mbs()` method in NewYorkFedAPIClient
2. **Extract:** Call client method
3. **Transform:** Map API fields to database table columns (need to check table schema)
4. **Load:** Use PostgresLoader to insert into `feeds.newyorkfed_agency_mbs`

**Sample Response Fields:** (need to test API for actual structure)

#### 6. FX Swaps Job (`run_newyorkfed_fx_swaps.py`)
**Endpoint:** `/api/fxs/all/latest.json`  
**Response Root Path:** `fxSwaps`

**Implementation:**
1. **Client Method:** Create `get_fx_swaps()` method
2. **Extract:** Call client method
3. **Transform:** Map API fields to database columns
4. **Load:** Insert into `feeds.newyorkfed_fx_swaps`

#### 7. Guide Sheets Job (`run_newyorkfed_guide_sheets.py`)
**Endpoint:** `/api/guidesheets/si/latest.json`  
**Response Root Path:** `guidesheet`

**Implementation:**
1. **Client Method:** Create `get_guide_sheets()` method
2. **Extract:** Call client method  
3. **Transform:** Map API fields to database columns
4. **Load:** Insert into `feeds.newyorkfed_guide_sheets`

#### 8. Securities Lending Job (`run_newyorkfed_securities_lending.py`)
**Endpoint:** `/api/seclending/all/results/summary/latest.json`  
**Response Root Path:** `seclending.operations`

**Implementation:**
1. **Client Method:** Create `get_securities_lending()` method
2. **Extract:** Call client method
3. **Transform:** Map fields like:
   - `operationId` → `operation_id`
   - `operationDate` → `operation_date`
   - `totalParAmtSubmitted` → `total_submitted`
   - `totalParAmtAccepted` → `total_accepted`
4. **Load:** Insert into `feeds.newyorkfed_securities_lending`

**Confirmed Response Structure:**
```json
{
  "seclending": {
    "operations": [
      {
        "operationId": "SL 020626 1",
        "operationDate": "2026-02-06",
        "totalParAmtSubmitted": 34732000000,
        "totalParAmtAccepted": 34434000000,
        ...
      }
    ]
  }
}
```

#### 9. Treasury Job (already has name fix above)
**Endpoint:** `/api/tsy/all/announcements/summary/latest.json`  
**Response Root Path:** `treasury`

**Implementation:**
1. **Client Method:** Create `get_treasury_operations()` method
2. **Extract:** Call client method
3. **Transform:** Map API fields to database columns
4. **Load:** Insert into `feeds.newyorkfed_treasury`

---

### Group 4: Jobs Not in User List (Leave as Stubs)

#### 10. Market Share Job (`run_newyorkfed_market_share.py`)
**Status:** Keep as stub (user didn't provide endpoint)

**Note:** If needed later, can implement when user provides correct endpoint

---

## Critical Files to Modify

### 1. NewYorkFedAPIClient (`etl/clients/newyorkfed_client.py`)

**Changes Needed:**
1. Update `get_soma_holdings()` - use monthly Treasury endpoint
2. Update `get_repo_operations()` - use lastTwoWeeks endpoint
3. Add `get_agency_mbs()` - new method
4. Add `get_fx_swaps()` - new method
5. Add `get_guide_sheets()` - new method
6. Add `get_securities_lending()` - new method
7. Add `get_treasury_operations()` - new method

**Pattern for New Methods:**
```python
def get_<category>(self) -> List[Dict]:
    """Fetch <category> from NewYorkFed API."""
    return self.fetch_endpoint(
        endpoint_path='/api/<path>/latest.{format}',
        response_root_path='<root_path>'
    )
```

### 2. Job Files to Update

**Quick fixes (1 line each):**
- `etl/jobs/run_newyorkfed_pd_statistics.py` - dataset type name
- `etl/jobs/run_newyorkfed_treasury.py` - dataset type name (plus implementation)

**Endpoint updates:**
- `etl/jobs/run_newyorkfed_soma_holdings.py` - change to monthly Treasury
- `etl/jobs/run_newyorkfed_repo.py` - change to lastTwoWeeks

**Full implementations (extract/transform/load):**
- `etl/jobs/run_newyorkfed_agency_mbs.py`
- `etl/jobs/run_newyorkfed_fx_swaps.py`
- `etl/jobs/run_newyorkfed_guide_sheets.py`
- `etl/jobs/run_newyorkfed_securities_lending.py`

### 3. Database Tables to Check

Need to verify table schemas exist for:
- `feeds.newyorkfed_agency_mbs`
- `feeds.newyorkfed_fx_swaps`
- `feeds.newyorkfed_guide_sheets`
- `feeds.newyorkfed_securities_lending`
- `feeds.newyorkfed_treasury`

**If tables don't exist:** Will need to create schema SQL files

---

## Implementation Order

### Phase 1: Quick Wins (5 minutes)
1. Fix PD Statistics dataset type name
2. Fix Treasury dataset type name

**Rebuild and test:** Both jobs should no longer have dataset type errors

### Phase 2: Update Existing Jobs (30 minutes)
3. Update `NewYorkFedAPIClient.get_soma_holdings()` to use monthly Treasury endpoint
4. Update `NewYorkFedAPIClient.get_repo_operations()` to use lastTwoWeeks endpoint
5. Update corresponding job files if needed

**Rebuild and test:** SOMA and Repo jobs should fetch from new endpoints

### Phase 3: Implement Stub Jobs (2-3 hours)
6. Test each stub endpoint with curl to understand response structure
7. Check database table schemas exist
8. Add client methods for each endpoint
9. Implement extract/transform/load logic for each job

**Priority Order:**
1. Securities Lending (response structure already known)
2. Treasury Operations
3. Agency MBS
4. FX Swaps
5. Guide Sheets

**Rebuild and test after each job:** Verify data loads correctly

---

## Verification

### After Each Job Implementation

```bash
# Dry-run test
docker compose exec admin python etl/jobs/run_newyorkfed_<job>.py --dry-run

# Production run
docker compose exec admin python etl/jobs/run_newyorkfed_<job>.py

# Verify data loaded
docker compose exec db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT COUNT(*) FROM feeds.newyorkfed_<table>;"
```

### Final Verification - All Jobs

```bash
# Test all 10 jobs
for job in reference_rates soma_holdings repo agency_mbs fx_swaps guide_sheets \
    pd_statistics market_share securities_lending treasury; do
  echo "========== Testing $job =========="
  docker compose exec admin python etl/jobs/run_newyorkfed_${job}.py --dry-run 2>&1 | \
    grep -E "(ERROR|Fetched|records|complete)" | head -5
done
```

**Expected Results:**
- ✅ Reference Rates: 6 records (unchanged)
- ✅ SOMA Holdings: N records (monthly Treasury holdings)
- ✅ Repo: N records (last 2 weeks of operations)
- ✅ Agency MBS: N records (latest announcements)
- ✅ FX Swaps: N records (latest swaps)
- ✅ Guide Sheets: N records (latest guide sheet)
- ✅ PD Statistics: 0 records or error (stub, but no dataset type error)
- ✅ Market Share: 0 records (stub)
- ✅ Securities Lending: N records (latest operations)
- ✅ Treasury: N records (latest announcements)

### Database Verification

```sql
-- Check all feeds have data (except stubs)
SELECT 'reference_rates' as feed, COUNT(*) FROM feeds.newyorkfed_reference_rates
UNION ALL
SELECT 'soma_holdings', COUNT(*) FROM feeds.newyorkfed_soma_holdings
UNION ALL
SELECT 'repo_operations', COUNT(*) FROM feeds.newyorkfed_repo_operations
UNION ALL
SELECT 'agency_mbs', COUNT(*) FROM feeds.newyorkfed_agency_mbs
UNION ALL
SELECT 'fx_swaps', COUNT(*) FROM feeds.newyorkfed_fx_swaps
UNION ALL
SELECT 'guide_sheets', COUNT(*) FROM feeds.newyorkfed_guide_sheets
UNION ALL
SELECT 'securities_lending', COUNT(*) FROM feeds.newyorkfed_securities_lending
UNION ALL
SELECT 'treasury', COUNT(*) FROM feeds.newyorkfed_treasury;
```

**Expected:** All counts > 0 except Market Share and PD Statistics (stubs)

---

## Summary

**Total Jobs:** 10  
**Jobs to Fix:** 9 (all except Reference Rates which is already working)

**Breakdown:**
- 2 quick dataset type name fixes (2 min)
- 2 endpoint updates for existing jobs (30 min)
- 5 full stub implementations (2-3 hours)
- 1 already working (Reference Rates)

**Estimated Total Time:** 3-4 hours

**Critical Dependencies:**
- Docker image rebuild required after each code change
- Database tables must exist for all jobs (verify first)
- API responses must be tested to understand field mappings
