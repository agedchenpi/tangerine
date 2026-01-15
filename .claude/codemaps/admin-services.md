# Admin Services Codemap

## Purpose

Service layer for the Streamlit admin interface. Implements business logic and database operations, decoupled from UI rendering.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Streamlit Page (admin/pages/*.py)                       │
│  - Handles user input, displays results                  │
│  - Calls service functions, catches exceptions           │
│  - Uses st.session_state for cross-rerun state           │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Service Layer (admin/services/*.py)                     │
│  - Pure Python functions (no Streamlit imports)          │
│  - Returns dicts/lists, raises exceptions on error       │
│  - Uses db_transaction() for all database operations     │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Database Utilities (common/db_utils.py)                 │
│  - Connection pooling                                    │
│  - Transaction management with auto-commit/rollback      │
│  - fetch_dict() returns List[Dict]                       │
└──────────────────────────────────────────────────────────┘
```

## Service Files

| File | Domain | Key Functions |
|------|--------|---------------|
| `import_config_service.py` | Import configurations | list_configs, get_config, create_config, update_config, delete_config |
| `reference_data_service.py` | Datasources, dataset types | get_datasources, create_datasource, get_datasettypes |
| `job_execution_service.py` | Running ETL jobs | execute_import_job (subprocess), get_job_history |
| `monitoring_service.py` | Logs, datasets, stats | get_logs, get_datasets, get_statistics |
| `inbox_config_service.py` | Gmail inbox rules | list_inbox_configs, create_inbox_config, delete_inbox_config |
| `report_manager_service.py` | Email reports | list_reports, create_report, update_report |
| `scheduler_service.py` | Cron job configs | list_scheduled_jobs, create_scheduled_job |
| `pubsub_service.py` | Event queue | list_events, create_event, list_subscribers |

## CRUD Pattern

All services follow this naming convention:

```python
# List with optional filters
def list_configs(active_only: bool = False, ...) -> List[Dict[str, Any]]:

# Get single by ID
def get_config(config_id: int) -> Optional[Dict[str, Any]]:

# Create (returns new ID)
def create_config(config_data: Dict[str, Any]) -> int:

# Update (void, raises on error)
def update_config(config_id: int, config_data: Dict[str, Any]) -> None:

# Delete (void, raises on error)
def delete_config(config_id: int) -> None:

# Check existence
def config_name_exists(name: str, exclude_id: Optional[int] = None) -> bool:

# Get stats
def get_config_stats() -> Dict[str, int]:
```

## Database Transaction Pattern

```python
from common.db_utils import fetch_dict, db_transaction

# Read operations (auto-managed connection)
def list_items() -> List[Dict]:
    query = "SELECT * FROM dba.table WHERE condition = %s"
    return fetch_dict(query, (param,))

# Write operations (explicit transaction)
def create_item(data: Dict) -> int:
    with db_transaction() as cursor:
        cursor.execute(
            "INSERT INTO dba.table (col) VALUES (%s) RETURNING id",
            (data['col'],)
        )
        return cursor.fetchone()[0]
```

## Key Conventions

1. **Parameterized Queries Only**: Never use f-strings for SQL
   ```python
   # WRONG
   cursor.execute(f"SELECT * FROM table WHERE id = {id}")

   # CORRECT
   cursor.execute("SELECT * FROM table WHERE id = %s", (id,))
   ```

2. **Double %% in LIKE Patterns** (psycopg2 quirk):
   ```python
   # WRONG - causes "tuple index out of range"
   query = "SELECT * FROM table WHERE name LIKE '%prefix%'"

   # CORRECT
   query = "SELECT * FROM table WHERE name LIKE '%%prefix%%'"
   ```

3. **Return Types**:
   - List operations: `List[Dict[str, Any]]`
   - Single item: `Optional[Dict[str, Any]]`
   - Create: `int` (new ID)
   - Update/Delete: `None` (raises on error)
   - Stats: `Dict[str, int]`

4. **Error Handling**: Services raise exceptions, pages catch and display

## Integration with Pages

```python
# In admin/pages/1_Import_Configs.py
from admin.services import import_config_service as service
from admin.components.notifications import show_success, show_error

try:
    new_id = service.create_config(form_data)
    st.session_state.success_message = f"Created config {new_id}"
    st.rerun()
except Exception as e:
    show_error(f"Failed to create: {e}")
```

## Test Coverage

- 311 pytest tests covering all services
- Integration tests use `db_transaction` fixture with auto-rollback
- Test data uses `AdminTest_*` prefix for cleanup
- 85% minimum coverage enforced
