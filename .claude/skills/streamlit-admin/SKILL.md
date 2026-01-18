---
name: streamlit-admin
description: Streamlit UI patterns for Tangerine admin interface - pages, forms, components, notifications
---

# Streamlit Admin Guidelines

## Overview

The admin interface uses Streamlit with a custom Tangerine theme. Pages are auto-discovered from the `pages/` directory.

## Directory Structure

```
admin/
├── app.py               # Landing page / dashboard
├── pages/               # Auto-discovered pages (numbered for order)
│   ├── 1_Import_Configs.py
│   ├── 2_Reference_Data.py
│   ├── 3_Run_Jobs.py
│   ├── 4_Monitoring.py
│   ├── 5_Inbox_Configs.py
│   ├── 6_Report_Manager.py
│   ├── 7_Scheduler.py
│   └── 8_Event_System.py
├── components/          # Reusable UI components
│   ├── forms.py
│   ├── tables.py
│   ├── validators.py
│   └── notifications.py
├── services/            # Business logic (no UI code!)
├── utils/               # Helpers
│   ├── db_helpers.py
│   ├── formatters.py
│   └── ui_helpers.py
└── styles/
    └── custom.css       # Tangerine theme
```

## Page Template

```python
"""
Page: Entity Management
CRUD interface for managing entities.
"""
import streamlit as st

from admin.components.notifications import show_error, show_success
from admin.services.entity_service import create, delete, get_all, get_by_id, update
from admin.utils.ui_helpers import add_page_header, load_custom_css

# Page configuration (MUST be first Streamlit call)
st.set_page_config(
    page_title="Entity Management",
    page_icon="📊",
    layout="wide"
)

# Load custom styling
load_custom_css()

# Page header
add_page_header(
    "Entity Management",
    icon="📊",
    subtitle="Create, view, and manage entities"
)

# Handle success messages from previous actions
if "success_message" in st.session_state:
    show_success(st.session_state.success_message)
    del st.session_state.success_message

# Main content with tabs
tab_list, tab_create = st.tabs(["📋 List", "➕ Create"])

with tab_list:
    items = get_all()
    if items:
        for item in items:
            with st.expander(f"**{item['name']}** (ID: {item['id']})"):
                st.write(f"Description: {item['description']}")

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("Edit", key=f"edit_{item['id']}"):
                        st.session_state.editing_id = item["id"]
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{item['id']}", type="secondary"):
                        if delete(item["id"]):
                            st.session_state.success_message = f"Deleted {item['name']}"
                            st.rerun()
    else:
        st.info("No items found. Create one using the Create tab.")

with tab_create:
    with st.form("create_form", clear_on_submit=True):
        name = st.text_input("Name", max_chars=100)
        description = st.text_area("Description")

        if st.form_submit_button("Create", type="primary"):
            if not name:
                show_error("Name is required")
            else:
                try:
                    new_id = create({"name": name, "description": description})
                    st.session_state.success_message = f"Created '{name}' (ID: {new_id})"
                    st.rerun()
                except Exception as e:
                    show_error(f"Failed to create: {e}")
```

## Key Patterns

### 1. Session State for Messages

Success messages must persist across `st.rerun()`:

```python
# After successful action
st.session_state.success_message = "Operation completed!"
st.rerun()

# At page load, display and clear
if "success_message" in st.session_state:
    show_success(st.session_state.success_message)
    del st.session_state.success_message
```

### 2. Unique Form Keys

Forms need unique keys, especially in loops:

```python
# WRONG - conflicts when multiple forms exist
with st.form(key="my_form"):
    ...

# CORRECT - unique per item
with st.form(key=f"edit_form_{item_id}"):
    ...

# CORRECT - unique per context
form_key = "create_form" if not editing else f"edit_form_{editing_id}"
with st.form(key=form_key):
    ...
```

### 3. Tabs for CRUD Operations

```python
tab_list, tab_create, tab_edit = st.tabs(["📋 List", "➕ Create", "✏️ Edit"])

# Or dynamic tabs based on state
if st.session_state.get("editing_id"):
    tabs = st.tabs(["📋 List", "✏️ Edit"])
else:
    tabs = st.tabs(["📋 List", "➕ Create"])
```

### 4. Expanders for Detail Views

```python
items = get_all()
for item in items:
    with st.expander(f"**{item['name']}**", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**ID:** {item['id']}")
            st.write(f"**Status:** {'Active' if item['is_active'] else 'Inactive'}")
        with col2:
            st.write(f"**Created:** {item['created_at']}")
```

### 5. Services for Logic

Pages call services, never raw SQL:

```python
# WRONG - SQL in page
cursor.execute("SELECT * FROM dba.ttable")

# CORRECT - use service
from admin.services.entity_service import get_all
items = get_all()
```

## Notifications

```python
from admin.components.notifications import (
    show_success,
    show_error,
    show_warning,
    show_info
)

show_success("Record created successfully!")
show_error("Failed to save: validation error")
show_warning("This action cannot be undone")
show_info("Tip: Use filters to narrow results")
```

## Custom CSS

Always load at page start:

```python
from admin.utils.ui_helpers import load_custom_css

# After st.set_page_config()
load_custom_css()
```

## UI Helper Functions

```python
from admin.utils.ui_helpers import (
    load_custom_css,        # Load Tangerine theme
    add_page_header,        # Styled page header with icon
    with_loading,           # Execute function with spinner
    safe_execute,           # Error handling wrapper
    render_empty_state,     # Placeholder for no data
    render_stat_card,       # Metric card with styling
)

# Page header
add_page_header("Dashboard", icon="📊", subtitle="System overview")

# Loading spinner
result = with_loading(expensive_function, "Loading data...")

# Stat cards
col1, col2, col3 = st.columns(3)
with col1:
    render_stat_card("Total Records", 1234, delta="+12%")
```

## Form Validation

```python
from admin.components.validators import (
    validate_required,
    validate_email,
    validate_regex_pattern,
    validate_path_exists,
)

with st.form("create_form"):
    name = st.text_input("Name")
    email = st.text_input("Email")
    pattern = st.text_input("Regex Pattern")

    if st.form_submit_button("Create"):
        errors = []

        if not validate_required(name):
            errors.append("Name is required")

        if email and not validate_email(email):
            errors.append("Invalid email format")

        if pattern and not validate_regex_pattern(pattern):
            errors.append("Invalid regex pattern")

        if errors:
            for error in errors:
                show_error(error)
        else:
            # Proceed with creation
            pass
```

## Data Display

### Tables

```python
import pandas as pd

items = get_all()
if items:
    df = pd.DataFrame(items)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "name": st.column_config.TextColumn("Name", width="medium"),
            "created_at": st.column_config.DatetimeColumn("Created", format="YYYY-MM-DD HH:mm"),
        }
    )
```

### Metrics

```python
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Jobs", 156, delta="+12")
with col2:
    st.metric("Success Rate", "98.5%", delta="+0.5%")
with col3:
    st.metric("Failed Today", 2, delta="-3", delta_color="inverse")
with col4:
    st.metric("Pending", 5)
```

## Common Pitfalls

1. **Don't put st.set_page_config() after other Streamlit calls** - Must be first
2. **Don't use same form key twice** - Causes conflicts
3. **Don't forget st.rerun() after state changes** - UI won't update
4. **Don't put heavy computation in main flow** - Use caching or spinners
5. **Don't mix UI and business logic** - Keep services separate

## Testing Admin Pages

Pages are harder to test directly. Focus on testing:
- Services (unit/integration tests)
- Validators (unit tests)
- Formatters (unit tests)

```bash
# Run all admin tests
docker compose exec tangerine pytest tests/ -v

# Run service tests only
docker compose exec tangerine pytest tests/integration/services/ -v
```

## Documentation Requirements

**After making changes to admin pages, always update documentation:**

1. **CHANGELOG.md** - Add entry under `[Unreleased]` section:
   - `Added` - New features/pages
   - `Changed` - Modifications to existing functionality
   - `Fixed` - Bug fixes

2. **Codemaps** (if architecture changes):
   - `.claude/codemaps/admin-services.md` - Service layer changes
   - `.claude/codemaps/architecture-overview.md` - New pages/components

3. **Feature docs** (for significant features):
   - Create `docs/features/{feature-name}.md` using `/doc-feature`

**Example CHANGELOG entry:**
```markdown
### Changed
- **Inbox Rules UX**: Added inline pattern examples and Quick Start guide
```

This ensures future developers (and Claude) understand what changed and why.
