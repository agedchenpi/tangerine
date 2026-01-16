# Code Style Guidelines

This document defines coding conventions for the Tangerine ETL project. Follow these guidelines to ensure consistency across all contributions.

---

## Table of Contents

1. [SQL Conventions](#sql-conventions)
2. [Python Conventions](#python-conventions)
3. [Streamlit Conventions](#streamlit-conventions)
4. [Testing Conventions](#testing-conventions)
5. [Documentation Conventions](#documentation-conventions)
6. [File Organization](#file-organization)

---

## SQL Conventions

### Object Naming Prefixes

All database objects use a lowercase prefix indicating their type:

| Object Type | Prefix | Example |
|-------------|--------|---------|
| Table | `t` | `timportconfig`, `tdataset` |
| Procedure | `p` | `pimportconfig_create`, `pdataset_update` |
| Function | `f` | `fget_next_business_day`, `fvalidate_email` |
| View | `v` | `vdataset_summary`, `vimport_history` |
| Index | `idx_` | `idx_dataset_status`, `idx_events_created` |
| Foreign Key | `fk_` | `fk_dataset_datasource`, `fk_config_strategy` |
| Check Constraint | `chk_` | `chk_valid_status`, `chk_positive_count` |
| Unique Constraint | `uq_` | `uq_config_name`, `uq_subscriber_name` |
| Sequence | `seq_` | `seq_dataset_id`, `seq_event_id` |

### Table Design

```sql
-- Table naming: t + descriptive_name (singular, lowercase)
CREATE TABLE IF NOT EXISTS dba.timportconfig (
    -- Primary key: table_name + id (without 't' prefix)
    config_id SERIAL PRIMARY KEY,

    -- Foreign keys: referenced_table + id
    datasource_id INTEGER REFERENCES dba.tdatasource(datasource_id),

    -- Boolean columns: is_ or has_ prefix
    is_active BOOLEAN DEFAULT TRUE,
    has_header BOOLEAN DEFAULT TRUE,

    -- Timestamps: use _at suffix (modern convention)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Text fields: descriptive names
    config_name VARCHAR(100) NOT NULL,
    description TEXT
);
```

### Column Naming

| Type | Convention | Examples |
|------|------------|----------|
| Primary Key | `{entity}_id` | `config_id`, `dataset_id` |
| Foreign Key | `{referenced_table}_id` | `datasource_id`, `strategy_id` |
| Boolean | `is_` or `has_` prefix | `is_active`, `has_header` |
| Timestamp | `_at` suffix | `created_at`, `processed_at` |
| Date | `_date` suffix | `file_date`, `report_date` |
| Count | `_count` suffix | `record_count`, `retry_count` |
| Name/Label | descriptive | `config_name`, `display_label` |

### Stored Procedures

```sql
-- Naming: p + table_name + operation
-- Operations: create, update, delete, get, list, upsert (iu = insert/update)

CREATE OR REPLACE PROCEDURE dba.pimportconfig_create(
    -- Parameters: p_ prefix
    p_config_name VARCHAR(100),
    p_datasource_id INTEGER,
    p_is_active BOOLEAN DEFAULT TRUE,
    -- Output parameter
    OUT p_config_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO dba.timportconfig (config_name, datasource_id, is_active)
    VALUES (p_config_name, p_datasource_id, p_is_active)
    RETURNING config_id INTO p_config_id;
END;
$$;
```

### Functions

```sql
-- Naming: f + descriptive_action
-- Pure functions that return values

CREATE OR REPLACE FUNCTION dba.fget_next_business_day(
    p_date DATE
)
RETURNS DATE
LANGUAGE plpgsql
AS $$
DECLARE
    v_result DATE;  -- Local variables: v_ prefix
BEGIN
    -- Implementation
    RETURN v_result;
END;
$$;
```

### Query Formatting

```sql
-- Use uppercase for SQL keywords
-- Align columns and conditions for readability
-- One column per line for SELECT with more than 3 columns

SELECT
    ic.config_id,
    ic.config_name,
    ic.is_active,
    ds.source_name AS datasource,
    dt.type_name AS dataset_type
FROM dba.timportconfig ic
INNER JOIN dba.tdatasource ds ON ic.datasource_id = ds.datasource_id
LEFT JOIN dba.tdatasettype dt ON ic.datasettype_id = dt.datasettype_id
WHERE ic.is_active = TRUE
  AND ic.created_at >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY ic.config_name ASC;
```

### Idempotent DDL

All schema files must be idempotent (safe to run multiple times):

```sql
-- Tables
CREATE TABLE IF NOT EXISTS dba.ttablename (...);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_name ON dba.ttable(column);

-- Procedures/Functions
CREATE OR REPLACE PROCEDURE/FUNCTION ...

-- Constraints (check first)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_name'
    ) THEN
        ALTER TABLE dba.ttable ADD CONSTRAINT fk_name ...;
    END IF;
END $$;
```

---

## Python Conventions

### Formatting and Readability

**Line Length:** 120 characters max (pragmatic, not strict 80)

**Blank Lines:**
- 2 blank lines between top-level definitions (functions, classes)
- 1 blank line between method definitions within a class
- 1 blank line to separate logical sections within a function

**Vertical Spacing for Readability:**
```python
def process_import(config_id: int, dry_run: bool = False) -> Dict[str, Any]:
    """Process an import configuration."""

    # Section 1: Setup and validation
    config = get_config(config_id)
    if not config:
        raise ConfigNotFoundError(f"Config {config_id} not found")

    # Section 2: File discovery
    source_dir = Path(config['source_directory'])
    pattern = config['file_pattern']
    matched_files = list(source_dir.glob(pattern))

    # Section 3: Processing
    results = []
    for file_path in matched_files:
        result = _process_single_file(file_path, config)
        results.append(result)

    # Section 4: Summary
    return {
        'config_id': config_id,
        'files_processed': len(results),
        'records_loaded': sum(r['count'] for r in results)
    }
```

### Naming Conventions

| Element | Convention | Examples |
|---------|------------|----------|
| Functions | snake_case, verb prefix | `get_config()`, `create_dataset()` |
| Variables | snake_case, descriptive | `config_id`, `matched_files` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| Classes | PascalCase | `ImportConfig`, `FileExtractor` |
| Private | Leading underscore | `_helper_function()`, `_internal_var` |
| Booleans | `is_`, `has_`, `can_` prefix | `is_active`, `has_header` |

**Function Naming Verbs:**
```python
get_*()      # Retrieve single item
list_*()     # Retrieve multiple items
create_*()   # Insert new record
update_*()   # Modify existing record
delete_*()   # Remove record
count_*()    # Count records
validate_*() # Check validity
process_*()  # Transform/handle data
```

### Import Organization

Follow PEP 8 with clear grouping:

```python
# 1. Standard library imports (alphabetical)
import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 2. Third-party imports (alphabetical)
import psycopg2
from openpyxl import load_workbook
from pydantic import BaseModel, Field

# 3. Local application imports (alphabetical)
from common.db_utils import db_transaction, fetch_dict
from common.logging_utils import get_logger
from etl.base.etl_job import BaseETLJob
```

### Type Hints

Always use type hints for function signatures:

```python
def list_configs(
    active_only: bool = False,
    file_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """List import configurations with optional filters."""
    ...

def get_config(config_id: int) -> Optional[Dict[str, Any]]:
    """Get single configuration by ID."""
    ...

def create_config(config_data: Dict[str, Any]) -> int:
    """Create configuration and return new ID."""
    ...
```

### String Formatting

Use f-strings exclusively:

```python
# Good
message = f"Processing config {config_id}: {config_name}"
path = f"{base_dir}/{filename}"
query = f"Found {count:,} records in {elapsed:.2f}s"

# Avoid
message = "Processing config {}: {}".format(config_id, config_name)  # No
message = "Processing config %s: %s" % (config_id, config_name)      # No
message = "Processing config " + str(config_id)                       # No
```

### Docstrings (Google Style)

```python
def bulk_insert(
    table: str,
    columns: List[str],
    values: List[Tuple],
    schema: str = "feeds"
) -> int:
    """
    Perform bulk insert using COPY for performance.

    Args:
        table: Target table name (without schema)
        columns: List of column names
        values: List of value tuples to insert
        schema: Database schema (default: feeds)

    Returns:
        Number of records inserted

    Raises:
        DatabaseError: If insert fails
        ValueError: If columns and values don't match

    Example:
        >>> count = bulk_insert(
        ...     table='sales_data',
        ...     columns=['date', 'amount', 'region'],
        ...     values=[('2024-01-01', 100.50, 'North'), ...]
        ... )
    """
```

### Error Handling

```python
# Define custom exceptions for domain errors
class ConfigNotFoundError(Exception):
    """Raised when import configuration is not found."""
    pass

class ImportValidationError(Exception):
    """Raised when import validation fails."""
    pass

# Use try-except with specific handling
try:
    records = extractor.extract(file_path)
    loaded = loader.load(records)
except FileNotFoundError:
    logger.error(f"Source file not found: {file_path}")
    raise
except DatabaseError as e:
    logger.error(f"Database error during load: {e}")
    raise ImportValidationError(f"Failed to load: {e}") from e

# Context managers for cleanup
with db_transaction() as cursor:
    cursor.execute(query, params)
    # Auto-commits on success, rolls back on exception
```

### Database Queries

**Always use parameterized queries:**

```python
# Good - parameterized
cursor.execute(
    "SELECT * FROM dba.timportconfig WHERE config_id = %s",
    (config_id,)
)

# Good - multi-parameter
cursor.execute(
    """
    SELECT * FROM dba.timportconfig
    WHERE is_active = %s AND file_type = %s
    """,
    (True, file_type)
)

# DANGER - SQL injection vulnerability
cursor.execute(f"SELECT * FROM dba.timportconfig WHERE config_id = {config_id}")
```

**LIKE patterns require double percent signs:**

```python
# Correct - double %% for psycopg2
query = "SELECT * FROM dba.tlogentry WHERE message LIKE '%%ERROR%%'"

# Wrong - causes "tuple index out of range"
query = "SELECT * FROM dba.tlogentry WHERE message LIKE '%ERROR%'"
```

### Collections and Comprehensions

```python
# List comprehensions for simple transformations
names = [config['name'] for config in configs]
active = [c for c in configs if c['is_active']]

# Dict comprehensions
lookup = {c['id']: c['name'] for c in configs}

# Generator expressions for large datasets
total = sum(r['count'] for r in results)

# Use sets for membership testing
existing_columns = set(get_table_columns(schema, table))
new_columns = set(record.keys()) - existing_columns

# Prefer early returns over nested conditions
def get_config(config_id: int) -> Optional[Dict]:
    if not config_id:
        return None

    result = fetch_dict(query, (config_id,))
    if not result:
        return None

    return result[0]
```

---

## Streamlit Conventions

### Form Keys

All forms require unique keys, even across tabs:

```python
# Pattern: {context}_{action}_form
form_key = f"import_config_{'edit' if is_edit else 'create'}_form"

with st.form(key=form_key):
    config_name = st.text_input("Name", value=existing.get('name', ''))
    submitted = st.form_submit_button("Save")
```

### Session State

Use session state for messages that persist across reruns:

```python
# Store message before rerun
st.session_state.success_message = f"Created config: {config_name}"
st.rerun()

# Display and clear at page start
if 'success_message' in st.session_state:
    st.success(st.session_state.success_message)
    del st.session_state.success_message
```

### Page Structure

```python
import streamlit as st
from admin.utils.ui_helpers import load_custom_css, add_page_header

# 1. Page config (must be first Streamlit call)
st.set_page_config(page_title="Import Configs", layout="wide")

# 2. Load CSS
load_custom_css()

# 3. Display any session messages
if 'success_message' in st.session_state:
    st.success(st.session_state.success_message)
    del st.session_state.success_message

# 4. Page header
add_page_header("Import Configurations", icon="settings", subtitle="Manage ETL imports")

# 5. Main content
# ...
```

### Service Layer Separation

Pages should only handle UI; business logic goes in services:

```python
# Good - page calls service
from admin.services.import_config_service import create_config, list_configs

configs = list_configs(active_only=True)
for config in configs:
    st.write(config['name'])

# Bad - page contains SQL
cursor.execute("SELECT * FROM dba.timportconfig")  # No!
```

---

## Testing Conventions

### File Naming

```
tests/
├── unit/                    # No database, fast
│   ├── test_validators.py   # test_{module}.py
│   └── test_formatters.py
├── integration/             # Requires database
│   └── services/
│       ├── test_import_config_service.py
│       └── test_monitoring_service.py
└── fixtures/                # Shared test data
    └── import_config_fixtures.py
```

### Test Structure

```python
import pytest
from admin.services.import_config_service import create_config, get_config

class TestImportConfigCreate:
    """Tests for create_config function."""

    @pytest.mark.integration
    def test_create_config_returns_id(self, db_transaction, sample_datasource):
        """Create config should return new config ID."""
        # Arrange
        config_data = {
            'config_name': 'AdminTest_create_test',
            'datasource_id': sample_datasource['id'],
            'is_active': True
        }

        # Act
        config_id = create_config(config_data)

        # Assert
        assert config_id is not None
        assert isinstance(config_id, int)
        assert config_id > 0

    @pytest.mark.integration
    def test_create_config_persists_data(self, db_transaction, sample_datasource):
        """Created config should be retrievable."""
        # Arrange
        config_data = {'config_name': 'AdminTest_persist', ...}

        # Act
        config_id = create_config(config_data)
        retrieved = get_config(config_id)

        # Assert
        assert retrieved is not None
        assert retrieved['config_name'] == 'AdminTest_persist'
```

### Test Data Naming

All test data uses `AdminTest_` prefix for easy cleanup:

```python
# Good - identifiable test data
config_name = f"AdminTest_{uuid.uuid4().hex[:8]}"
datasource_name = "AdminTest_sales_source"

# Bad - could conflict with real data
config_name = "test_config"
datasource_name = "sales"
```

### Markers

```python
@pytest.mark.unit        # Fast, no external dependencies
@pytest.mark.integration # Requires database
@pytest.mark.slow        # Long-running tests
@pytest.mark.crud        # CRUD operation tests
```

---

## Documentation Conventions

### Markdown Files

- Use ATX-style headers (`#`, `##`, `###`)
- Include table of contents for files > 100 lines
- Use fenced code blocks with language identifier
- Keep lines under 120 characters

### Code Comments

```python
# Good - explains WHY, not WHAT
# Skip system columns that PostgreSQL manages automatically
system_columns = {'datasetid', 'created_at', 'updated_at'}

# Bad - states the obvious
# Loop through configs
for config in configs:
    ...

# Good - warns about non-obvious behavior
# NOTE: psycopg2 requires %% for literal % in LIKE patterns
query = "WHERE name LIKE '%%test%%'"
```

### TODO Comments

```python
# TODO(username): Brief description of what needs to be done
# TODO: Add retry logic for transient failures
# FIXME: This breaks when file_path contains spaces
```

---

## File Organization

### Directory Structure

```
project/
├── admin/                 # Streamlit UI layer
│   ├── pages/             # Individual pages (numbered for ordering)
│   ├── services/          # Business logic (one file per domain)
│   ├── components/        # Reusable UI components
│   └── utils/             # Helper functions
├── common/                # Shared utilities
├── etl/                   # ETL framework
│   ├── base/              # Abstract base classes
│   ├── jobs/              # Concrete job implementations
│   ├── extractors/        # File format extractors
│   └── transformers/      # Data transformers
├── schema/                # Database DDL
│   └── dba/
│       ├── tables/        # One file per table
│       ├── procedures/    # One file per procedure
│       └── views/         # One file per view
└── tests/                 # Test suite
```

### Module Organization

```python
"""
Module docstring explaining purpose and usage.
"""

# Imports (grouped as specified above)
import ...

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Type aliases (if needed)
ConfigDict = Dict[str, Any]

# Public functions (alphabetical or logical order)
def create_config(...):
    ...

def get_config(...):
    ...

def list_configs(...):
    ...

# Private functions (after public)
def _validate_config(...):
    ...

def _process_record(...):
    ...

# Classes (after functions)
class ImportConfig:
    ...

# Entry point (if applicable)
if __name__ == '__main__':
    main()
```

---

## Quick Reference

### SQL Prefixes
| `t` table | `p` procedure | `f` function | `v` view | `idx_` index | `fk_` foreign key |

### Python Naming
| `snake_case` functions/vars | `PascalCase` classes | `UPPER_CASE` constants | `_private` internal |

### Common Patterns
| `get_*` single | `list_*` multiple | `create_*` insert | `update_*` modify | `delete_*` remove |

### Dangerous Patterns to Avoid
- SQL without parameterization
- Single `%` in LIKE patterns (use `%%`)
- Duplicate Streamlit form keys
- Business logic in UI pages
- Test data without `AdminTest_` prefix
