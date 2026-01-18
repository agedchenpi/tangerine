---
name: service-developer
description: Service layer patterns for Tangerine admin - CRUD operations, database transactions, Streamlit integration
---

# Service Developer Guidelines

## Overview

Services encapsulate business logic and database operations. They are called by Streamlit pages but contain no UI code.

## Service Location

```
admin/services/
├── import_config_service.py      # Import configuration CRUD
├── reference_data_service.py     # Datasources, dataset types
├── job_execution_service.py      # Run ETL jobs
├── monitoring_service.py         # Logs, datasets, statistics
├── inbox_config_service.py       # Gmail inbox rules
├── report_manager_service.py     # Report configurations
├── scheduler_service.py          # Cron job management
└── pubsub_service.py             # Event system
```

## Service Pattern

### Basic CRUD Template

```python
"""
Service for managing {entity_name} records.
"""
from common.db_utils import db_transaction


def get_all() -> list[dict]:
    """Return all active records."""
    with db_transaction() as cursor:
        cursor.execute("""
            SELECT * FROM dba.t{entity}
            WHERE is_active = TRUE
            ORDER BY {entity}_id
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_by_id(entity_id: int) -> dict | None:
    """Return single record or None if not found."""
    with db_transaction() as cursor:
        cursor.execute(
            "SELECT * FROM dba.t{entity} WHERE {entity}_id = %s",
            (entity_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def create(data: dict) -> int:
    """Create record and return new ID."""
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.t{entity} (col1, col2, col3)
            VALUES (%(col1)s, %(col2)s, %(col3)s)
            RETURNING {entity}_id
        """, data)
        return cursor.fetchone()["{entity}_id"]


def update(entity_id: int, data: dict) -> bool:
    """Update record. Returns True if updated."""
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.t{entity}
            SET col1 = %(col1)s,
                col2 = %(col2)s,
                last_modified_at = CURRENT_TIMESTAMP
            WHERE {entity}_id = %(id)s
        """, {**data, "id": entity_id})
        return cursor.rowcount > 0


def delete(entity_id: int) -> bool:
    """Delete record. Returns True if deleted."""
    with db_transaction() as cursor:
        cursor.execute(
            "DELETE FROM dba.t{entity} WHERE {entity}_id = %s",
            (entity_id,)
        )
        return cursor.rowcount > 0
```

## Key Rules

### 1. Never Return Streamlit Widgets

```python
# WRONG - couples service to UI
def get_items():
    items = fetch_from_db()
    return st.dataframe(items)  # NO!

# CORRECT - return data only
def get_items() -> list[dict]:
    items = fetch_from_db()
    return items  # Let page handle display
```

### 2. Use Parameterized Queries

```python
# WRONG - SQL injection risk
cursor.execute(f"SELECT * FROM table WHERE name = '{name}'")

# CORRECT - parameterized
cursor.execute("SELECT * FROM table WHERE name = %s", (name,))

# CORRECT - named parameters
cursor.execute(
    "SELECT * FROM table WHERE name = %(name)s AND type = %(type)s",
    {"name": name, "type": type_val}
)
```

### 3. Always Use db_transaction()

```python
from common.db_utils import db_transaction

# Handles connection pooling, commits, and rollbacks
with db_transaction() as cursor:
    cursor.execute(...)
    # Auto-commits on success, rolls back on exception
```

### 4. Return Dicts, Not Rows

```python
# psycopg2 returns RealDictRow objects
row = cursor.fetchone()

# Convert to regular dict for consistency
return dict(row) if row else None

# For multiple rows
return [dict(row) for row in cursor.fetchall()]
```

### 5. Handle None/Empty Cases

```python
def get_by_id(entity_id: int) -> dict | None:
    with db_transaction() as cursor:
        cursor.execute("SELECT * FROM table WHERE id = %s", (entity_id,))
        row = cursor.fetchone()
        return dict(row) if row else None  # Explicit None handling
```

## SQL Naming Conventions

| Object | Prefix | Example |
|--------|--------|---------|
| Table | t | timportconfig |
| Procedure | p | pimportconfigi |
| Function | f | fgetlabel |
| View | v | vimportstatus |
| Index | idx_ | idx_dataset_date |
| Foreign Key | fk_ | fk_dataset_source |

## Common Query Patterns

### Pagination

```python
def get_paginated(page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
    """Return (items, total_count)."""
    offset = (page - 1) * per_page

    with db_transaction() as cursor:
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM dba.ttable")
        total = cursor.fetchone()["count"]

        # Get page
        cursor.execute("""
            SELECT * FROM dba.ttable
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

        return [dict(row) for row in cursor.fetchall()], total
```

### Filtering

```python
def get_filtered(filters: dict) -> list[dict]:
    """Filter by optional criteria."""
    conditions = ["is_active = TRUE"]
    params = []

    if filters.get("status"):
        conditions.append("status = %s")
        params.append(filters["status"])

    if filters.get("date_from"):
        conditions.append("created_at >= %s")
        params.append(filters["date_from"])

    query = f"""
        SELECT * FROM dba.ttable
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
    """

    with db_transaction() as cursor:
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
```

### Check Existence

```python
def exists(name: str, exclude_id: int | None = None) -> bool:
    """Check if name already exists (for duplicate validation)."""
    with db_transaction() as cursor:
        if exclude_id:
            cursor.execute(
                "SELECT 1 FROM dba.ttable WHERE name = %s AND id != %s",
                (name, exclude_id)
            )
        else:
            cursor.execute(
                "SELECT 1 FROM dba.ttable WHERE name = %s",
                (name,)
            )
        return cursor.fetchone() is not None
```

## Error Handling

```python
from psycopg2 import IntegrityError, DatabaseError

def create_with_validation(data: dict) -> tuple[int | None, str | None]:
    """Return (id, error_message)."""
    try:
        with db_transaction() as cursor:
            cursor.execute(...)
            return cursor.fetchone()["id"], None
    except IntegrityError as e:
        if "unique" in str(e).lower():
            return None, "A record with this name already exists"
        if "foreign key" in str(e).lower():
            return None, "Referenced record does not exist"
        return None, f"Database constraint error: {e}"
    except DatabaseError as e:
        return None, f"Database error: {e}"
```

## Testing

Service tests are in `tests/integration/services/`:

```bash
# Run all service tests
docker compose exec tangerine pytest tests/integration/services/ -v

# Run specific service tests
docker compose exec tangerine pytest tests/integration/services/test_import_config_service.py -v
```

Use the `db_transaction` fixture for test isolation:

```python
@pytest.mark.integration
def test_create_item(db_transaction):
    """Test creating an item."""
    with db_transaction() as cursor:
        # Test code here - auto-rolls back after test
```

## Documentation Requirements

**After making service changes, always update documentation:**

1. **CHANGELOG.md** - Add entry under `[Unreleased]` section:
   - `Added` - New services, CRUD operations
   - `Changed` - Modifications to existing services
   - `Fixed` - Bug fixes

2. **Codemaps** (if architecture changes):
   - `.claude/codemaps/admin-services.md` - New services, patterns
   - `.claude/codemaps/database-schema.md` - New tables accessed

3. **Feature docs** (for significant features):
   - Create `docs/features/{feature-name}.md` using `/doc-feature`

**Example CHANGELOG entry:**
```markdown
### Added
- **Audit Service**: Track all CRUD operations with user and timestamp
```
