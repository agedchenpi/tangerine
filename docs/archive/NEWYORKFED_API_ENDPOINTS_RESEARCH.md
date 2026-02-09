# NewYorkFed API Endpoints Research Results

**Date:** 2026-02-06
**Status:** ✅ ENDPOINTS FOUND

## Summary

Both PD Statistics and Market Share API endpoints exist and have data available. The stub implementations can be completed.

## Primary Dealer Statistics Endpoints

### Available Endpoints

1. **Latest by Series Break:** `/api/pd/latest/{seriesbreak}.{format}`
   - Example: `/api/pd/latest/SBN2024.json`
   - Returns: Time series data for the latest week in the specified series break
   - **Status:** ✅ HAS DATA (112KB JSON response with hundreds of data points)

2. **List Series Breaks:** `/api/pd/list/seriesbreaks.{format}`
   - Returns: List of available series breaks with date ranges
   - **Current Series Breaks:**
     - SBP2001: Jan 1998 to Jun 2001
     - SBP2013: Jul 2001 to Mar 2013
     - SBN2013: Apr 2013 to Dec 2014
     - SBN2015: Jan 2015 to Dec 2021
     - SBN2022: Jan 2022 to Jun 2024
     - **SBN2024: Jul 2024 to present (ACTIVE)**

3. **All Time Series CSV:** `/api/pd/get/all/timeseries.csv`
   - Returns: Complete historical time series data

4. **List Time Series:** `/api/pd/list/timeseries.{format}`
   - Returns: List of available time series keys

5. **List As-Of Dates:** `/api/pd/list/asof.{format}`
   - Returns: Available report dates

6. **Get by As-Of Date:** `/api/pd/get/asof/{date}.{format}`
   - Returns: Data for a specific date

7. **Get Time Series:** `/api/pd/get/{timeseries}.{format}`
   - Returns: Specific time series data

8. **Get Series Break + Time Series:** `/api/pd/get/{seriesbreak}/timeseries/{timeseries}.{format}`
   - Returns: Specific time series within a series break

### Data Structure

PD Statistics returns time series data with:
- `asofdate`: Report date (YYYY-MM-DD)
- `keyid`: Time series key (e.g., "PDWOTIPSC", "PDABTOTC")
- `value`: Numeric value or "*" for suppressed data

Example record:
```json
{
  "asofdate": "2026-01-28",
  "keyid": "PDWOTIPSC",
  "value": "10035"
}
```

### Recommended Implementation

Use the **latest by series break** endpoint to get current week data:
- Endpoint: `/api/pd/latest/SBN2024.json`
- Response path: `pd.timeseries`
- Returns: Array of time series records
- Update strategy: Fetch latest weekly data on schedule

## Market Share Endpoints

### Available Endpoints

1. **Quarterly Latest:** `/api/marketshare/qtrly/latest.{format}`
   - Returns: Latest quarterly market share data
   - **Status:** ✅ HAS DATA (large JSON response, ~20KB)

2. **Year-to-Date Latest:** `/api/marketshare/ytd/latest.{format}`
   - Returns: Latest year-to-date market share data
   - **Status:** ✅ HAS DATA (verified working)

### Data Structure

Market Share returns quintile distribution data:
- `releaseDate`: Publication date
- `title`: Period description
- `numDealers`: Number of dealers per quintile
- `interDealerBrokers`: Array of security type market shares

Example record:
```json
{
  "securityType": "U.S. TREASURY SECURITIES (EXCLUDING TIPS)",
  "security": "TREASURY BILLS",
  "percentFirstQuintRange": ">=6.22",
  "percentFirstQuintMktShare": "49.58",
  "percentSecondQuintRange": "4.99 - 6.17",
  "percentSecondQuintMktShare": "27.81",
  "dailyAvgVolInMillions": 43832.1
}
```

### Recommended Implementation

Use **both quarterly and YTD endpoints**:
- Quarterly: `/api/marketshare/qtrly/latest.json`
  - Response path: `pd.marketshare.qtrly`
- YTD: `/api/marketshare/ytd/latest.json`
  - Response path: `pd.marketshare.ytd`
- Update strategy: Fetch on schedule (quarterly releases typically)

## Implementation Plan

### 1. Update NewYorkFedAPIClient

Add two new methods to `etl/clients/newyorkfed_client.py`:

```python
def get_pd_statistics(self, seriesbreak: str = 'SBN2024') -> List[Dict]:
    """
    Fetch Primary Dealer statistics for latest period.

    Args:
        seriesbreak: Series break code (default: current series SBN2024)

    Returns:
        List of time series dictionaries
    """
    return self.fetch_endpoint(
        endpoint_path=f'/api/pd/latest/{seriesbreak}.{{format}}',
        response_root_path='pd.timeseries'
    )

def get_market_share(self, period: str = 'ytd') -> List[Dict]:
    """
    Fetch market share data (quarterly or year-to-date).

    Args:
        period: 'qtrly' or 'ytd' (default: 'ytd')

    Returns:
        List of market share records
    """
    return self.fetch_endpoint(
        endpoint_path=f'/api/marketshare/{period}/latest.{{format}}',
        response_root_path=f'pd.marketshare.{period}.interDealerBrokers'
    )
```

### 2. Implement ETL Jobs

#### PD Statistics Job (`etl/jobs/run_newyorkfed_pd_statistics.py`)

- Extract: Call `client.get_pd_statistics('SBN2024')`
- Transform: Map fields to table schema
  - `report_date` ← `asofdate`
  - `report_type` ← Extract from keyid prefix
  - `security_type` ← Parse from keyid
  - Numeric fields ← `value` (handle "*" as NULL)
- Load: Insert into `feeds.newyorkfed_pd_statistics`

#### Market Share Job (`etl/jobs/run_newyorkfed_market_share.py`)

- Extract: Call both `client.get_market_share('qtrly')` and `client.get_market_share('ytd')`
- Transform: Flatten quintile data
  - `report_date` ← `releaseDate`
  - `security_type` ← `securityType`
  - `market_segment` ← `security`
  - Parse quintile ranges and percentages
- Load: Insert into `feeds.newyorkfed_market_share`

### 3. Table Schema Compatibility

Current schemas support the data:

**newyorkfed_pd_statistics:**
- ✅ `report_date DATE NOT NULL` ← maps to `asofdate`
- ✅ `report_type VARCHAR(50)` ← can extract from keyid
- ✅ `dealer_name VARCHAR(100)` ← may be NULL (aggregate data)
- ✅ `security_type VARCHAR(50)` ← can parse from keyid
- ✅ Multiple numeric fields for financing/securities data

**newyorkfed_market_share:**
- ✅ `report_date DATE NOT NULL` ← maps to `releaseDate`
- ✅ `participant VARCHAR(100)` ← use "QUINTILE_1" etc.
- ✅ `market_segment VARCHAR(100)` ← maps to `security`
- ✅ `share_percentage NUMERIC(10, 2)` ← quintile percentages

## Testing Verification

```bash
# Test PD Statistics endpoint
curl "https://markets.newyorkfed.org/api/pd/list/seriesbreaks.json"
curl "https://markets.newyorkfed.org/api/pd/latest/SBN2024.json" | jq '.pd.timeseries | length'

# Test Market Share endpoints
curl "https://markets.newyorkfed.org/api/marketshare/ytd/latest.json" | jq '.pd.marketshare.ytd.title'
curl "https://markets.newyorkfed.org/api/marketshare/qtrly/latest.json" | jq '.pd.marketshare.qtrly.title'
```

## Next Steps

1. ✅ **Research Complete** - Both APIs found and verified
2. ⏭️ **Implementation** - Add client methods
3. ⏭️ **Jobs** - Replace stub implementations with full ETL
4. ⏭️ **Testing** - Verify data loads into tables
5. ⏭️ **Scheduling** - Add to regular job runner

## Conclusion

**Both PD Statistics and Market Share endpoints are available and functional.**

The stub implementations should be upgraded to full ETL jobs. This will bring the NewYorkFed integration to **10/10 complete jobs** (currently 8/10).
