# NewYorkFed Feeds Tables Debug and Data Retention Plan

## Context

The user reported that not all NewYorkFed feeds tables have data despite successful job runs. After comprehensive investigation, I've identified the root causes and created a plan to ensure all tables can properly retain records when data becomes available.

**Current Database State:**
- ✅ All 10 tables exist in database
- ✅ All 10 job files exist
- ✅ 8 jobs are fully implemented
- ⚠️ 2 jobs are stubs (PD Statistics, Market Share)
- ✅ 5 tables have data (reference_rates, soma_holdings, repo_operations, securities_lending, guide_sheets)
- ⚠️ 5 tables are empty (agency_mbs, fx_swaps, treasury_operations, pd_statistics, market_share)

**Root Causes Identified:**

1. **3 Empty Tables - API Data Unavailable (NOT A BUG):**
   - `newyorkfed_agency_mbs` (0 records) - Job works correctly, but Fed API returns empty array
   - `newyorkfed_fx_swaps` (0 records) - Job works correctly, but Fed API returns empty array
   - `newyorkfed_treasury_operations` (0 records) - Job works correctly, but Fed API returns empty array
   - **Verified:** Directly queried APIs and confirmed they return `{"ambs": {"auctions": []}}`, `{"fxSwaps": {"operations": []}}`, `{"treasury": {"auctions": []}}` respectively
   - **Why:** The Federal Reserve is not currently conducting operations in these categories

2. **2 Empty Tables - Stub Implementation:**
   - `newyorkfed_pd_statistics` (0 records) - Job has no extract logic (returns empty list)
   - `newyorkfed_market_share` (0 records) - Job has no extract logic (returns empty list)
   - **Reason:** API endpoints for these categories may not exist or were not provided by user

## Comprehensive Audit Report

### Current Record Counts (as of 2026-02-06)

| Table Name | Records | Date Range | Status | Notes |
|------------|---------|------------|--------|-------|
| **reference_rates** | 36 | 2026-02-04 to 2026-02-06 | ✅ ACTIVE | Working correctly |
| **soma_holdings** | 167,455 | 2003-07-30 to 2026-02-04 | ✅ ACTIVE | Historical Treasury holdings |
| **repo_operations** | 69 | 2026-01-23 to 2026-02-06 | ✅ ACTIVE | Last two weeks of operations |
| **securities_lending** | 2 | 2026-02-06 | ✅ ACTIVE | Latest operations |
| **guide_sheets** | 22 | 2026-02-04 | ✅ ACTIVE | SI guide sheet details |
| **agency_mbs** | 0 | N/A | ⏳ WAITING | API has no data - job ready |
| **fx_swaps** | 0 | N/A | ⏳ WAITING | API has no data - job ready |
| **treasury_operations** | 0 | N/A | ⏳ WAITING | API has no data - job ready |
| **pd_statistics** | 0 | N/A | ❌ STUB | Not implemented |
| **market_share** | 0 | N/A | ❌ STUB | Not implemented |

### Job Implementation Status

**8 Fully Functional Jobs:**
1. ✅ Reference Rates → `/api/rates/all/latest.json` → `newyorkfed_reference_rates`
2. ✅ SOMA Holdings → `/api/soma/tsy/get/monthly.json` → `newyorkfed_soma_holdings`
3. ✅ Repo Operations → `/api/rp/all/all/results/lastTwoWeeks.json` → `newyorkfed_repo_operations`
4. ✅ Securities Lending → `/api/seclending/all/results/summary/latest.json` → `newyorkfed_securities_lending`
5. ✅ Guide Sheets → `/api/guidesheets/si/latest.json` → `newyorkfed_guide_sheets`
6. ✅ Agency MBS → `/api/ambs/all/announcements/summary/latest.json` → `newyorkfed_agency_mbs` *(ready, waiting for data)*
7. ✅ FX Swaps → `/api/fxs/all/latest.json` → `newyorkfed_fx_swaps` *(ready, waiting for data)*
8. ✅ Treasury Operations → `/api/tsy/all/announcements/summary/latest.json` → `newyorkfed_treasury_operations` *(ready, waiting for data)*

**2 Stub Jobs (Not Implemented):**
9. ❌ PD Statistics → No endpoint → `newyorkfed_pd_statistics`
10. ❌ Market Share → No endpoint → `newyorkfed_market_share`

### Database Schema Status

All 10 tables are properly created with:
- ✅ Primary key (`record_id SERIAL`)
- ✅ Foreign key to `dba.tdataset(datasetid)`
- ✅ Proper indexes (dataset, date, type-specific fields)
- ✅ Audit columns (`created_date`, `created_by`)
- ✅ Appropriate data types (DATE, NUMERIC, VARCHAR, TEXT)

**Total database size:** ~25 MB (mostly from soma_holdings with 167K records)

## Plan: Ensure All Tables Can Retain Records

### Phase 1: Document Current State (1 hour)

**Deliverables:**
1. **Comprehensive Status Report** showing:
   - Which tables have data vs. empty
   - Why each table is empty (API unavailable vs. stub)
   - Expected vs. actual record counts
   - Last successful data fetch timestamps

2. **API Availability Monitor Script** (`scripts/monitor_newyorkfed_apis.py`):
   - Check all 10 API endpoints
   - Report which have data available
   - Identify when previously empty APIs get data
   - Run on schedule to detect data availability changes

3. **Updated Documentation** in `NEWYORKFED_BUG_FIX_SUMMARY.md`:
   - Document that 8/10 jobs are working
   - Explain 3 empty tables are due to Fed not having data (not a bug)
   - Note 2 stubs need API endpoint research

### Phase 2: Verify Data Retention Capability (30 minutes)

**Goal:** Confirm that empty tables CAN retain records when data becomes available

**Tests:**
1. **Create synthetic test data** for agency_mbs, fx_swaps, treasury_operations
2. **Manually inject** test records into each empty table
3. **Verify persistence** by querying tables
4. **Delete test data** after verification
5. **Document** that tables are ready to receive real data

**Test Script:** `scripts/test_newyorkfed_table_retention.py`
- Insert 1-2 test records per empty table
- Verify foreign key constraints work
- Verify indexes are functional
- Verify audit columns auto-populate
- Clean up test data

### Phase 3: Research Stub Jobs API Endpoints (1-2 hours)

**Goal:** Determine if PD Statistics and Market Share endpoints exist in NewYorkFed API

**Investigation Steps:**
1. **Review NewYorkFed API documentation:**
   - Official docs: https://markets.newyorkfed.org/static/docs/markets-api.html
   - Check for Primary Dealer Statistics category
   - Check for Market Share category

2. **Test potential endpoints:**
   ```bash
   # Try common patterns
   curl "https://markets.newyorkfed.org/api/pd/stats/latest.json"
   curl "https://markets.newyorkfed.org/api/marketshare/latest.json"
   curl "https://markets.newyorkfed.org/api/primarydealer/statistics/latest.json"
   ```

3. **Outcomes:**
   - **If endpoints found:** Implement full ETL jobs with extract/transform/load
   - **If endpoints NOT found:** Document as unavailable and remove from active job list

### Phase 4: Implement Solutions Based on Findings (varies)

**Option A: For Empty Tables with Working Jobs (agency_mbs, fx_swaps, treasury_operations)**

*No code changes needed* - jobs are working correctly

**Actions:**
1. Add logging to indicate "API returned 0 records (no data available)"
2. Set up monitoring to alert when APIs start providing data
3. Document expected behavior in job comments
4. Run jobs daily to capture data when it becomes available

**Option B: For Stub Jobs (pd_statistics, market_share)**

*If endpoints are found:*
1. Implement client methods in `etl/clients/newyorkfed_client.py`
2. Implement extract/transform/load logic in job files
3. Test with API data
4. Add to `scripts/run_all_newyorkfed_jobs.py`

*If endpoints NOT found:*
1. Mark jobs as "Not Available" in documentation
2. Keep stub implementation in case endpoints are added later
3. Remove from active job runner script
4. Document in comments why these are stubs

### Phase 5: Create Enhanced Monitoring (2 hours)

**Goal:** Proactive monitoring for when data becomes available

**Deliverables:**

1. **API Status Dashboard** (`scripts/newyorkfed_api_status_report.py`):
   - Query all 10 APIs
   - Show record counts from each API
   - Compare against database record counts
   - Highlight discrepancies
   - Generate HTML/JSON report

2. **Scheduled Health Check** (Airflow DAG or cron):
   - Run daily to check API availability
   - Send alert when previously empty API has data
   - Track data freshness (last update time)

3. **Data Quality Checks:**
   - Verify no duplicate records
   - Check for missing required fields
   - Validate date ranges are consistent
   - Flag anomalies (sudden drops in record counts)

## Critical Files

### Files to Create/Modify:

1. **Monitor Script** (NEW)
   - `scripts/monitor_newyorkfed_apis.py` - Check API data availability

2. **Test Script** (NEW)
   - `scripts/test_newyorkfed_table_retention.py` - Verify tables can retain records

3. **Status Report** (NEW)
   - `scripts/newyorkfed_api_status_report.py` - Generate comprehensive status report

4. **Job Updates** (MODIFY if needed)
   - `etl/jobs/run_newyorkfed_agency_mbs.py` - Add better logging for 0 records
   - `etl/jobs/run_newyorkfed_fx_swaps.py` - Add better logging for 0 records
   - `etl/jobs/run_newyorkfed_treasury.py` - Add better logging for 0 records

5. **Stub Jobs** (IMPLEMENT if endpoints found)
   - `etl/jobs/run_newyorkfed_pd_statistics.py` - Replace stub with full implementation
   - `etl/jobs/run_newyorkfed_market_share.py` - Replace stub with full implementation

6. **Client Updates** (MODIFY if stub endpoints found)
   - `etl/clients/newyorkfed_client.py` - Add methods for pd_statistics and market_share

7. **Documentation** (UPDATE)
   - `NEWYORKFED_BUG_FIX_SUMMARY.md` - Update with current findings
   - `NEWYORKFED_TESTING_SUMMARY.md` - Add table retention test results

## Verification Plan

### Step 1: Verify Table Schemas
```sql
-- Confirm all 10 tables exist with proper structure
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('feeds.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'feeds' AND tablename LIKE 'newyorkfed_%'
ORDER BY tablename;
```

### Step 2: Test Data Retention
```python
# Run retention test script
python scripts/test_newyorkfed_table_retention.py

# Expected output:
# ✅ newyorkfed_agency_mbs can retain records
# ✅ newyorkfed_fx_swaps can retain records
# ✅ newyorkfed_treasury_operations can retain records
# ✅ newyorkfed_pd_statistics can retain records
# ✅ newyorkfed_market_share can retain records
```

### Step 3: Run API Monitor
```bash
# Check API status for all endpoints
python scripts/monitor_newyorkfed_apis.py

# Expected output shows:
# - Which APIs have data available
# - Which APIs return empty arrays
# - API response times
# - Any errors
```

### Step 4: Generate Status Report
```bash
# Create comprehensive status report
python scripts/newyorkfed_api_status_report.py --output report.html

# Report should show:
# - Table record counts
# - API data availability
# - Job execution history
# - Data freshness metrics
```

### Step 5: Run All Jobs
```bash
# Execute all functional jobs
python scripts/run_all_newyorkfed_jobs.py

# Expected: 8 jobs succeed (5 with data, 3 with 0 records but no errors)
```

## Expected Outcomes

**After Implementation:**

1. **Clear Documentation** of why tables are empty:
   - 3 tables: "Waiting for Federal Reserve to publish data"
   - 2 tables: "API endpoint not available" or "Fully implemented"

2. **Monitoring System** that:
   - Detects when APIs start providing data
   - Alerts if data stops flowing
   - Tracks data freshness

3. **Proven Table Retention**:
   - All 10 tables verified to accept and retain records
   - Foreign keys working correctly
   - Indexes functional
   - No schema issues

4. **Complete Implementation**:
   - Either 10/10 jobs functional (if PD/Market Share endpoints found)
   - Or 8/10 jobs functional + 2 documented as unavailable

## Summary

**Problem:** 5 of 10 NewYorkFed tables have no data

**Root Cause Analysis:**
- ✅ Table schemas are correct (all 10 exist and can retain data)
- ✅ Job implementations work correctly (8 of 10 fully functional)
- ⏳ 3 empty tables are waiting for Federal Reserve to publish data (not a bug)
- ❌ 2 empty tables are stubs without API endpoint implementation

**Solution:**
- Document current state clearly
- Verify table retention capability
- Research missing API endpoints
- Implement monitoring for data availability
- Enhance logging for empty API responses

**Timeline:** 4-5 hours total
- Phase 1: Documentation (1 hour)
- Phase 2: Retention testing (30 min)
- Phase 3: Endpoint research (1-2 hours)
- Phase 4: Implementation (varies based on findings)
- Phase 5: Monitoring setup (2 hours)
