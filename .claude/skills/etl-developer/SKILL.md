---
name: etl-developer
description: ETL job development patterns for Tangerine - import jobs, extractors, schema management, file processing
---

# ETL Developer Guidelines

## Overview

Tangerine uses a config-driven ETL framework. Most imports use `generic_import.py` with database configuration rather than custom job files.

## Job Structure

```
etl/
├── base/
│   └── etl_job.py              # Base ETL job class
├── jobs/
│   ├── generic_import.py       # Config-driven file imports
│   ├── run_gmail_inbox_processor.py  # Email attachment processing
│   ├── run_report_generator.py       # SQL-based report generation
│   └── generate_crontab.py           # Scheduler generation
└── regression/
    ├── run_regression_tests.py
    └── generate_test_files.py
```

## Creating a New Import

**DO NOT create new job files.** Instead:

1. Add configuration to `dba.timportconfig` table via admin UI
2. Configure: file pattern, target table, import strategy, metadata extraction
3. Run via: `docker compose exec tangerine python etl/jobs/generic_import.py --config-id {id}`

## Supported File Formats

| Format | Extension | Parser |
|--------|-----------|--------|
| CSV | .csv | csv.DictReader |
| Excel | .xls, .xlsx | pandas/openpyxl |
| JSON | .json | json.load |
| XML | .xml | xml.etree.ElementTree |

## Import Strategies

| ID | Name | Behavior |
|----|------|----------|
| 1 | Auto-add | ALTER TABLE to add new columns from file |
| 2 | Ignore | Skip columns not already in table |
| 3 | Strict | Fail if file columns don't match table |

**Recommendation:** Use Strategy 2 (Ignore) for most imports. Use Strategy 1 only when schema evolution is expected.

## Key Classes

### SchemaManager

Handles table creation and column type inference:

```python
from etl.jobs.generic_import import SchemaManager

manager = SchemaManager(cursor, "feeds.my_table")
manager.ensure_table_exists(columns, sample_data)
manager.add_missing_columns(new_columns)
```

### Extractor Pattern

Each file type has an extractor that returns records:

```python
def extract_csv(file_path: Path, delimiter: str = ",") -> list[dict]:
    """Extract records from CSV file."""
    with open(file_path, "r", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return list(reader)
```

## Required Patterns

### 1. Dry-Run Mode

All jobs MUST support `--dry-run` flag:

```python
parser.add_argument("--dry-run", action="store_true",
                    help="Validate without database writes")

if args.dry_run:
    logger.info("DRY RUN - no changes will be made")
    # Skip: INSERT, UPDATE, DELETE, file archiving
```

### 2. Logging

Use the common logging utility:

```python
from common.logging_utils import get_etl_logger

logger = get_etl_logger("generic_import", run_uuid)
logger.info("Starting import for config_id=%s", config_id)
logger.error("Failed to process file: %s", str(e))
```

### 3. Dataset Tracking

Create a dataset record for each import:

```python
cursor.execute("""
    INSERT INTO dba.tdataset (
        datasourceid, datasettypeid, label, datasetdate, datastatusid
    ) VALUES (%s, %s, %s, %s, 1)
    RETURNING datasetid
""", (datasource_id, datasettype_id, label, file_date))
dataset_id = cursor.fetchone()["datasetid"]
```

### 4. File Archiving

Move processed files to archive directory:

```python
import shutil
from datetime import datetime

archive_name = f"{datetime.now():%Y%m%d_%H%M%S}_{file_path.name}"
archive_path = archive_dir / archive_name
shutil.move(str(file_path), str(archive_path))
```

## Database Connections

Always use the transaction context manager:

```python
from common.db_utils import db_transaction

with db_transaction() as cursor:
    cursor.execute("SELECT * FROM dba.timportconfig WHERE config_id = %s", (config_id,))
    config = cursor.fetchone()
```

## Metadata Extraction

Three modes for extracting dataset labels:

| Mode | Config | Example |
|------|--------|---------|
| filename | `metadata_label_source='filename'`, `metadata_label_location='_:2'` | `data_sales_20260115.csv` → `20260115` |
| file_content | `metadata_label_source='file_content'`, `metadata_label_location='label_column'` | Column value from first row |
| static | `metadata_label_source='static'`, `metadata_label_location='Fixed Label'` | Literal string |

## Date Extraction

Convert Java date formats to Python:

```python
def java_to_python_format(java_fmt: str) -> str:
    """Convert Java date format to Python strptime format."""
    return (java_fmt
        .replace("yyyy", "%Y")
        .replace("MM", "%m")
        .replace("dd", "%d"))

# Example: "yyyyMMdd" → "%Y%m%d"
```

## Testing

Tests are in `tests/integration/etl/`:

```bash
# Run all ETL tests
docker compose exec tangerine pytest tests/integration/etl/ -v

# Run specific test file
docker compose exec tangerine pytest tests/integration/etl/test_generic_import.py -v
```

## Common Pitfalls

1. **Don't hardcode paths** - Use config values from database
2. **Don't skip dry-run** - Always implement and test dry-run mode
3. **Don't forget dataset tracking** - Every import needs a tdataset record
4. **Don't leave files in source** - Archive after successful processing
5. **Don't use string formatting for SQL** - Always use parameterized queries

## Documentation Requirements

**After making ETL changes, always update documentation:**

1. **CHANGELOG.md** - Add entry under `[Unreleased]` section:
   - `Added` - New jobs, extractors, file formats
   - `Changed` - Modifications to existing ETL behavior
   - `Fixed` - Bug fixes

2. **Codemaps** (if architecture changes):
   - `.claude/codemaps/etl-framework.md` - Job structure, strategies
   - `.claude/codemaps/database-schema.md` - New tracking tables

3. **Feature docs** (for significant features):
   - Create `docs/features/{feature-name}.md` using `/doc-feature`

**Example CHANGELOG entry:**
```markdown
### Added
- **XML Import Support**: Added XML file parsing to generic import job
```
