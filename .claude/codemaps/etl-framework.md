# ETL Framework Codemap

## Purpose

Config-driven ETL system for importing files (CSV, XLS, XLSX, JSON, XML) into PostgreSQL with support for dynamic schema management, metadata extraction, and file archiving.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GenericImportJob                             │
│  (etl/jobs/generic_import.py)                                    │
│  - Reads config from dba.timportconfig                           │
│  - Orchestrates extract → transform → load                       │
└─────────────────────────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────────────────────┐
           ▼                                                      │
┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐ │
│  FileExtractor    │  │  SchemaManager    │  │  PostgresLoader │ │
│  - CSVExtractor   │  │  - get_columns()  │  │  - bulk_insert  │ │
│  - ExcelExtractor │  │  - add_column()   │  │  - dataset FK   │ │
│  - JSONExtractor  │  │  - create_table() │  └─────────────────┘ │
│  - XMLExtractor   │  └───────────────────┘                      │
└───────────────────┘                                              │
           │                                                       │
           └───────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `etl/jobs/generic_import.py` | Main import job (1200+ LOC) |
| `etl/base/etl_job.py` | Base class with lifecycle methods |
| `etl/loaders/postgres_loader.py` | Bulk insert to PostgreSQL |
| `etl/jobs/run_gmail_inbox_processor.py` | Download email attachments |
| `etl/jobs/run_report_generator.py` | SQL-based email reports |
| `etl/jobs/generate_crontab.py` | Generate crontab from DB |

## GenericImportJob Lifecycle

```python
class GenericImportJob(BaseETLJob):
    def setup(self):
        # Load config from dba.timportconfig
        # Find matching files in source_directory

    def extract(self) -> List[Dict]:
        # Use appropriate FileExtractor
        # Add metadata columns (_source_file, _metadata_label, _file_date)

    def transform(self, data) -> List[Dict]:
        # Normalize column names (snake_case)
        # Apply import strategy
        # Create table if not exists

    def load(self, data):
        # Bulk insert via PostgresLoader
        # Associate with dataset_id

    def cleanup(self):
        # Archive processed files
        # Update last_modified_at
```

## File Extractors

| Extractor | File Types | Key Behavior |
|-----------|------------|--------------|
| CSVExtractor | .csv | Uses csv.DictReader, comma delimiter |
| ExcelExtractor | .xls, .xlsx | openpyxl for xlsx, xlrd for xls |
| JSONExtractor | .json | Array → records, Object → single row with raw_data |
| XMLExtractor | .xml | Tries relational parse, falls back to blob |

## Import Strategies (dba.timportstrategy)

| ID | Name | Behavior |
|----|------|----------|
| 1 | Auto-add columns | ALTER TABLE to add new columns |
| 2 | Ignore extras | Only import matching columns |
| 3 | Strict validation | Fail if column mismatch |

## Metadata Extraction

The `metadata_label_source` field determines how the dataset label is extracted:

| Source | Location Field | Behavior |
|--------|----------------|----------|
| `static` | Fixed value | Use location as literal label |
| `filename` | Index (0-based) | Split filename by delimiter, use part at index |
| `file_content` | Column name | Read value from first record's column |

Example: For file `sales_2024_q1.csv` with delimiter `_` and location `1`:
- Extracts `2024` as the label

## Date Extraction

Similar to metadata, controlled by `dateconfig`:

| Source | Location Field | Format Field |
|--------|----------------|--------------|
| `static` | Date string | Date format |
| `filename` | Index | Date format (e.g., `yyyy-MM-dd`) |
| `file_content` | Column name | Date format |

## Dynamic Table Creation

When target table doesn't exist, SchemaManager creates it:

```sql
CREATE TABLE feeds.{table} (
    {table}id SERIAL PRIMARY KEY,
    datasetid INT REFERENCES dba.tdataset(datasetid),
    -- business columns inferred from first 5 records
    col1 VARCHAR(100),
    col2 INTEGER,
    col3 NUMERIC(12,2),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50)
);
```

Type inference: TEXT → VARCHAR(50/100/255) → INTEGER → BIGINT → NUMERIC → BOOLEAN

## Running Jobs

```bash
# Basic execution
docker compose exec tangerine python etl/jobs/generic_import.py --config-id 1

# Dry run (no database writes)
docker compose exec tangerine python etl/jobs/generic_import.py --config-id 1 --dry-run

# With specific date
docker compose exec tangerine python etl/jobs/generic_import.py --config-id 1 --date 2026-01-15
```

## Event Integration

Jobs emit events to pub/sub queue on completion:

```python
# In generic_import.py main()
from admin.services.pubsub_service import create_event
create_event(
    event_type='import_complete',
    event_source=f'generic_import:{config_id}',
    event_data={'records_loaded': count, 'run_uuid': uuid}
)
```

## Volume Mounts

```
Local:     ./.data/etl/source/    → Container: /app/data/source/
Local:     ./.data/etl/archive/   → Container: /app/data/archive/
Local:     ./.data/etl/inbox/     → Container: /app/data/source/inbox/
```

Files sync bidirectionally between host and container.
