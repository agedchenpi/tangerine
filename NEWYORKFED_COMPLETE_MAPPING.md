# NewYorkFed Markets API - Complete Component Mapping

## Overview
Each of the 10 NewYorkFed API categories has:
1. A dedicated ETL job
2. A dedicated feeds table
3. A dataset type configuration
4. A scheduler job configuration

## Complete Mapping

| # | API Category | ETL Job | Feeds Table | Status |
|---|--------------|---------|-------------|--------|
| 1 | **Reference Rates** | `run_newyorkfed_reference_rates.py` | `feeds.newyorkfed_reference_rates` | ✅ Implemented |
| 2 | **SOMA Holdings** | `run_newyorkfed_soma_holdings.py` | `feeds.newyorkfed_soma_holdings` | ✅ Implemented |
| 3 | **Repo Operations** | `run_newyorkfed_repo.py` | `feeds.newyorkfed_repo_operations` | ✅ Implemented |
| 4 | **Agency MBS** | `run_newyorkfed_agency_mbs.py` | `feeds.newyorkfed_agency_mbs` | 🔶 Stub |
| 5 | **FX Swaps** | `run_newyorkfed_fx_swaps.py` | `feeds.newyorkfed_fx_swaps` | 🔶 Stub |
| 6 | **Guide Sheets** | `run_newyorkfed_guide_sheets.py` | `feeds.newyorkfed_guide_sheets` | 🔶 Stub |
| 7 | **PD Statistics** | `run_newyorkfed_pd_statistics.py` | `feeds.newyorkfed_pd_statistics` | 🔶 Stub |
| 8 | **Market Share** | `run_newyorkfed_market_share.py` | `feeds.newyorkfed_market_share` | 🔶 Stub |
| 9 | **Securities Lending** | `run_newyorkfed_securities_lending.py` | `feeds.newyorkfed_securities_lending` | 🔶 Stub |
| 10 | **Treasury Operations** | `run_newyorkfed_treasury_operations.py` | `feeds.newyorkfed_treasury_operations` | 🔶 Stub |

## File Structure

```
tangerine/
├── etl/
│   ├── clients/
│   │   └── newyorkfed_client.py                        # API client
│   └── jobs/
│       ├── run_newyorkfed_reference_rates.py           # 1. ✅ Implemented
│       ├── run_newyorkfed_soma_holdings.py             # 2. ✅ Implemented
│       ├── run_newyorkfed_repo.py                      # 3. ✅ Implemented
│       ├── run_newyorkfed_agency_mbs.py                # 4. 🔶 Stub
│       ├── run_newyorkfed_fx_swaps.py                  # 5. 🔶 Stub
│       ├── run_newyorkfed_guide_sheets.py              # 6. 🔶 Stub
│       ├── run_newyorkfed_pd_statistics.py             # 7. 🔶 Stub
│       ├── run_newyorkfed_market_share.py              # 8. 🔶 Stub
│       ├── run_newyorkfed_securities_lending.py        # 9. 🔶 Stub
│       └── run_newyorkfed_treasury_operations.py       # 10. 🔶 Stub
└── schema/
    ├── dba/
    │   ├── tables/
    │   │   └── timportconfig.sql                       # Updated with API columns
    │   └── data/
    │       ├── newyorkfed_reference_data.sql           # Data source + 10 dataset types
    │       └── newyorkfed_scheduler_jobs.sql           # 11 scheduler jobs
    └── feeds/
        ├── newyorkfed_reference_rates.sql              # 1. ✅ Table ready
        ├── newyorkfed_soma_holdings.sql                # 2. ✅ Table ready
        ├── newyorkfed_repo_operations.sql              # 3. ✅ Table ready
        ├── newyorkfed_agency_mbs.sql                   # 4. ✅ Table ready
        ├── newyorkfed_fx_swaps.sql                     # 5. ✅ Table ready
        ├── newyorkfed_guide_sheets.sql                 # 6. ✅ Table ready
        ├── newyorkfed_pd_statistics.sql                # 7. ✅ Table ready
        ├── newyorkfed_market_share.sql                 # 8. ✅ Table ready
        ├── newyorkfed_securities_lending.sql           # 9. ✅ Table ready
        └── newyorkfed_treasury_operations.sql          # 10. ✅ Table ready
```

## Detailed Component Breakdown

### 1. Reference Rates (SOFR, EFFR, OBFR, TGCR, BGCR)
- **Endpoint**: `/api/rates/all/latest.json` or `/api/rates/all/search.json`
- **Job**: `run_newyorkfed_reference_rates.py` ✅
- **Table**: `feeds.newyorkfed_reference_rates` ✅
- **Dataset Type**: `ReferenceRates`
- **Scheduler**: `NewYorkFed_ReferenceRates` (Daily 9:00 AM) ✅ Active
- **Key Columns**: rate_type, effective_date, rate_percent, volume_billions
- **Test Status**: ✅ Verified - 6 records loaded successfully

### 2. SOMA Holdings
- **Endpoint**: `/api/soma/summary.json`
- **Job**: `run_newyorkfed_soma_holdings.py` ✅
- **Table**: `feeds.newyorkfed_soma_holdings` ✅
- **Dataset Type**: `SOMAHoldings`
- **Scheduler**: `NewYorkFed_SOMA` (Thursday 10:00 AM) ✅ Active
- **Key Columns**: as_of_date, security_type, cusip, par_value

### 3. Repo Operations
- **Endpoint**: `/api/repo/results/search.json`, `/api/reverserepo/results/search.json`
- **Job**: `run_newyorkfed_repo.py` ✅
- **Table**: `feeds.newyorkfed_repo_operations` ✅
- **Dataset Type**: `RepoOperations`
- **Scheduler**:
  - `NewYorkFed_Repo` (Daily 9:05 AM) ✅ Active
  - `NewYorkFed_ReverseRepo` (Daily 9:10 AM) ✅ Active
- **Key Columns**: operation_date, operation_type, amount_accepted, award_rate

### 4. Agency MBS
- **Endpoint**: TBD (requires API documentation research)
- **Job**: `run_newyorkfed_agency_mbs.py` 🔶 Stub
- **Table**: `feeds.newyorkfed_agency_mbs` ✅ Ready
- **Dataset Type**: `AgencyMBS`
- **Scheduler**: `NewYorkFed_AgencyMBS` (Friday 10:00 AM) ❌ Inactive
- **Key Columns**: operation_date, cusip, operation_amount, total_accepted

### 5. FX Swaps
- **Endpoint**: TBD
- **Job**: `run_newyorkfed_fx_swaps.py` 🔶 Stub
- **Table**: `feeds.newyorkfed_fx_swaps` ✅ Ready
- **Dataset Type**: `FXSwaps`
- **Scheduler**: `NewYorkFed_FXSwaps` (Friday 10:05 AM) ❌ Inactive
- **Key Columns**: swap_date, counterparty, currency_code, exchange_rate

### 6. Guide Sheets
- **Endpoint**: TBD
- **Job**: `run_newyorkfed_guide_sheets.py` 🔶 Stub
- **Table**: `feeds.newyorkfed_guide_sheets` ✅ Ready
- **Dataset Type**: `GuideSheets`
- **Scheduler**: `NewYorkFed_GuideSheets` (1st Monday 11:00 AM) ❌ Inactive
- **Key Columns**: publication_date, guide_type, cusip, settlement_price

### 7. Primary Dealer Statistics
- **Endpoint**: TBD
- **Job**: `run_newyorkfed_pd_statistics.py` 🔶 Stub
- **Table**: `feeds.newyorkfed_pd_statistics` ✅ Ready
- **Dataset Type**: `PDStatistics`
- **Scheduler**: `NewYorkFed_PDStatistics` (Friday 10:10 AM) ❌ Inactive
- **Key Columns**: report_date, dealer_name, security_type, net_financing

### 8. Market Share
- **Endpoint**: TBD
- **Job**: `run_newyorkfed_market_share.py` 🔶 Stub
- **Table**: `feeds.newyorkfed_market_share` ✅ Ready
- **Dataset Type**: `MarketShare`
- **Scheduler**: `NewYorkFed_MarketShare` (Quarterly 11:00 AM) ❌ Inactive
- **Key Columns**: report_date, dealer_name, market_share_pct, rank_position

### 9. Securities Lending
- **Endpoint**: TBD
- **Job**: `run_newyorkfed_securities_lending.py` 🔶 Stub
- **Table**: `feeds.newyorkfed_securities_lending` ✅ Ready
- **Dataset Type**: `SecuritiesLending`
- **Scheduler**: `NewYorkFed_SecLending` (Daily 9:15 AM) ❌ Inactive
- **Key Columns**: operation_date, cusip, par_amount, fee_rate

### 10. Treasury Operations
- **Endpoint**: TBD
- **Job**: `run_newyorkfed_treasury_operations.py` 🔶 Stub
- **Table**: `feeds.newyorkfed_treasury_operations` ✅ Ready
- **Dataset Type**: `TreasuryOperations`
- **Scheduler**: `NewYorkFed_Treasury` (Daily 9:20 AM) ❌ Inactive
- **Key Columns**: operation_date, cusip, total_accepted, stop_out_rate

## Implementation Status Summary

| Component | Implemented | Stub | Total |
|-----------|-------------|------|-------|
| ETL Jobs | 3 | 7 | 10 |
| Feeds Tables | 10 | 0 | 10 |
| Dataset Types | 10 | 0 | 10 |
| Scheduler Jobs | 4 | 7 | 11 |

**Key Points:**
- ✅ **All 10 feeds tables created** - Ready for data when jobs are implemented
- ✅ **All 10 dataset types configured** - Metadata framework complete
- ✅ **3 jobs fully functional** - Reference Rates, SOMA Holdings, Repo Operations
- 🔶 **7 jobs are stubs** - Table schemas ready, need endpoint implementation
- ✅ **4 scheduler jobs active** - 3 implemented + ReverseRepo using same job
- ❌ **7 scheduler jobs inactive** - Will activate after implementation

## Next Steps for Stub Implementation

For each stub job (4-10), the implementation process is:

1. **Research API Endpoint** - Find exact endpoint URL in NewYorkFed API docs
2. **Update API Client** - Add convenience method to `newyorkfed_client.py`
3. **Implement Job** - Update stub job with:
   - Correct endpoint path in `extract()`
   - Field mapping in `transform()`
   - Table name in `load()`
4. **Test** - Run with `--dry-run`, then verify data load
5. **Activate Scheduler** - Update `is_active = TRUE` in scheduler config

## Testing Fresh Database

To verify all tables are created correctly:

```bash
# Stop and recreate database
docker compose down -v
docker compose up -d db

# Wait for init
sleep 10

# List all NewYorkFed tables (should show 10)
docker compose exec db psql -U tangerine_admin -d tangerine_db -c "\dt feeds.newyorkfed*"

# Verify count
docker compose exec db psql -U tangerine_admin -d tangerine_db -c \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'feeds' AND table_name LIKE 'newyorkfed_%';"
```

Expected result: **10 tables**

---

**Last Updated**: February 6, 2026
**Status**: Schema complete for all 10 API categories
