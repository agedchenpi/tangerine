# Database Schema Codemap

## Purpose

PostgreSQL 18 database with two schemas:
- `dba`: ETL pipeline configuration, logging, and events
- `feeds`: Raw data storage (target tables for imports)

## Schema Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         dba schema                               │
├─────────────────────────────────────────────────────────────────┤
│ Configuration:                                                   │
│   timportconfig    - Import job configurations                   │
│   tdatasource      - Data source reference                       │
│   tdatasettype     - Dataset type reference                      │
│   timportstrategy  - Import strategies (3 predefined)            │
│                                                                  │
│ Email Services:                                                  │
│   tinboxconfig     - Gmail inbox processing rules                │
│   treportmanager   - Report configurations                       │
│   tscheduler       - Cron job scheduler                          │
│                                                                  │
│ Pub/Sub:                                                         │
│   tpubsub_events   - Event queue                                 │
│   tpubsub_subscribers - Event subscribers                        │
│                                                                  │
│ Tracking & Logging:                                              │
│   tdataset         - Dataset metadata                            │
│   tlogentry        - ETL execution logs                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        feeds schema                              │
├─────────────────────────────────────────────────────────────────┤
│ Dynamic tables created by GenericImportJob                       │
│ All tables must have:                                            │
│   - {table}id SERIAL PRIMARY KEY                                 │
│   - datasetid INT REFERENCES dba.tdataset(datasetid)             │
│   - created_date TIMESTAMP                                       │
│   - created_by VARCHAR(50)                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Key Tables

### dba.timportconfig

```sql
-- Import job configuration (19 fields)
config_id SERIAL PRIMARY KEY,
config_name VARCHAR(100) UNIQUE NOT NULL,
datasource VARCHAR(50) NOT NULL,          -- FK to tdatasource
datasettype VARCHAR(50) NOT NULL,         -- FK to tdatasettype
source_directory VARCHAR(500) NOT NULL,   -- /app/data/source/
archive_directory VARCHAR(500) NOT NULL,  -- /app/data/archive/
file_pattern VARCHAR(200) NOT NULL,       -- Regex pattern
file_type VARCHAR(10) NOT NULL,           -- CSV, XLS, XLSX, JSON, XML
metadata_label_source VARCHAR(20),        -- static, filename, file_content
metadata_label_location VARCHAR(100),     -- Index or column name
dateconfig VARCHAR(20),                   -- static, filename, file_content
datelocation VARCHAR(100),
dateformat VARCHAR(50),                   -- yyyy-MM-dd, etc.
delimiter VARCHAR(10),                    -- For filename parsing
target_table VARCHAR(100) NOT NULL,       -- feeds.tablename
importstrategyid INT DEFAULT 1,           -- FK to timportstrategy
is_active BOOLEAN DEFAULT TRUE,
is_blob BOOLEAN DEFAULT FALSE,
last_modified_at TIMESTAMP
```

### dba.tdataset

```sql
-- Tracks each import run
datasetid SERIAL PRIMARY KEY,
datasourceid INT NOT NULL,               -- FK to tdatasource
datasettypeid INT NOT NULL,              -- FK to tdatasettype
label VARCHAR(100),                      -- Extracted metadata label
datastatusid INT DEFAULT 1,              -- FK to tdatastatus
loadeddateutc DATE,
run_uuid VARCHAR(36) UNIQUE NOT NULL,
createdby VARCHAR(50),
createddate TIMESTAMP DEFAULT NOW()
```

### dba.tlogentry

```sql
-- ETL execution logs
logentryid SERIAL PRIMARY KEY,
run_uuid VARCHAR(36) NOT NULL,
process_type VARCHAR(50),
message TEXT,
stepruntime NUMERIC(10,2),               -- Seconds
created_date TIMESTAMP DEFAULT NOW()
```

### dba.tpubsub_events

```sql
-- Event queue
event_id SERIAL PRIMARY KEY,
event_type VARCHAR(50) NOT NULL,         -- file_received, import_complete, etc.
event_source VARCHAR(200),               -- Origin identifier
event_data JSONB,                        -- Event payload
status VARCHAR(20) DEFAULT 'pending',    -- pending, processing, completed, failed
priority INT DEFAULT 5,                  -- 1-10
created_at TIMESTAMP DEFAULT NOW(),
processed_at TIMESTAMP,
completed_at TIMESTAMP,
error_message TEXT,
retry_count INT DEFAULT 0,
max_retries INT DEFAULT 3
```

### dba.tpubsub_subscribers

```sql
-- Event subscribers (handlers)
subscriber_id SERIAL PRIMARY KEY,
subscriber_name VARCHAR(100) UNIQUE NOT NULL,
description TEXT,
event_type VARCHAR(50) NOT NULL,         -- Event to subscribe to
event_filter JSONB,                      -- Optional filter conditions
job_type VARCHAR(50) NOT NULL,           -- import, inbox_processor, report, custom
config_id INT,                           -- FK to relevant config table
script_path VARCHAR(500),                -- For custom handlers
is_active BOOLEAN DEFAULT TRUE,
trigger_count INT DEFAULT 0,
last_triggered_at TIMESTAMP,
created_at TIMESTAMP DEFAULT NOW(),
last_modified_at TIMESTAMP DEFAULT NOW()
```

## Stored Procedures

| Procedure | Purpose |
|-----------|---------|
| `dba.pimportconfigi` | Insert new import config |
| `dba.pimportconfigu` | Update import config |
| `dba.ppubsub_iu` | Upsert pub/sub events |

## Key Relationships

```
timportconfig
    └── importstrategyid → timportstrategy.importstrategyid
    └── datasource → tdatasource.sourcename
    └── datasettype → tdatasettype.typename

tdataset
    └── datasourceid → tdatasource.datasourceid
    └── datasettypeid → tdatasettype.datasettypeid
    └── datastatusid → tdatastatus.datastatusid

feeds.{table}
    └── datasetid → tdataset.datasetid

tpubsub_subscribers
    └── config_id → timportconfig OR tinboxconfig OR treportmanager
```

## Querying Patterns

```python
# Always use parameterized queries
from common.db_utils import fetch_dict, db_transaction

# Read: Use fetch_dict (returns List[Dict])
results = fetch_dict("SELECT * FROM dba.table WHERE id = %s", (id,))

# Write: Use db_transaction context manager
with db_transaction() as cursor:
    cursor.execute("INSERT INTO dba.table (col) VALUES (%s)", (val,))
```

## Important: LIKE Pattern Escaping

```python
# WRONG - causes "tuple index out of range" in psycopg2
query = "SELECT * FROM table WHERE name LIKE '%prefix%'"

# CORRECT - double the percent signs
query = "SELECT * FROM table WHERE name LIKE '%%prefix%%'"
```

## Database Roles

| Role | Permissions |
|------|-------------|
| tangerine_admin | Full access (DDL + DML) |
| app_rw | SELECT, INSERT, UPDATE, DELETE on dba.* and feeds.* |
| app_ro | SELECT only |
