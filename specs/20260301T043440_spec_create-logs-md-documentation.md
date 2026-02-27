# Plan: Create logs.md Documentation

## Context
The user wants a comprehensive reference document that catalogues every logging mechanism in the Tangerine project (database tables, Python utilities, file logs, admin UI) and proposes targeted improvements. This document will serve as a single source of truth for the logging architecture.

## Document Location
`/opt/tangerine/logs.md` — project root alongside CLAUDE.md, README.md

## Document Structure

### 1. Overview
Brief description of the three-tier logging architecture and the correlation strategy (run_uuid).

### 2. Database Tables

| Table | Schema | Purpose |
|---|---|---|
| `tlogentry` | dba | Detailed ETL process logs (each log line) |
| `tjobrun` | dba | One row per ETL script execution (job-level) |
| `tjobstep` | dba | One row per step within a job (step-level) |
| `tddllogs` | dba | Automatic DDL change audit via event trigger |

For each table: columns, how it's populated, and relationships.

### 3. Python Logging Utilities (`common/logging_utils.py`)

- **`ETLLogger`** — context manager; dual-writes to file + database; auto-generates run_uuid
- **`DatabaseLogHandler`** — custom `logging.Handler`; batches 100 entries; flushes on ERROR or 10s timeout; writes to `dba.tlogentry`
- **`JsonFormatter`** — structured JSON output with metadata fields
- **`get_logger()`** — lightweight factory for console-only logging in scripts

### 4. Job-Level Tracking (`etl/base/import_utils.py`)

- **`JobRunLogger`** — context manager; creates `tjobrun` + `tjobstep` records; tracks records_in/records_out; links step logs via `log_run_uuid`

### 5. File Logging

- Path: `/app/logs/tangerine.log`
- RotatingFileHandler: 50MB max, 10 backups (500MB ceiling)
- Format: JSON via `JsonFormatter`
- Controlled by: `ETL_ENABLE_FILE_LOGGING`, `ETL_LOG_DIR` env vars

### 6. Configuration

| Env Var | Default | Effect |
|---|---|---|
| `ETL_LOG_LEVEL` | `INFO` | Min log level (DEBUG/INFO/WARNING/ERROR) |
| `ETL_LOG_DIR` | `/app/logs` | File log destination |
| `ETL_ENABLE_DB_LOGGING` | `true` | Write to dba.tlogentry |
| `ETL_ENABLE_FILE_LOGGING` | `true` | Write to rotating file |

Defined in `common/config.py` via pydantic-settings.

### 7. Admin UI Log Surfaces

| Page | Source Tables | Features |
|---|---|---|
| Monitoring | `dba.tlogentry` | Search, filter, export CSV, purge |
| Pipeline Monitor | `dba.tjobrun`, `dba.tjobstep` | Hierarchical job view, step drilldown, re-run, override |
| Scheduler | `dba.tlogentry` (via last_run_uuid) | Log dialog, download as .log |

Services: `monitoring_service.py`, `pipeline_monitor_service.py`, `scheduler_service.py`

### 8. Data Flow Diagram

```
ETL Script
  └─ JobRunLogger → dba.tjobrun (1 row), dba.tjobstep (1 row/step)
  └─ ETLLogger → DatabaseLogHandler → dba.tlogentry (n rows)
                → RotatingFileHandler → /app/logs/tangerine.log

DDL Commands → flogddlchanges() EVENT TRIGGER → dba.tddllogs

Correlation:
  tjobstep.log_run_uuid ──→ tlogentry.run_uuid
  tjobrun.run_uuid       ──→ tlogentry.run_uuid
  tscheduler.last_run_uuid → tlogentry.run_uuid
```

### 9. Audit Columns on Data Tables

Several tables carry lightweight audit columns (not a centralized audit log):
- `tdataset`: `createddate`, `createdby`
- `timportconfig`: `created_at`, `last_modified_at`
- `tscheduler`: `created_at`, `last_modified_at`, `last_run_at`, `last_run_status`, `last_run_uuid`, `last_run_output`

### 10. Improvement Suggestions

1. **No automated log retention** — `tlogentry` grows unbounded; the UI has a manual purge but no scheduled cleanup. Recommend a scheduled job or `pg_partman` for time-based partitioning / auto-drop.

2. **run_uuid gap between layers** — `JobRunLogger` and `ETLLogger` (inside `GenericImportJob`) each generate their own `run_uuid`. The link is only soft via `tjobstep.log_run_uuid`. Consider passing the parent run_uuid through so all layers share one ID.

3. **`tddllogs` not surfaced in admin UI** — DDL audit data is captured but invisible to users. A simple "Schema Changes" tab on the Monitoring page would make it useful.

4. **No alerting on job failure** — Failed jobs are only discoverable by checking the admin UI. A notification hook (email, Slack webhook) triggered on `status = 'failed'` would improve observability.

5. **`last_run_output` (raw stdout) on tscheduler** — This is a fallback when structured logs aren't available. It's a text blob that can grow large. Consider capping it or removing it once `tlogentry` coverage is confirmed complete for all jobs.

6. **No per-script log level override** — All scripts share a single `ETL_LOG_LEVEL`. Adding a per-config override in `timportconfig` would allow verbose debugging of a single job without flooding all logs.

7. **File logs not accessible in admin UI** — The rotating file at `/app/logs/tangerine.log` is only reachable via shell. A simple tail/search UI or log download would be useful for cases where DB logging is disabled.

8. **DEBUG logs are not persisted to database** — `DatabaseLogHandler` receives all levels, but practically the default `INFO` level means DEBUG never reaches it. If a developer temporarily sets `ETL_LOG_LEVEL=DEBUG`, those verbose logs won't persist after the container restarts. Consider always writing ERROR+ to DB regardless of the global level.

## Critical Files

| File | Role |
|---|---|
| `common/logging_utils.py` | ETLLogger, DatabaseLogHandler, JsonFormatter, get_logger |
| `etl/base/import_utils.py` | JobRunLogger |
| `common/config.py` | ETLConfig pydantic-settings |
| `schema/dba/tables/tlogentry.sql` | Detailed log table |
| `schema/dba/tables/tjobrun.sql` | Job execution table |
| `schema/dba/tables/tjobstep.sql` | Step tracking table |
| `schema/dba/tables/tddllogs.sql` | DDL audit table |
| `schema/dba/functions/flogddlchanges.sql` | DDL event trigger function |
| `admin/pages/monitoring.py` | Log viewer UI |
| `admin/pages/pipeline_monitor.py` | Job run UI |
| `admin/services/monitoring_service.py` | tlogentry queries |
| `admin/services/pipeline_monitor_service.py` | tjobrun/tjobstep queries |

## Verification
- Read the final `logs.md` in the browser/editor to confirm it renders clearly
- Cross-check column names against the actual SQL files to ensure accuracy
- No code changes required — this is documentation only
