# New Page: SQL Query Runner (`/sql`)

## Context
Add an admin page where users can type SQL queries, execute them against the database, and view results in a data grid. This is a developer/admin utility for ad-hoc data exploration.

## Changes

### 1. Create page file: `admin/pages/sql.py`

- `load_custom_css()` + `add_page_header("SQL Query Runner", icon="🔍", subtitle="...")`
- `st.text_area` for SQL input (with placeholder example query)
- "Run Query" button
- On submit: call `fetch_dict(query)` to execute
- Display results as `st.dataframe(pd.DataFrame(results), use_container_width=True)` with row count caption
- Error handling with `format_sql_error(e)`
- **Read-only enforcement**: Strip query, reject if it doesn't start with `SELECT` (prevent mutations from this page)
- No service layer needed — this is a direct query tool

### 2. Register page: `admin/app.py`

Add to the `"System"` section of the `pages` dict:
```python
st.Page("pages/sql.py", title="SQL", icon="🔍"),
```

## Key Files
- `admin/pages/sql.py` (new)
- `admin/app.py` (~line 66-88, pages dict)
- `common/db_utils.py` — reuse `fetch_dict()`
- `admin/utils/db_helpers.py` — reuse `format_sql_error()`
- `admin/utils/ui_helpers.py` — reuse `load_custom_css()`, `add_page_header()`
- `admin/components/notifications.py` — reuse `show_error`, `show_info`

## Verification
1. `docker compose up -d --build admin`
2. Navigate to `/sql` in sidebar
3. Enter `SELECT * FROM dba.timportconfig LIMIT 5` and click Run — results should display in a grid
4. Enter `DELETE FROM dba.timportconfig` — should be rejected with an error message
