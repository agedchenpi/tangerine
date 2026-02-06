# NewYorkFed Markets API Integration Plan

## Overview

Integrate the Federal Reserve Bank of New York Markets API into Tangerine's ETL framework to import reference rates, repo operations, SOMA holdings, and other market data. The implementation follows the existing API pattern (gmail_inbox_processor) while extending the config-driven architecture to support both file and API imports.

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

## Implementation Steps

### Phase 1: Schema Extension (Foundation)

**1.1 Create Migration Script**

File: `/opt/tangerine/schema/migrations/add_api_columns_to_timportconfig.sql`

Add columns:
```sql
-- API-specific columns (all nullable for backward compatibility)
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS
    import_mode VARCHAR(20) DEFAULT 'file' CHECK (import_mode IN ('file', 'api'));

ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_base_url VARCHAR(255);
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_endpoint_path VARCHAR(255);
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_http_method VARCHAR(10) DEFAULT 'GET';
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_response_format VARCHAR(10) DEFAULT 'json';
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_query_params JSONB;
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_request_headers JSONB;
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_auth_type VARCHAR(50) DEFAULT 'none';
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_auth_credentials JSONB;
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_rate_limit_rpm INT;
ALTER TABLE dba.timportconfig ADD COLUMN IF NOT EXISTS api_response_root_path VARCHAR(255);

-- Modify constraint: allow empty directories for API imports
ALTER TABLE dba.timportconfig DROP CONSTRAINT IF EXISTS valid_directories;
ALTER TABLE dba.timportconfig ADD CONSTRAINT valid_directories CHECK (
    (import_mode = 'file' AND source_directory != archive_directory
        AND source_directory ~ '^/.*[^/]$' AND archive_directory ~ '^/.*[^/]$')
    OR (import_mode = 'api')
);
```

**1.2 Apply Migration**
```bash
docker compose exec db psql -U tangerine_admin -d tangerine_db -f /app/schema/migrations/add_api_columns_to_timportconfig.sql
```

**1.3 Verify Backward Compatibility**
- Ensure existing file-based imports still work
- Run regression tests: `pytest tests/integration/etl/test_generic_import.py -v`

### Phase 2: API Client Implementation

**2.1 Create NewYorkFedAPIClient**

File: `/opt/tangerine/etl/clients/newyorkfed_client.py`

```python
from typing import Dict, List, Optional, Any
from etl.base.api_client import BaseAPIClient

class NewYorkFedAPIClient(BaseAPIClient):
    """Client for Federal Reserve Bank of New York Markets API."""

    def __init__(self, base_url='https://markets.newyorkfed.org'):
        super().__init__(base_url=base_url, rate_limit=60)

    def get_headers(self) -> Dict[str, str]:
        # Public API - no auth needed
        return {'Accept': 'application/json'}

    def fetch_endpoint(
        self,
        endpoint_path: str,
        response_format: str = 'json',
        query_params: Optional[Dict] = None,
        response_root_path: Optional[str] = None
    ) -> List[Dict]:
        # Replace {format} placeholder
        endpoint = endpoint_path.replace('{format}', response_format)

        # Fetch data
        response = self.get(endpoint, params=query_params)

        # Extract nested data if root path specified
        if response_root_path and isinstance(response, dict):
            data = self._extract_by_path(response, response_root_path)
        else:
            data = response if isinstance(response, list) else [response]

        return data

    def _extract_by_path(self, data: dict, path: str) -> List[Dict]:
        """Extract nested data using dot notation (e.g., 'refRates' or 'data.results')."""
        parts = path.split('.')
        result = data
        for part in parts:
            result = result.get(part, [])
        return result if isinstance(result, list) else [result]
```

**2.2 Test API Client**
```bash
# Manual test
python -c "
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
client = NewYorkFedAPIClient()
data = client.fetch_endpoint('/api/rates/all/latest.json', response_root_path='refRates')
print(f'Fetched {len(data)} records')
print(data[0])
"
```

### Phase 3: Category-Specific Jobs

**3.1 Create Reference Rates Job (Template)**

File: `/opt/tangerine/etl/jobs/run_newyorkfed_reference_rates.py`

```python
from datetime import date, datetime, timedelta
from typing import List, Dict
import argparse
import sys

from etl.base.etl_job import BaseETLJob
from etl.clients.newyorkfed_client import NewYorkFedAPIClient
from etl.loaders.postgres_loader import PostgresLoader

class NewYorkFedReferenceRatesJob(BaseETLJob):
    """Import Federal Reserve reference rates (SOFR, EFFR, OBFR, TGCR, BGCR)."""

    def __init__(self, endpoint_type='latest', run_date=None, dry_run=False):
        super().__init__(
            run_date=run_date or date.today(),
            dataset_type='ReferenceRates',
            data_source='NewYorkFed',
            dry_run=dry_run
        )
        self.endpoint_type = endpoint_type
        self.client = NewYorkFedAPIClient()
        self.loader = PostgresLoader(schema='feeds')

    def extract(self) -> List[Dict]:
        """Fetch reference rates from NewYorkFed API."""
        if self.endpoint_type == 'latest':
            return self.client.fetch_endpoint(
                '/api/rates/all/latest.json',
                response_root_path='refRates'
            )
        else:  # search
            end_date = self.run_date
            start_date = self.run_date - timedelta(days=30)
            return self.client.fetch_endpoint(
                '/api/rates/all/search.json',
                query_params={
                    'startDate': start_date.strftime('%Y-%m-%d'),
                    'endDate': end_date.strftime('%Y-%m-%d')
                },
                response_root_path='refRates'
            )

    def transform(self, data: List[Dict]) -> List[Dict]:
        """Normalize field names and add audit columns."""
        transformed = []
        for record in data:
            transformed.append({
                'rate_type': record.get('type'),
                'effective_date': record.get('effectiveDate'),
                'rate_percent': record.get('percentRate'),
                'volume_billions': record.get('volumeInBillions'),
                'percentile_1': record.get('percentile1'),
                'percentile_25': record.get('percentile25'),
                'percentile_75': record.get('percentile75'),
                'percentile_99': record.get('percentile99'),
                'target_range_from': record.get('targetRangeFrom'),
                'target_range_to': record.get('targetRangeTo'),
                'created_date': datetime.now(),
                'created_by': self.username
            })
        return transformed

    def load(self, data: List[Dict]):
        """Load to feeds.newyorkfed_reference_rates."""
        if not self.dry_run:
            self.records_loaded = self.loader.load(
                table='newyorkfed_reference_rates',
                data=data,
                dataset_id=self.dataset_id
            )
        else:
            self.logger.info(f"DRY RUN: Would load {len(data)} records")
            self.records_loaded = len(data)

def main():
    parser = argparse.ArgumentParser(description='Import NewYorkFed reference rates')
    parser.add_argument('--endpoint-type', choices=['latest', 'search'],
                       default='latest', help='Endpoint type to fetch')
    parser.add_argument('--dry-run', action='store_true',
                       help='Validate without database writes')
    args = parser.parse_args()

    job = NewYorkFedReferenceRatesJob(
        endpoint_type=args.endpoint_type,
        dry_run=args.dry_run
    )
    success = job.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
```

**3.2 Replicate for Remaining 9 Categories**
- Follow same structure for each category
- Adjust endpoints, field mappings, target tables
- See API documentation for specific endpoint paths and response structures

### Phase 4: Configuration Setup

**4.1 Create Data Sources & Dataset Types**

File: `/opt/tangerine/scripts/setup_newyorkfed_datasources.sql`

```sql
-- Insert data source
INSERT INTO dba.tdatasource (sourcename, description, createdby)
VALUES ('NewYorkFed', 'Federal Reserve Bank of New York Markets API', 'admin')
ON CONFLICT (sourcename) DO NOTHING;

-- Insert dataset types (10 categories)
INSERT INTO dba.tdatasettype (typename, description, createdby) VALUES
    ('ReferenceRates', 'Reference rates (SOFR, EFFR, OBFR, TGCR, BGCR)', 'admin'),
    ('AgencyMBS', 'Agency mortgage-backed securities operations', 'admin'),
    ('FXSwaps', 'Central bank liquidity swaps', 'admin'),
    ('GuideSheets', 'Guide sheet publications', 'admin'),
    ('PDStatistics', 'Primary dealer statistics', 'admin'),
    ('MarketShare', 'Primary dealer market share', 'admin'),
    ('RepoOperations', 'Repo and reverse repo operations', 'admin'),
    ('SecuritiesLending', 'Securities lending operations', 'admin'),
    ('SOMAHoldings', 'System Open Market Account holdings', 'admin'),
    ('TreasuryOperations', 'Treasury securities operations', 'admin')
ON CONFLICT (typename) DO NOTHING;
```

**4.2 Setup Scheduler Jobs**

File: `/opt/tangerine/scripts/setup_newyorkfed_schedules.sql`

```sql
-- Daily imports at 9 AM EST (staggered by 5 minutes)
INSERT INTO dba.tscheduler (
    job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
    script_path, is_active
) VALUES
    ('NewYorkFed_ReferenceRates', 'custom', '0', '9', '*', '*', '*',
     'python /app/etl/jobs/run_newyorkfed_reference_rates.py --endpoint-type latest', TRUE),
    ('NewYorkFed_AgencyMBS', 'custom', '5', '9', '*', '*', '*',
     'python /app/etl/jobs/run_newyorkfed_agency_mbs.py', TRUE),
    ('NewYorkFed_FXSwaps', 'custom', '10', '9', '*', '*', '*',
     'python /app/etl/jobs/run_newyorkfed_fx_swaps.py', TRUE),
    ('NewYorkFed_Repo', 'custom', '15', '9', '*', '*', '*',
     'python /app/etl/jobs/run_newyorkfed_repo.py', TRUE),
    ('NewYorkFed_SecLending', 'custom', '20', '9', '*', '*', '*',
     'python /app/etl/jobs/run_newyorkfed_securities_lending.py', TRUE),
    ('NewYorkFed_Treasury', 'custom', '25', '9', '*', '*', '*',
     'python /app/etl/jobs/run_newyorkfed_treasury.py', TRUE),
    -- Weekly jobs
    ('NewYorkFed_PDStatistics', 'custom', '0', '10', '*', '*', '5',
     'python /app/etl/jobs/run_newyorkfed_pd_statistics.py', TRUE),
    ('NewYorkFed_SOMA', 'custom', '0', '10', '*', '*', '4',
     'python /app/etl/jobs/run_newyorkfed_soma_holdings.py', TRUE),
    -- Quarterly jobs
    ('NewYorkFed_MarketShare', 'custom', '0', '11', '1', '1,4,7,10', '*',
     'python /app/etl/jobs/run_newyorkfed_market_share.py', TRUE),
    -- Monthly jobs
    ('NewYorkFed_GuideSheets', 'custom', '0', '11', '1-7', '*', '1-5',
     'python /app/etl/jobs/run_newyorkfed_guide_sheets.py', TRUE)
ON CONFLICT (job_name) DO NOTHING;
```

### Phase 5: Testing

**5.1 Unit Tests**

File: `/opt/tangerine/tests/etl/test_newyorkfed_client.py`

```python
import pytest
from unittest.mock import Mock, patch
from etl.clients.newyorkfed_client import NewYorkFedAPIClient

class TestNewYorkFedAPIClient:
    @pytest.fixture
    def client(self):
        return NewYorkFedAPIClient()

    def test_format_replacement(self, client):
        endpoint = '/api/rates/all/latest.{format}'
        result = endpoint.replace('{format}', 'json')
        assert result == '/api/rates/all/latest.json'

    @patch('etl.clients.newyorkfed_client.requests.Session')
    def test_fetch_endpoint(self, mock_session, client):
        mock_response = Mock()
        mock_response.json.return_value = {
            'refRates': [{'type': 'SOFR', 'rate': 5.32}]
        }
        mock_session.return_value.request.return_value = mock_response

        data = client.fetch_endpoint(
            '/api/rates/all/latest.{format}',
            response_root_path='refRates'
        )

        assert len(data) == 1
        assert data[0]['type'] == 'SOFR'
```

**5.2 Integration Tests**

```bash
# Test each job with dry-run
python etl/jobs/run_newyorkfed_reference_rates.py --dry-run
python etl/jobs/run_newyorkfed_agency_mbs.py --dry-run
# ... repeat for all 10 jobs

# Test with database writes (dev environment)
python etl/jobs/run_newyorkfed_reference_rates.py

# Verify data loaded
docker compose exec db psql -U tangerine_admin -d tangerine_db -c "
SELECT COUNT(*) FROM feeds.newyorkfed_reference_rates;
SELECT * FROM feeds.newyorkfed_reference_rates LIMIT 5;
"
```

**5.3 Run Test Suite**
```bash
pytest tests/etl/test_newyorkfed_client.py -v
pytest tests/etl/test_newyorkfed_integration.py -v --integration
```

## Verification

### End-to-End Verification Steps

1. **Schema Migration Verification**
   ```sql
   -- Verify new columns exist
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_schema = 'dba' AND table_name = 'timportconfig'
   AND column_name LIKE 'api_%' OR column_name = 'import_mode';

   -- Verify existing configs still work
   SELECT config_id, config_name, import_mode
   FROM dba.timportconfig
   WHERE import_mode = 'file' OR import_mode IS NULL;
   ```

2. **API Client Verification**
   ```bash
   # Test live API call
   python -c "
   from etl.clients.newyorkfed_client import NewYorkFedAPIClient
   client = NewYorkFedAPIClient()
   data = client.fetch_endpoint('/api/rates/all/latest.json', response_root_path='refRates')
   assert len(data) > 0, 'No data returned'
   assert 'type' in data[0], 'Missing type field'
   print(f'✓ Fetched {len(data)} records')
   "
   ```

3. **Job Execution Verification**
   ```bash
   # Run reference rates job
   python etl/jobs/run_newyorkfed_reference_rates.py

   # Check logs
   docker compose exec tangerine tail -f /app/logs/etl_*.log

   # Verify dataset created
   docker compose exec db psql -U tangerine_admin -d tangerine_db -c "
   SELECT datasetid, label, datasetdate, datastatusid
   FROM dba.tdataset
   WHERE datasourceid = (SELECT datasourceid FROM dba.tdatasource WHERE sourcename = 'NewYorkFed')
   ORDER BY datasetid DESC LIMIT 1;
   "

   # Verify feeds table created and populated
   docker compose exec db psql -U tangerine_admin -d tangerine_db -c "
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'feeds' AND table_name LIKE 'newyorkfed_%';

   SELECT COUNT(*) FROM feeds.newyorkfed_reference_rates;
   SELECT * FROM feeds.newyorkfed_reference_rates ORDER BY created_date DESC LIMIT 3;
   "
   ```

4. **Scheduler Verification**
   ```sql
   -- Verify scheduled jobs exist
   SELECT scheduler_id, job_name, job_type,
          cron_minute, cron_hour, is_active
   FROM dba.tscheduler
   WHERE job_name LIKE 'NewYorkFed_%';

   -- Verify cron syntax is valid
   SELECT job_name,
          cron_minute || ' ' || cron_hour || ' ' || cron_day || ' ' ||
          cron_month || ' ' || cron_weekday as cron_expression
   FROM dba.tscheduler
   WHERE job_name LIKE 'NewYorkFed_%';
   ```

5. **Data Quality Checks**
   ```sql
   -- Check for null critical fields
   SELECT rate_type, COUNT(*)
   FROM feeds.newyorkfed_reference_rates
   WHERE effective_date IS NULL OR rate_percent IS NULL
   GROUP BY rate_type;

   -- Verify date ranges
   SELECT MIN(effective_date), MAX(effective_date)
   FROM feeds.newyorkfed_reference_rates;

   -- Check for duplicates
   SELECT rate_type, effective_date, COUNT(*)
   FROM feeds.newyorkfed_reference_rates
   GROUP BY rate_type, effective_date
   HAVING COUNT(*) > 1;
   ```

## Key Design Decisions

1. **Extend timportconfig vs separate table**: Extended timportconfig with nullable API columns for single source of truth while maintaining backward compatibility

2. **Category-specific jobs vs generic**: Category-specific jobs provide type safety, better monitoring, and easier debugging despite more files

3. **JSON format**: JSON chosen as primary format for native parsing and nested structure support

4. **Daily scheduling**: Most endpoints updated daily; weekly/quarterly for slower-changing data

5. **Rate limiting**: Conservative 60 req/min with staggered start times to avoid API throttling

## Potential Issues & Mitigations

- **API rate limiting**: Staggered job start times (5-min intervals), conservative rate limit, exponential backoff
- **API schema changes**: Graceful degradation, logging warnings, manual quarterly reviews
- **Nested JSON structures**: Flexible response_root_path config per endpoint
- **Large datasets**: Pagination support, date range filtering, batch processing
- **Backward compatibility**: All new columns nullable, default import_mode='file', comprehensive regression tests
