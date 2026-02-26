# New Import Job: Bank of England SONIA Rates

## Context

Adding a daily ETL job to pull SONIA (Sterling Overnight Index Average) rates from the Bank of England's Interactive Statistical Database (IADB). The BoE publishes SONIA daily at ~10:00 AM London time. The job will run daily at 9:30 AM CST (3:30 PM UTC / 15:30).

The user has provided a working standalone Python script that fetches SONIA data via CSV endpoint. We need to adapt it into the Tangerine ETL framework following established patterns (BaseETLJob, BaseAPIClient, PostgresLoader).

## Files to Create

| # | File | Purpose |
|---|------|---------|
| 1 | `etl/clients/bankofengland_client.py` | API client extending `BaseAPIClient` — fetches CSV from BoE IADB |
| 2 | `etl/jobs/run_bankofengland_sonia_rates.py` | ETL job extending `BaseETLJob` — extract/transform/load lifecycle |
| 3 | `schema/feeds/bankofengland_sonia_rates.sql` | Feed table `feeds.bankofengland_sonia_rates` |
| 4 | `schema/dba/data/bankofengland_reference_data.sql` | Seed data: `BankOfEngland` datasource + `Rates` dataset type |
| 5 | `schema/dba/data/bankofengland_scheduler_jobs.sql` | Scheduler job: daily at 9:30 AM CST |

## Files to Modify

| File | Change |
|------|--------|
| `schema/init.sh` | Add lines to source the 3 new SQL files |

## Implementation Details

### 1. `etl/clients/bankofengland_client.py`

Extends `BaseAPIClient` (from `etl/base/api_client.py`). The BoE IADB returns CSV, not JSON, so we override the fetch pattern:

- **base_url**: `https://www.bankofengland.co.uk`
- **endpoint**: `/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes`
- **Series code**: `IUDSOIA` (SONIA daily rate)
- **Date format**: `DD/Mon/YYYY` (e.g. `28/Nov/2025`)
- **get_headers()**: Returns `User-Agent` header (BoE requires a browser-like UA)
- **get_sonia_rates(days=60)**: Builds query params, calls `_make_request('GET', ...)`, parses CSV from `response.text` using `csv.DictReader` (not pandas — keep dependencies minimal), returns `List[Dict]` with keys `date` and `rate`
- Note: `BaseAPIClient.get()` calls `.json()` on the response, so we need to call `_make_request()` directly and parse the CSV text ourselves

### 2. `etl/jobs/run_bankofengland_sonia_rates.py`

Follows the exact pattern of `run_newyorkfed_reference_rates.py`:

```python
class BankOfEnglandSONIARatesJob(BaseETLJob):
    def __init__(self, days=60, run_date=None, dry_run=False):
        super().__init__(
            run_date=run_date or date.today(),
            dataset_type='Rates',
            data_source='BankOfEngland',
            dry_run=dry_run,
            username='etl_user',
            dataset_label=f'SONIA_{run_date or date.today()}'
        )
        self.days = days
        self.client = None
        self.loader = None
```

- **setup()**: Init `BankOfEnglandAPIClient()` + `PostgresLoader(schema='feeds')`
- **extract()**: Call `self.client.get_sonia_rates(days=self.days)` → returns list of `{"date": "03 Jan 2025", "rate": "4.5500"}` dicts
- **transform()**: Parse dates (`datetime.strptime(d, '%d %b %Y').date()`), coerce rate to float, skip NaN/missing, add `created_date`/`created_by` audit columns. Output: `[{"effective_date": date, "rate_percent": float, "created_date": ..., "created_by": ...}]`
- **load()**: `self.loader.load(table='bankofengland_sonia_rates', data=data, dataset_id=self.dataset_id)`
- **cleanup()**: Close client
- **main()**: argparse with `--days` (default 60), `--dry-run`, `--date`

### 3. `schema/feeds/bankofengland_sonia_rates.sql`

Follow exact pattern of `schema/feeds/newyorkfed_reference_rates.sql`:

```sql
CREATE TABLE feeds.bankofengland_sonia_rates (
    record_id SERIAL PRIMARY KEY,
    datasetid INT NOT NULL,

    -- Rate data
    effective_date DATE NOT NULL,
    rate_percent NUMERIC(10, 4),

    -- Audit columns
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT CURRENT_USER,

    CONSTRAINT uq_boe_sonia_rates UNIQUE (effective_date, datasetid),
    CONSTRAINT fk_boe_sonia_rates_dataset FOREIGN KEY (datasetid) REFERENCES dba.tdataset(datasetid)
);
```

Plus indexes on `datasetid` and `effective_date`, comments, and GRANT statements for `app_ro`, `app_rw`, `admin`.

### 4. `schema/dba/data/bankofengland_reference_data.sql`

Follow pattern of `newyorkfed_reference_data.sql`:

```sql
-- Insert BankOfEngland data source
IF NOT EXISTS (SELECT 1 FROM dba.tdatasource WHERE sourcename = 'BankOfEngland') THEN
    INSERT INTO dba.tdatasource (sourcename, description, createdby)
    VALUES ('BankOfEngland', 'Bank of England Interactive Statistical Database (IADB)', 'admin');
END IF;

-- Insert dataset type
INSERT INTO dba.tdatasettype (typename, description, createdby) VALUES
    ('Rates', 'Interest rates and benchmark rates', 'admin')
ON CONFLICT (typename) DO NOTHING;
```

### 5. `schema/dba/data/bankofengland_scheduler_jobs.sql`

Follow pattern of `newyorkfed_scheduler_jobs.sql`:

- **9:30 AM CST** = cron_minute=`30`, cron_hour=`15` (UTC, since server runs UTC; CST = UTC-6, so 9:30 CST = 15:30 UTC)
- Weekdays only (Mon-Fri) since SONIA only publishes on business days: cron_weekday=`1-5`

```sql
INSERT INTO dba.tscheduler (
    job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
    script_path, is_active
) VALUES
    ('BankOfEngland_SONIA', 'custom', '30', '15', '*', '*', '1-5',
     'etl/jobs/run_bankofengland_sonia_rates.py', TRUE)
ON CONFLICT (job_name) DO UPDATE SET
    script_path = EXCLUDED.script_path,
    is_active = EXCLUDED.is_active;
```

### 6. `schema/init.sh` modifications

Add 3 new lines in the appropriate positions:

```bash
# After newyorkfed data lines (~line 59-63), add:
$PSQL -f /app/schema/dba/data/bankofengland_reference_data.sql
$PSQL -f /app/schema/dba/data/bankofengland_scheduler_jobs.sql

# After newyorkfed feeds table lines (~line 79), add:
$PSQL -f /app/schema/feeds/bankofengland_sonia_rates.sql
```

## Design Decisions

1. **Dedicated API client** (`bankofengland_client.py`) rather than inline HTTP calls — follows existing pattern, enables reuse if more BoE series are added later
2. **CSV parsing via stdlib csv module** — the user's script uses pandas, but existing codebase doesn't use pandas for API clients. Using `csv.DictReader` on `io.StringIO(response.text)` keeps it lightweight and consistent
3. **Simple table schema** — SONIA has just 2 domain fields (date + rate). No need for a complex schema
4. **Weekday-only schedule** — SONIA is only published on London business days. Mon-Fri cron avoids no-data runs on weekends
5. **60-day rolling window** — matches the user's default. Each run will fetch overlapping data; the UNIQUE constraint on `(effective_date, datasetid)` prevents duplicates within a dataset, and each run creates a new dataset

## Verification

1. **Run the seed SQL** against the live DB to create the datasource, dataset type, and scheduler entry
2. **Create the feeds table** by running the table SQL
3. **Regenerate crontab**: `docker compose exec tangerine python etl/jobs/generate_crontab.py --apply --preview --update-next-run`
4. **Dry run test**: `docker compose exec tangerine python etl/jobs/run_bankofengland_sonia_rates.py --dry-run`
5. **Live run test**: `docker compose exec tangerine python etl/jobs/run_bankofengland_sonia_rates.py`
6. **Verify data**: `SELECT COUNT(*), MIN(effective_date), MAX(effective_date) FROM feeds.bankofengland_sonia_rates;`
7. **Verify dataset status**: `SELECT label, datasetdate, statusname FROM dba.vdataset WHERE datasource = 'BankOfEngland';`
