# Plan: Fix Selectbox Dark Mode Visibility Issues

## Problem Statement

On pages like `/run_jobs` and `/monitoring`, selectbox dropdown elements have white backgrounds and grayish text in dark mode, making them hard to read. The user specifically mentioned:
- Time range dropdowns on /monitoring
- Process type dropdowns on /monitoring
- Max results dropdowns on /monitoring
- Configuration selector on /run_jobs

## Root Cause Analysis

### Current CSS Coverage (Insufficient)

**In `ui_helpers.py` (_apply_theme_css()):**
```css
.stSelectbox select {
    background-color: #2D2D3D !important;
    color: #F0F0F0 !important;
}
```

**In `custom.css`:**
```css
[data-theme="dark"] .stSelectbox > div > div {
    background-color: var(--bg-card-dark) !important;
    color: var(--text-on-dark-bg-bright) !important;
}
```

### Why This Doesn't Work

Streamlit's `st.selectbox()` uses **BaseWeb components** which have a complex rendering structure:

1. **Hidden `<select>` element** - styled by current CSS, but not visible to users
2. **BaseWeb Select wrapper** - the clickable trigger button (visible)
3. **BaseWeb dropdown menu** - the options list popup (visible when clicked)
4. **Portal-rendered overlay** - dropdown renders outside component hierarchy

The current selectors only target the hidden `<select>` element, not the visible BaseWeb components.

### Evidence from Exploration

**Selectbox locations found:**
- `run_jobs.py`: Lines 50-54, 172-177 (2 selectboxes)
- `monitoring.py`: Lines 65-71, 80-86, 98-103, 308-314, 323-329, 348-353, 595-596, 609-610, 620-621, 661-665, 700-704, 710-714, 722-726, 769-773, 827-831 (15+ selectboxes)

**Missing CSS selectors:**
- `[data-baseweb="select"]` - BaseWeb select wrapper/button
- `[data-baseweb="select"] > div` - Select display area
- `[data-baseweb="menu"]` - Dropdown menu container
- `[data-baseweb="option"]` - Individual option items
- `ul[role="listbox"]` - Options list container
- `li[role="option"]` - Individual options in the list

---

## Solution Strategy

Add comprehensive CSS selectors to `_apply_theme_css()` function in `ui_helpers.py` that target all BaseWeb selectbox components, including portal-rendered dropdowns.

### Why This Approach

1. ✅ **Targets visible components** - Styles the actual UI users see, not hidden elements
2. ✅ **Covers dropdown popups** - Styles the expanded options list
3. ✅ **Consistent with existing pattern** - Uses same dynamic injection method as other dark mode fixes
4. ✅ **Maximum specificity** - Uses `!important` to override BaseWeb defaults
5. ✅ **No code changes needed** - Pure CSS fix, no changes to Python files

### Alternative Approaches Considered

**Alternative 1: Fix in custom.css with `[data-theme="dark"]`**
- ❌ Doesn't work - `data-theme` attribute is never set in HTML
- ❌ Previous attempts showed this approach fails

**Alternative 2: Create custom selectbox wrapper component**
- ❌ Over-engineered for a styling issue
- ❌ Would require changing all 17+ selectbox calls across pages
- ❌ Maintenance burden

---

## Implementation Plan

### Phase 1: Add BaseWeb Selectbox CSS to _apply_theme_css()

**File:** `/opt/tangerine/admin/utils/ui_helpers.py`

**Location:** Inside the `_apply_theme_css()` function, in the dark mode CSS block (currently ends around line 456), add new section before the closing `</style>` tag.

**CSS to add:**

```css
/* ===== SELECTBOX COMPONENTS (BaseWeb) ===== */

/* Selectbox trigger button (the clickable area) */
[data-baseweb="select"],
.stSelectbox [data-baseweb="select"],
[data-baseweb="select"] > div,
.stSelectbox [data-baseweb="select"] > div,
.stSelectbox div[data-baseweb="select"] {
    background-color: #2D2D3D !important;
    border-color: #4A4A5A !important;
}

/* Selectbox display text (selected value shown in trigger) */
[data-baseweb="select"] input,
[data-baseweb="select"] div[role="button"],
[data-baseweb="select"] > div > div,
.stSelectbox [data-baseweb="select"] input,
.stSelectbox [data-baseweb="select"] div {
    background-color: #2D2D3D !important;
    color: #F0F0F0 !important;
}

/* Dropdown menu container (the popup that appears) */
[data-baseweb="menu"],
div[data-baseweb="menu"],
[data-baseweb="popover"],
div[data-baseweb="popover"],
ul[role="listbox"],
.stSelectbox ul[role="listbox"] {
    background-color: #2D2D3D !important;
    border: 1px solid #4A4A5A !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
}

/* Individual option items in dropdown */
[data-baseweb="option"],
li[data-baseweb="option"],
li[role="option"],
[data-baseweb="menu"] li,
ul[role="listbox"] li {
    background-color: #2D2D3D !important;
    color: #F0F0F0 !important;
}

/* Hovered option (hover state) */
[data-baseweb="option"]:hover,
li[data-baseweb="option"]:hover,
li[role="option"]:hover,
[aria-selected="true"] {
    background-color: #3D3D4D !important;
    color: #FFFFFF !important;
}

/* Selected option (currently selected) */
[data-baseweb="option"][aria-selected="true"],
li[data-baseweb="option"][aria-selected="true"],
li[role="option"][aria-selected="true"] {
    background-color: #FFA05C !important;
    color: #121212 !important;
}

/* Dropdown arrow icon */
[data-baseweb="select"] svg,
.stSelectbox svg {
    color: #F0F0F0 !important;
    fill: #F0F0F0 !important;
}

/* Fallback for deeply nested selectbox elements */
.stSelectbox,
.stSelectbox > div,
.stSelectbox > div > div,
.stSelectbox > div > div > div {
    background-color: transparent !important;
}

/* Selectbox input field (for searchable selects) */
.stSelectbox input[type="text"],
[data-baseweb="select"] input[type="text"] {
    background-color: #2D2D3D !important;
    color: #F0F0F0 !important;
    border-color: #4A4A5A !important;
}
```

**Insertion point:** Line ~456, just before the closing `</style>` tag in the dark mode CSS block.

### Phase 2: Update Existing Selectbox CSS (Optional Cleanup)

The existing selectbox CSS at lines 346-353 in `_apply_theme_css()` can remain as a fallback, but the new BaseWeb selectors will take precedence.

**Current code (lines 346-353):**
```css
/* ===== INPUTS ===== */
.stTextInput input,
.stSelectbox select,
.stMultiSelect,
.stTextArea textarea {
    background-color: #2D2D3D !important;
    color: #F0F0F0 !important;
    border-color: #4A4A5A !important;
}
```

**Action:** Keep as-is (provides fallback for hidden `<select>` elements).

### Phase 3: Rebuild and Test

1. Rebuild the admin Docker image: `docker compose build admin`
2. Restart the admin container: `docker compose up -d admin`
3. Clear browser cache (Ctrl+Shift+R / Cmd+Shift+R)
4. Test on both /run_jobs and /monitoring pages

---

## Files to Modify

### Critical Files

1. **`/opt/tangerine/admin/utils/ui_helpers.py`**
   - Function: `_apply_theme_css()` (lines 128-479)
   - Add new CSS section at line ~456 (before closing `</style>`)
   - ~60 lines of new CSS

### No Changes Needed

- ✅ `/opt/tangerine/admin/pages/run_jobs.py` - No Python changes
- ✅ `/opt/tangerine/admin/pages/monitoring.py` - No Python changes
- ✅ `/opt/tangerine/admin/styles/custom.css` - Keep existing fallback CSS
- ✅ All other page files - No changes required

---

## Verification Plan

### Test 1: Run Jobs Page Selectboxes

**Steps:**
1. Enable dark mode
2. Navigate to `/run_jobs` page
3. Click on "Select Configuration" dropdown (lines 50-54)
4. Verify dropdown popup has:
   - Dark background (#2D2D3D)
   - Bright white text (#F0F0F0)
   - Visible hover state (#3D3D4D)
   - No white backgrounds
5. Click on "Show last X records" dropdown (lines 172-177)
6. Verify same styling

**Expected result:** All dropdowns have dark backgrounds with bright white text.

### Test 2: Monitoring Page Selectboxes

**Steps:**
1. Stay in dark mode
2. Navigate to `/monitoring` page
3. Test each selectbox:
   - Time range selector
   - Process type selector
   - Max results selector
   - Data source selector (if present)
   - Status selector (if present)
4. For each dropdown, verify:
   - Dark background when closed
   - Dark dropdown popup when opened
   - Bright white text
   - Visible hover states
   - Orange selected state (#FFA05C)

**Expected result:** All 15+ selectboxes have consistent dark mode styling.

### Test 3: Selectbox Hover and Selection

**Steps:**
1. Open any dropdown
2. Hover over options without clicking
3. Verify hover state shows slightly lighter background (#3D3D4D)
4. Click an option
5. Verify selected option shows orange background (#FFA05C) with dark text (#121212)
6. Verify the trigger button shows the selected value with bright white text

**Expected result:** Interactive states are clearly visible and well-contrasted.

### Test 4: Light Mode Regression Test

**Steps:**
1. Toggle dark mode OFF
2. Visit /run_jobs and /monitoring
3. Verify selectboxes still work correctly in light mode
4. Verify no dark backgrounds appear in light mode

**Expected result:** Light mode selectboxes unchanged, using Streamlit defaults.

### Test 5: Other Input Types

**Steps:**
1. In dark mode, verify other form inputs are unaffected:
   - Text inputs (stTextInput)
   - Text areas (stTextArea)
   - Number inputs (stNumberInput)
   - Date inputs (stDateInput)
2. Verify all inputs maintain their dark mode styling

**Expected result:** No regressions in other input types.

---

## Risk Assessment

### Low Risk Changes

- ✅ Pure CSS changes, no Python logic affected
- ✅ Targeting specific BaseWeb components
- ✅ Using `!important` for maximum specificity
- ✅ Fallback CSS remains in place
- ✅ Light mode unaffected (CSS only applies when `is_dark_mode()` is true)

### Potential Issues

1. **BaseWeb class names change in Streamlit updates**
   - Risk: LOW - Streamlit uses stable `data-baseweb` attributes
   - Mitigation: Using both `data-baseweb` and role attributes

2. **Portal rendering causes CSS not to apply**
   - Risk: MEDIUM - Dropdowns render outside component hierarchy
   - Mitigation: Using global selectors, not nested selectors

3. **Specificity conflicts with Streamlit's BaseWeb theme**
   - Risk: LOW - Using `!important` overrides all other rules
   - Mitigation: Maximum specificity selectors

4. **Performance impact from many selectors**
   - Risk: VERY LOW - CSS selectors are highly optimized by browsers
   - Mitigation: Modern browsers handle complex selectors efficiently

---

## Success Criteria

### Visual
- ✅ All selectbox trigger buttons have dark backgrounds (#2D2D3D)
- ✅ All dropdown popups have dark backgrounds (#2D2D3D)
- ✅ All option text is bright white (#F0F0F0)
- ✅ Hover states are visible and distinct (#3D3D4D)
- ✅ Selected options are clearly marked (orange #FFA05C)
- ✅ No white backgrounds visible in dark mode
- ✅ No gray text on light backgrounds

### Functional
- ✅ All selectboxes remain fully functional
- ✅ Selection works correctly
- ✅ Keyboard navigation still works
- ✅ Search functionality (if enabled) still works
- ✅ Light mode selectboxes unaffected

### Technical
- ✅ CSS targets both `data-baseweb` and role attributes
- ✅ Portal-rendered dropdowns are styled
- ✅ Maximum specificity ensures overrides work
- ✅ No Python code changes required
- ✅ Single source of truth (ui_helpers.py)

---

## Rollback Plan

If issues arise:

1. **Partial rollback:** Comment out the new CSS section in ui_helpers.py
2. **Full rollback:** Git checkout the file before changes
3. **Testing:** Can test CSS in browser dev tools before rebuilding container
4. **Isolation:** Changes only affect selectbox styling, all other components unaffected

---

## Implementation Steps

1. ✅ Read existing plan file (completed)
2. ✅ Explore codebase for selectbox usage (completed)
3. ✅ Analyze current CSS coverage (completed)
4. ✅ Design solution (completed)
5. ⬜ Edit ui_helpers.py to add BaseWeb selectbox CSS
6. ⬜ Rebuild Docker image
7. ⬜ Test on /run_jobs page
8. ⬜ Test on /monitoring page
9. ⬜ Verify light mode unchanged
10. ⬜ Confirm with user

---

## Summary

**Problem:** Selectbox dropdowns have white backgrounds and gray text in dark mode, making them hard to read on /run_jobs and /monitoring pages.

**Root Cause:** Current CSS only targets hidden `<select>` elements, not the visible BaseWeb components used by Streamlit.

**Solution:** Add comprehensive CSS selectors targeting BaseWeb select components (`[data-baseweb="select"]`, `[data-baseweb="menu"]`, `[data-baseweb="option"]`) to `_apply_theme_css()` in ui_helpers.py.

**Benefit:** All 17+ selectboxes across run_jobs and monitoring pages will have proper dark mode styling with dark backgrounds and bright white text.

**Effort:** Low - single CSS addition to one function, ~60 lines of CSS.

**Risk:** Low - pure CSS change, no Python logic affected, light mode unaffected.
