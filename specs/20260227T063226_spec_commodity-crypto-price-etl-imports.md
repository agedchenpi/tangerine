# Plan: Commodity & Crypto Price ETL Imports

## Context

Add two new ETL pipelines for daily market price data:
- **YFinance**: 13 commodity futures (Energy, Metals, Agriculture, Livestock, Softs) via the `yfinance` Python library
- **CoinGecko**: Top 5 cryptocurrencies via the free CoinGecko REST API using the `/coins/{id}/ohlc` endpoint for real daily OHLC

Each pipeline follows the existing Individual Script Pattern: fetch → transform → save JSON → `run_generic_import`. Each source gets its own `feeds.*` table (with `record_id SERIAL PK` + `datasetid FK`), its own import config, and its own ETL script.

---

## Architecture Decisions

- **Two separate feed tables** (not one shared `prices` table): `feeds.yfinance_commodities` and `feeds.coingecko_crypto`
- **CoinGecko OHLC endpoint**: `/api/v3/coins/{id}/ohlc?vs_currency=usd&days=1` — returns intraday candles, aggregated in transform to one daily record (first open, max high, min low, last close)
- **yfinance** is not yet in requirements — must add to `requirements/base.txt`
- **prefix_map** in `import_utils.py` must be extended for two new sources

---

## Files to Create / Modify

### New files (8)
| File | Purpose |
|------|---------|
| `schema/feeds/yfinance_commodities.sql` | Feed table DDL |
| `schema/feeds/coingecko_crypto.sql` | Feed table DDL |
| `schema/dba/data/yfinance_import_configs.sql` | timportconfig INSERT |
| `schema/dba/data/coingecko_import_configs.sql` | timportconfig INSERT |
| `etl/clients/yfinance_client.py` | yfinance wrapper |
| `etl/clients/coingecko_client.py` | CoinGecko OHLC client (extends BaseAPIClient) |
| `etl/jobs/run_yfinance_commodities.py` | ETL script — CONFIG: `YFinance_Commodities` |
| `etl/jobs/run_coingecko_crypto.py` | ETL script — CONFIG: `CoinGecko_Crypto` |

### Modified files (2)
| File | Change |
|------|--------|
| `requirements/base.txt` | Add `yfinance` |
| `etl/base/import_utils.py` | Add `'yfinance': 'YFinance_'` and `'coingecko': 'CoinGecko_'` to `prefix_map` in `save_json()` |

---

## Step-by-Step Changes

### 1. `requirements/base.txt`
Add one line:
```
yfinance>=0.2.40
```

### 2. `etl/base/import_utils.py`
In `save_json()`, extend `prefix_map`:
```python
prefix_map = {
    'newyorkfed': 'NewYorkFed_',
    'bankofengland': 'BankOfEngland_',
    'yfinance': 'YFinance_',
    'coingecko': 'CoinGecko_',
}
```
Slug result examples:
- `save_json(data, 'YFinance_Commodities', 'yfinance')` → `yfinance_commodities_TIMESTAMP.json`
- `save_json(data, 'CoinGecko_Crypto', 'coingecko')` → `coingecko_crypto_TIMESTAMP.json`

### 3. `schema/feeds/yfinance_commodities.sql`
```sql
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname='feeds' AND tablename='yfinance_commodities') THEN
    CREATE TABLE feeds.yfinance_commodities (
        record_id    SERIAL PRIMARY KEY,
        datasetid    INT NOT NULL REFERENCES dba.tdataset(datasetid),
        symbol       VARCHAR(20) NOT NULL,   -- e.g. CL, GC, NG
        ticker       VARCHAR(20),            -- e.g. CL=F
        category     VARCHAR(50),            -- Energy, Metals, Agriculture, etc.
        price_date   DATE NOT NULL,
        open         NUMERIC(18, 6),
        high         NUMERIC(18, 6),
        low          NUMERIC(18, 6),
        close        NUMERIC(18, 6),
        volume       BIGINT,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by   VARCHAR(50) DEFAULT 'etl_user',
        CONSTRAINT uq_yfinance_commodities UNIQUE (symbol, price_date, datasetid)
    );
    CREATE INDEX idx_yfinance_commodities_dataset ON feeds.yfinance_commodities(datasetid);
    CREATE INDEX idx_yfinance_commodities_date ON feeds.yfinance_commodities(price_date);
    CREATE INDEX idx_yfinance_commodities_symbol ON feeds.yfinance_commodities(symbol);
  END IF;
END $$;
GRANT SELECT ON feeds.yfinance_commodities TO app_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON feeds.yfinance_commodities TO app_rw;
GRANT ALL ON feeds.yfinance_commodities TO admin;
GRANT USAGE, SELECT ON SEQUENCE feeds.yfinance_commodities_record_id_seq TO app_rw;
```

### 4. `schema/feeds/coingecko_crypto.sql`
Same pattern; columns:
```sql
record_id  SERIAL PK, datasetid INT NOT NULL FK,
symbol     VARCHAR(20) NOT NULL,  -- BTC, ETH, BNB, SOL, XRP
coin_id    VARCHAR(50) NOT NULL,  -- bitcoin, ethereum, binancecoin, solana, ripple
price_date DATE NOT NULL,
open NUMERIC(18,6), high NUMERIC(18,6), low NUMERIC(18,6), close NUMERIC(18,6),
created_date TIMESTAMP, created_by VARCHAR(50),
UNIQUE (symbol, price_date, datasetid)
```

### 5. `schema/dba/data/yfinance_import_configs.sql`
```sql
INSERT INTO dba.timportconfig (
    config_name, datasource, datasettype,
    source_directory, archive_directory, file_pattern, file_type,
    metadata_label_source, metadata_label_location,
    dateconfig, datelocation, dateformat, delimiter,
    target_table, importstrategyid, is_active, is_blob, import_mode
) VALUES (
    'YFinance_Commodities', 'YFinance', 'Commodities',
    '/app/data/source/yfinance', '/app/data/archive/yfinance',
    'yfinance_commodities_.*\.json', 'JSON',
    'static', 'Commodities',
    'file_content', 'price_date', 'yyyy-MM-dd', NULL,
    'feeds.yfinance_commodities', 2, TRUE, FALSE, 'file'
) ON CONFLICT (config_name) DO UPDATE SET ...;
```
(`importstrategyid = 2` = "Import only, ignore new columns" — we control the schema)

### 6. `schema/dba/data/coingecko_import_configs.sql`
Same pattern:
```sql
config_name='CoinGecko_Crypto', datasource='CoinGecko', datasettype='Crypto',
source_directory='/app/data/source/coingecko', archive_directory='/app/data/archive/coingecko',
file_pattern='coingecko_crypto_.*\.json', target_table='feeds.coingecko_crypto'
```

### 7. `etl/clients/yfinance_client.py`
Plain class (not BaseAPIClient — yfinance is a library, not HTTP):
```python
class YFinanceClient:
    COMMODITIES = {
        'CL=F': ('CL', 'Energy'),    'BZ=F': ('BZ', 'Energy'),
        'NG=F': ('NG', 'Energy'),    'GC=F': ('GC', 'Metals'),
        'SI=F': ('SI', 'Metals'),    'HG=F': ('HG', 'Metals'),
        'ZW=F': ('ZW', 'Agriculture'), 'ZC=F': ('ZC', 'Agriculture'),
        'ZS=F': ('ZS', 'Agriculture'), 'LE=F': ('LE', 'Livestock'),
        'HE=F': ('HE', 'Livestock'), 'KC=F': ('KC', 'Softs'),
        'SB=F': ('SB', 'Softs'),
    }
    def get_commodity_prices(self, period='5d') -> list:
        # yf.download(tickers, period=period, progress=False)
        # Returns MultiIndex DataFrame; handle single vs multi-ticker edge case
        # Return list of dicts: {symbol, ticker, category, price_date, open, high, low, close, volume}
```
Uses `period='5d'` to handle weekend/holiday gaps, takes most recent non-null row per ticker.

### 8. `etl/clients/coingecko_client.py`
Extends `BaseAPIClient` from `etl.base.api_client`:
```python
class CoinGeckoClient(BaseAPIClient):
    BASE_URL = 'https://api.coingecko.com/api/v3'
    COINS = {
        'bitcoin': 'BTC', 'ethereum': 'ETH', 'binancecoin': 'BNB',
        'solana': 'SOL', 'ripple': 'XRP',
    }
    def get_crypto_ohlc_daily(self, days=1) -> list:
        # GET /coins/{id}/ohlc?vs_currency=usd&days=1 for each coin
        # Response: [[timestamp_ms, open, high, low, close], ...]
        # Aggregate intraday candles → one daily record:
        #   open=first[1], high=max([2]), low=min([3]), close=last[4]
        #   price_date = date of last candle (UTC)
        # Return list of dicts: {symbol, coin_id, price_date, open, high, low, close}
```
Rate limit: 10–30 rpm (CoinGecko free tier). Add small `time.sleep(1)` between coin fetches.

### 9. `etl/jobs/run_yfinance_commodities.py`
```python
CONFIG_NAME = 'YFinance_Commodities'

def transform(raw_data: list) -> list:
    # raw_data already structured from client
    # Add audit_cols(), ensure price_date is ISO string
    ...

def main():
    with JobRunLogger('run_yfinance_commodities', CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step('data_collection', 'Data Collection')
        client = YFinanceClient()
        raw_data = client.get_commodity_prices()
        transformed = transform(raw_data)
        save_json(transformed, CONFIG_NAME, source='yfinance')
        job_log.complete_step(step_id, ...)
        return run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)
```

### 10. `etl/jobs/run_coingecko_crypto.py`
Same pattern; CONFIG_NAME = `'CoinGecko_Crypto'`; source=`'coingecko'`.

---

## DB Migration (run after Docker rebuild)

```sql
-- 1. Create feed tables
\i schema/feeds/yfinance_commodities.sql
\i schema/feeds/coingecko_crypto.sql

-- 2. Insert import configs
\i schema/dba/data/yfinance_import_configs.sql
\i schema/dba/data/coingecko_import_configs.sql
```
Or run directly via Docker exec (as `tangerine_admin`).

---

## Verification

1. `docker compose build && docker compose up -d` (picks up new yfinance dep + code)
2. Run yfinance script in dry-run: `docker exec tangerine-tangerine-1 python etl/jobs/run_yfinance_commodities.py --dry-run`
3. Run CoinGecko script in dry-run: `docker exec tangerine-tangerine-1 python etl/jobs/run_coingecko_crypto.py --dry-run`
4. Run live (no dry-run) and verify rows in `feeds.yfinance_commodities` and `feeds.coingecko_crypto`
5. Pipeline Monitor → History → confirm both jobs appear with success status and correct step record counts
6. Run both scripts a second time to confirm idempotency (no duplicate rows via UNIQUE constraint)
