# Plan: Market Index ETL Imports (YFinance)

## Context

Add three new ETL pipelines for daily market index price data, following the exact same Individual Script Pattern as the recently-implemented commodity and crypto pipelines. The user wants US + Global + Sector coverage, grouped into separate feed tables — one per logical group, one script per group.

All data comes from **YFinance** (already installed). No new library dependencies. The `'yfinance'` prefix_map entry already exists in `import_utils.py`. The `datasettype = 'Index'` does not yet exist in `tdatasettype` — a reference data SQL file will create it.

---

## Groups & Tickers

### Group 1 — US Indexes (`feeds.yfinance_us_indexes`)
| Ticker | Name |
|--------|------|
| `^GSPC` | S&P 500 |
| `^IXIC` | NASDAQ Composite |
| `^NDX`  | NASDAQ-100 |
| `^DJI`  | Dow Jones Industrial Average |
| `^RUT`  | Russell 2000 |
| `^VIX`  | CBOE Volatility Index |
| `^TNX`  | 10-Year Treasury Yield |
| `^TYX`  | 30-Year Treasury Yield |

### Group 2 — Global Indexes (`feeds.yfinance_global_indexes`)
| Ticker | Name | Region |
|--------|------|--------|
| `^FTSE`   | FTSE 100       | Europe |
| `^GDAXI`  | DAX            | Europe |
| `^FCHI`   | CAC 40         | Europe |
| `^STOXX50E` | Euro Stoxx 50 | Europe |
| `^N225`   | Nikkei 225     | Asia |
| `^HSI`    | Hang Seng      | Asia |
| `^AXJO`   | ASX 200        | Asia |

### Group 3 — US Sector ETFs (`feeds.yfinance_sector_etfs`)
| Ticker | Name | Sector |
|--------|------|--------|
| `XLF`  | Financial Select Sector SPDR  | Financials |
| `XLK`  | Technology Select Sector SPDR | Technology |
| `XLE`  | Energy Select Sector SPDR     | Energy |
| `XLV`  | Health Care Select Sector SPDR | Health Care |
| `XLI`  | Industrial Select Sector SPDR | Industrials |
| `XLU`  | Utilities Select Sector SPDR  | Utilities |
| `XLB`  | Materials Select Sector SPDR  | Materials |
| `XLRE` | Real Estate Select Sector SPDR | Real Estate |
| `XLY`  | Consumer Discretionary Select Sector SPDR | Consumer Discretionary |
| `XLP`  | Consumer Staples Select Sector SPDR | Consumer Staples |
| `XLC`  | Communication Services Select Sector SPDR | Communication Services |

---

## Files to Create / Modify

### New files (9)
| File | Purpose |
|------|---------|
| `schema/dba/data/yfinance_index_reference_data.sql` | Insert `'Index'` into `tdatasettype`; re-ensure `'YFinance'` datasource exists |
| `schema/feeds/yfinance_us_indexes.sql` | Feed table DDL |
| `schema/feeds/yfinance_global_indexes.sql` | Feed table DDL |
| `schema/feeds/yfinance_sector_etfs.sql` | Feed table DDL |
| `schema/dba/data/yfinance_index_import_configs.sql` | 3 `timportconfig` INSERTs |
| `schema/dba/data/yfinance_index_scheduler_jobs.sql` | 3 `tscheduler` INSERTs |
| `etl/jobs/run_yfinance_us_indexes.py` | ETL script — CONFIG: `YFinance_US_Indexes` |
| `etl/jobs/run_yfinance_global_indexes.py` | ETL script — CONFIG: `YFinance_Global_Indexes` |
| `etl/jobs/run_yfinance_sector_etfs.py` | ETL script — CONFIG: `YFinance_Sector_ETFs` |

### Modified files (2)
| File | Change |
|------|--------|
| `etl/clients/yfinance_client.py` | Add private `_download_ticker_prices()` helper + `US_INDEXES`, `GLOBAL_INDEXES`, `SECTOR_ETFS` dicts + 3 public fetch methods |
| `schema/init.sh` | Add 4 new SQL file references after existing yfinance entries |

**No changes needed to:**
- `requirements/base.txt` — yfinance already installed
- `etl/base/import_utils.py` — `'yfinance': 'YFinance_'` prefix_map already exists

---

## Step-by-Step Changes

### 1. `schema/dba/data/yfinance_index_reference_data.sql`
```sql
DO $$ BEGIN
    INSERT INTO dba.tdatasource (sourcename, description, createdby)
    VALUES ('YFinance', 'Yahoo Finance market data', 'admin')
    ON CONFLICT (sourcename) DO NOTHING;

    INSERT INTO dba.tdatasettype (typename, description, createdby)
    VALUES ('Index', 'Market index and benchmark data', 'admin')
    ON CONFLICT (typename) DO NOTHING;
END $$;
```

### 2. Feed Table DDL (3 files)

All follow exact same pattern as `schema/feeds/yfinance_commodities.sql`.

**`yfinance_us_indexes.sql`** — columns:
```sql
record_id SERIAL PK, datasetid INT FK,
symbol VARCHAR(20) NOT NULL,       -- e.g. ^GSPC, ^VIX, ^TNX
index_name VARCHAR(100),           -- e.g. S&P 500
price_date DATE NOT NULL,
open NUMERIC(18,6), high NUMERIC(18,6), low NUMERIC(18,6), close NUMERIC(18,6),
volume BIGINT,
created_date TIMESTAMP, created_by VARCHAR(50),
UNIQUE (symbol, price_date, datasetid)
```
Indexes: `datasetid`, `price_date`, `symbol`

**`yfinance_global_indexes.sql`** — same + `region VARCHAR(50)` (Europe/Asia):
```sql
symbol VARCHAR(20), index_name VARCHAR(100), region VARCHAR(50),
price_date DATE, open/high/low/close NUMERIC(18,6), volume BIGINT
UNIQUE (symbol, price_date, datasetid)
```

**`yfinance_sector_etfs.sql`** — same + `sector VARCHAR(50)` (Technology, Energy, etc.):
```sql
symbol VARCHAR(20), etf_name VARCHAR(100), sector VARCHAR(50),
price_date DATE, open/high/low/close NUMERIC(18,6), volume BIGINT
UNIQUE (symbol, price_date, datasetid)
```

### 3. `schema/dba/data/yfinance_index_import_configs.sql`

One `DO $$ ... $$` block with all 3 INSERTs. Reuses strategy 2 ("Import only"). All share `source_directory='/app/data/source/yfinance'` and `archive_directory='/app/data/archive/yfinance'` (same directory as commodities, different file_pattern per config):

```
config_name            | datasettype | file_pattern                      | target_table
-----------------------|-------------|-----------------------------------|--------------------------
YFinance_US_Indexes    | Index       | yfinance_us_indexes_.*\.json      | feeds.yfinance_us_indexes
YFinance_Global_Indexes| Index       | yfinance_global_indexes_.*\.json  | feeds.yfinance_global_indexes
YFinance_Sector_ETFs   | Index       | yfinance_sector_etfs_.*\.json     | feeds.yfinance_sector_etfs
```

Insert `'Index'` datasettype and `'YFinance'` datasource `ON CONFLICT DO NOTHING` at the top of the block.

### 4. `schema/dba/data/yfinance_index_scheduler_jobs.sql`

All 3 jobs: cron `'0', '23', '*', '*', '1-5'` (23:00 UTC Mon-Fri). Rationale: US/European/Asian markets all settled by this time; `period='5d'` handles any stale-data edge cases.

```
job_name                | script_path
------------------------|----------------------------------------------
YFinance_US_Indexes     | etl/jobs/run_yfinance_us_indexes.py
YFinance_Global_Indexes | etl/jobs/run_yfinance_global_indexes.py
YFinance_Sector_ETFs    | etl/jobs/run_yfinance_sector_etfs.py
```

### 5. `etl/clients/yfinance_client.py` — new methods

Add a **private helper** to eliminate the duplicated MultiIndex download logic:

```python
def _download_ticker_prices(self, tickers: list, period: str = '5d') -> dict:
    """Download OHLCV for tickers. Returns {ticker: {price_date, open, high, low, close, volume}}."""
    df = yf.download(tickers, period=period, progress=False, auto_adjust=False)
    if df is None or df.empty:
        return {}
    results = {}
    if isinstance(df.columns, pd.MultiIndex):
        for ticker in tickers:
            try:
                ticker_df = df.xs(ticker, axis=1, level=1).dropna(subset=['Close'])
                if ticker_df.empty:
                    continue
                row = ticker_df.iloc[-1]
                results[ticker] = {
                    'price_date': ticker_df.index[-1].date().isoformat(),
                    'open': _safe_float(row.get('Open')),
                    'high': _safe_float(row.get('High')),
                    'low': _safe_float(row.get('Low')),
                    'close': _safe_float(row.get('Close')),
                    'volume': _safe_int(row.get('Volume')),
                }
            except Exception as e:
                self.logger.warning(f"Skipping {ticker}: {e}")
    else:
        # Single-ticker fallback
        ticker = tickers[0]
        df_clean = df.dropna(subset=['Close'])
        if not df_clean.empty:
            row = df_clean.iloc[-1]
            results[ticker] = {
                'price_date': df_clean.index[-1].date().isoformat(),
                'open': _safe_float(row.get('Open')),
                'high': _safe_float(row.get('High')),
                'low': _safe_float(row.get('Low')),
                'close': _safe_float(row.get('Close')),
                'volume': _safe_int(row.get('Volume')),
            }
    return results
```

Add 3 dicts + 3 public methods:

```python
US_INDEXES = {
    '^GSPC': 'S&P 500',
    '^IXIC': 'NASDAQ Composite',
    '^NDX':  'NASDAQ-100',
    '^DJI':  'Dow Jones Industrial Average',
    '^RUT':  'Russell 2000',
    '^VIX':  'CBOE Volatility Index',
    '^TNX':  '10-Year Treasury Yield',
    '^TYX':  '30-Year Treasury Yield',
}

GLOBAL_INDEXES = {
    '^FTSE':    ('FTSE 100',    'Europe'),
    '^GDAXI':   ('DAX',         'Europe'),
    '^FCHI':    ('CAC 40',      'Europe'),
    '^STOXX50E':('Euro Stoxx 50','Europe'),
    '^N225':    ('Nikkei 225',  'Asia'),
    '^HSI':     ('Hang Seng',   'Asia'),
    '^AXJO':    ('ASX 200',     'Asia'),
}

SECTOR_ETFS = {
    'XLF':  ('Financial Select Sector SPDR',           'Financials'),
    'XLK':  ('Technology Select Sector SPDR',          'Technology'),
    'XLE':  ('Energy Select Sector SPDR',              'Energy'),
    'XLV':  ('Health Care Select Sector SPDR',         'Health Care'),
    'XLI':  ('Industrial Select Sector SPDR',          'Industrials'),
    'XLU':  ('Utilities Select Sector SPDR',           'Utilities'),
    'XLB':  ('Materials Select Sector SPDR',           'Materials'),
    'XLRE': ('Real Estate Select Sector SPDR',         'Real Estate'),
    'XLY':  ('Consumer Discretionary Select Sector SPDR','Consumer Discretionary'),
    'XLP':  ('Consumer Staples Select Sector SPDR',    'Consumer Staples'),
    'XLC':  ('Communication Services Select Sector SPDR','Communication Services'),
}

def get_us_index_prices(self, period='5d') -> list:
    # Calls _download_ticker_prices, adds symbol + index_name

def get_global_index_prices(self, period='5d') -> list:
    # Calls _download_ticker_prices, adds symbol + index_name + region

def get_sector_etf_prices(self, period='5d') -> list:
    # Calls _download_ticker_prices, adds symbol + etf_name + sector
```

### 6. ETL Job Scripts (3 files)

Each follows exact same structure as `run_yfinance_commodities.py`:
- `argparse` with `--dry-run`
- `JobRunLogger` context manager wrapping `begin_step / complete_step / fail_step`
- `transform()` that validates required fields and adds `created_date`/`created_by`
- `save_json(transformed, CONFIG_NAME, source='yfinance')`
- `run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)`

| Script | CONFIG_NAME | client method |
|--------|-------------|---------------|
| `run_yfinance_us_indexes.py` | `YFinance_US_Indexes` | `client.get_us_index_prices()` |
| `run_yfinance_global_indexes.py` | `YFinance_Global_Indexes` | `client.get_global_index_prices()` |
| `run_yfinance_sector_etfs.py` | `YFinance_Sector_ETFs` | `client.get_sector_etf_prices()` |

### 7. `schema/init.sh`

Insert after the existing `yfinance_scheduler_jobs.sql` line:
```bash
$PSQL -f /app/schema/dba/data/yfinance_index_reference_data.sql
$PSQL -f /app/schema/dba/data/yfinance_index_import_configs.sql
$PSQL -f /app/schema/dba/data/yfinance_index_scheduler_jobs.sql
```

Insert after `yfinance_commodities.sql` in the feeds section:
```bash
$PSQL -f /app/schema/feeds/yfinance_us_indexes.sql
$PSQL -f /app/schema/feeds/yfinance_global_indexes.sql
$PSQL -f /app/schema/feeds/yfinance_sector_etfs.sql
```

---

## DB Migration (no Docker rebuild needed — no new dependencies)

```bash
PSQL="docker exec tangerine-db-1 psql -U tangerine_admin -d tangerine_db"

# Reference data
$PSQL -f /app/schema/dba/data/yfinance_index_reference_data.sql

# Feed tables
$PSQL -f /app/schema/feeds/yfinance_us_indexes.sql
$PSQL -f /app/schema/feeds/yfinance_global_indexes.sql
$PSQL -f /app/schema/feeds/yfinance_sector_etfs.sql

# Import configs + scheduler
$PSQL -f /app/schema/dba/data/yfinance_index_import_configs.sql
$PSQL -f /app/schema/dba/data/yfinance_index_scheduler_jobs.sql
```

Then restart the `tangerine` service only (picks up new Python files):
```bash
docker compose restart tangerine
```

---

## Verification

1. Dry-run all 3 scripts:
   ```bash
   docker exec tangerine-tangerine-1 python etl/jobs/run_yfinance_us_indexes.py --dry-run
   docker exec tangerine-tangerine-1 python etl/jobs/run_yfinance_global_indexes.py --dry-run
   docker exec tangerine-tangerine-1 python etl/jobs/run_yfinance_sector_etfs.py --dry-run
   ```
2. Run live and verify row counts: `SELECT count(*) FROM feeds.yfinance_us_indexes` (expect 8), global (7), sector_etfs (11)
3. Re-run live to confirm idempotency (UNIQUE constraint prevents duplicates)
4. Confirm 3 scheduler entries: `SELECT job_name, cron_hour, is_active FROM dba.tscheduler WHERE job_name LIKE 'YFinance_%'`
5. Pipeline Monitor → History → confirm all 3 jobs have success status and correct step counts
