# UX Improvements: Inline Create for Dependencies

## Objective
Add "(Create New)" option to dropdowns so users can create new datasources/datasettypes directly from the Imports form without navigating away.

---

## Current Behavior
- Imports form has dropdowns for Data Source and Dataset Type
- If the desired option doesn't exist, user must navigate to Reference Data page, create it, then return
- This breaks the user's workflow

## Desired Behavior
- Each dropdown (datasource, datasettype) has a "+ Create New" option
- Selecting it reveals an inline form to create the new entity
- After creation, the new entity is auto-selected in the dropdown
- User can continue filling out the import form without leaving the page

---

## Implementation Approach

### Option A: Expander-based inline form (Recommended)
Add a collapsible expander below each dropdown that contains a mini-form to create a new entity.

**Pros:**
- Works well with Streamlit's form limitations (no nested forms)
- Clean UX - doesn't clutter the page
- Easy to implement

**Cons:**
- Creation happens outside the main form, requires rerun

### Option B: st.dialog modal
Use Streamlit's dialog component for a modal popup.

**Pros:**
- More polished UX
- Feels like a proper modal

**Cons:**
- Requires Streamlit 1.33+ for @st.dialog decorator
- More complex state management

---

## Implementation Plan (Option A)

### File: `admin/components/forms.py`

**Changes to `render_import_config_form()`:**

1. After the datasource selectbox, add an expander "Need a new data source?"
   - Contains inline form fields (name, description)
   - Has "Create" button
   - On success: shows success message, triggers rerun so dropdown refreshes

2. After the datasettype selectbox, add same pattern for dataset types

**Code structure:**
```python
# Datasource selection
datasource = st.selectbox("Data Source *", options=datasources, ...)

# Inline create option
with st.expander("+ Add new data source"):
    new_ds_name = st.text_input("Name", key="new_ds_name")
    new_ds_desc = st.text_area("Description", key="new_ds_desc")
    if st.button("Create Data Source", key="create_ds_btn"):
        # Validate and create
        # Set session state to select the new one
        # Rerun
```

### Session State for Auto-selection
After creating a new datasource/datasettype, store the new name in session state so the dropdown auto-selects it on rerun.

---

## Files to Modify

| File | Changes |
|------|---------|
| `admin/components/forms.py` | Add inline create expanders for datasource and datasettype |

## Files to Revert (from previous implementation)

| File | Action |
|------|--------|
| `admin/pages/imports.py` | Remove dependency status expander (not needed) |
| `admin/components/dependency_checker.py` | Keep - still useful for other pages |

---

## Verification

1. Go to Imports > Create New
2. Click "+ Add new data source" expander
3. Enter name and description, click Create
4. Verify: datasource is created and auto-selected in dropdown
5. Repeat for dataset type
6. Complete import config creation
7. Verify the new datasource/datasettype appear in Reference Data page

---

## Keep from Previous Implementation

These changes are still valuable and should remain:
- Reference Data page: "Used by X configs" badges
- Reference Data page: Delete protection with specific config names
- Scheduler page: "Create Config" links when empty
- Event System page: "Create Config" links when empty
- `dependency_checker.py`: Reusable for Scheduler/Event System pages
