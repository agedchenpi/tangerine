# Plan: Fix Container/Card White Backgrounds in Dark Mode

## Problem Summary

After fixing metric cards, **container and card backgrounds** (from `st.container()`, `st.columns()`, and similar Streamlit elements) still display white or light backgrounds in dark mode.

**User Requirement:**
- Dark mode should have dark backgrounds for ALL containers, cards, and wrapper elements
- No white/light backgrounds should be visible anywhere in dark mode

**Current Issue:**
Despite comprehensive dark mode CSS (lines 973-1189 in custom.css), Streamlit's container wrapper elements don't have dark backgrounds because they use runtime-generated classes that aren't explicitly targeted.

---

## Root Cause Analysis

### Issue: Missing CSS Selectors for Streamlit Container Wrappers

**Problem:**
Streamlit generates container elements at runtime with specific CSS classes:
- `[data-testid="stVerticalBlock"]` - Vertical layout containers
- `[data-testid="stHorizontalBlock"]` - Horizontal layout containers (columns)
- `[data-testid="column"]` - Individual columns
- `div[data-testid^="st"]` - Various Streamlit wrapper divs

These elements inherit Streamlit's default styling, which often includes white or transparent backgrounds that show the parent's light background.

**Why Dark Mode CSS Doesn't Apply:**

Current dark mode CSS (lines 1005-1010) only targets:
```css
[data-theme="dark"] .stApp,
[data-theme="dark"] .main,
[data-theme="dark"] .block-container {
    background-color: var(--bg-body) !important;
    color: var(--text-on-dark-bg) !important;
}
```

But it **doesn't target**:
- Vertical/horizontal block containers
- Column wrappers
- Generic Streamlit container divs
- Nested container elements

**Result:** White/light backgrounds show through on container elements.

---

## Evidence from Codebase Investigation

### 1. Container Usage is Extensive

Found `st.container()` and `st.columns()` usage in:
- `/opt/tangerine/admin/pages/home.py` (lines 26, 140)
- `/opt/tangerine/admin/pages/monitoring.py`
- `/opt/tangerine/admin/pages/scheduler.py`
- `/opt/tangerine/admin/pages/event_system.py`
- `/opt/tangerine/admin/pages/imports.py`
- `/opt/tangerine/admin/pages/reference_data.py`
- `/opt/tangerine/admin/pages/reports.py`
- `/opt/tangerine/admin/pages/run_jobs.py`
- `/opt/tangerine/admin/pages/inbox_rules.py`
- `/opt/tangerine/admin/utils/ui_helpers.py`

All use bare Streamlit containers without custom styling, relying on CSS for theming.

### 2. Current Dark Mode CSS Coverage

**What IS covered** (lines 973-1189 in custom.css):
✅ `.stApp`, `.main`, `.block-container` - Main page containers
✅ `[data-testid="stMetric"]` - Metric cards (recently fixed)
✅ `[data-testid="stDataFrame"]` - Data tables
✅ `[data-testid="stSidebar"]` - Sidebar
✅ `.stTextInput`, `.stSelectbox`, etc. - Form inputs
✅ `.stTabs` - Tab containers
✅ `.streamlit-expanderHeader` - Expanders
✅ `.stButton` - Buttons
✅ `.stPlotlyChart` - Charts

**What is MISSING:**
❌ `[data-testid="stVerticalBlock"]` - Vertical containers
❌ `[data-testid="stHorizontalBlock"]` - Horizontal containers (columns)
❌ `[data-testid="column"]` - Individual columns
❌ Generic container wrapper divs

### 3. CSS Variable Defaults

Lines 42-43 in custom.css define:
```css
--bg-card: #FFFFFF;
--bg-light: #F8F9FA;
```

While dark mode overrides exist for CSS variables (lines 989-991):
```css
--bg-body: #121212;
--bg-card-dark: #1E1E2E;
--bg-card-light: #FFFFFF;  /* Kept for light-bg-in-dark override class */
```

**However:** Streamlit's default container styling doesn't reference these variables - it uses hardcoded values or inherits from parent elements.

---

## Solution: Add Dark Mode CSS for Streamlit Container Elements

### Strategy

Add comprehensive CSS selectors targeting all Streamlit container wrapper elements to ensure dark backgrounds in dark mode.

**Why This Works:**
1. ✅ **Targets runtime-generated classes** - Covers all Streamlit container types
2. ✅ **Uses !important** - Overrides Streamlit's default styling
3. ✅ **Consistent with existing dark mode CSS** - Uses same color scheme and patterns
4. ✅ **No Python code changes** - Pure CSS fix, no need to modify component usage
5. ✅ **Future-proof** - Covers generic `div[data-testid^="st"]` selector for new components

---

## Implementation Plan

### Change: Add Container Dark Mode CSS to `custom.css`

**File:** `/opt/tangerine/admin/styles/custom.css`

**Action:** Add container selectors after line 1022 (after metric cards section, before dataframes section)

**Current Code (lines 1020-1032):**
```css
[data-theme="dark"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #FFA05C !important;
}

/* ===== TABS ===== */

/* Tab container - dark background */
[data-theme="dark"] .stTabs [data-baseweb="tab-list"] {
    background-color: var(--bg-card-dark) !important;
}
```

**New Code:**
```css
[data-theme="dark"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #FFA05C !important;
}

/* ===== CONTAINERS & WRAPPERS ===== */

/* Vertical block containers (from st.container, default layout) */
[data-theme="dark"] [data-testid="stVerticalBlock"],
[data-theme="dark"] div[data-testid="stVerticalBlock"] > div {
    background-color: transparent !important;
}

/* Horizontal block containers (from st.columns) */
[data-theme="dark"] [data-testid="stHorizontalBlock"],
[data-theme="dark"] div[data-testid="stHorizontalBlock"] > div {
    background-color: transparent !important;
}

/* Individual columns */
[data-theme="dark"] [data-testid="column"],
[data-theme="dark"] div[data-testid="column"] {
    background-color: transparent !important;
}

/* Generic Streamlit container wrappers - catch-all for any missed containers */
[data-theme="dark"] div[data-testid^="st"]:not([data-testid="stMetric"]):not([data-testid="stDataFrame"]):not([data-testid="stSidebar"]) {
    background-color: transparent !important;
}

/* ===== TABS ===== */

/* Tab container - dark background */
[data-theme="dark"] .stTabs [data-baseweb="tab-list"] {
    background-color: var(--bg-card-dark) !important;
}
```

**Why Transparent Instead of Dark Color:**
- Containers should inherit the dark background from parent `.stApp` / `.main` (which are set to `#121212`)
- Using `transparent` allows the dark background to show through
- Prevents "double-dark" layering that could create visual artifacts
- Cards/metrics that need explicit dark backgrounds already have them (lines 1025-1029)

**Alternative Approach (if transparent doesn't work):**
If testing shows that containers still show light backgrounds with `transparent`, change to explicit dark color:
```css
background-color: var(--bg-body) !important;  /* #121212 */
```

---

## Verification Plan

### Test 1: Home Page Containers

**Page:** `/opt/tangerine/admin/pages/home.py`

**Setup:**
1. Navigate to Home page
2. Enable dark mode
3. Inspect container elements using DevTools

**Expected Visual:**
- ✅ System Status section (uses `st.columns(4)` at line 26) has dark background
- ✅ All column wrappers have dark backgrounds
- ✅ No white/light containers visible anywhere
- ✅ Metric cards within columns have proper dark backgrounds (from previous fix)

**DevTools Verification:**
```
Selector: [data-testid="stHorizontalBlock"]
Computed Styles:
  background-color: transparent (or rgb(18, 18, 18) if using explicit color)

Selector: [data-testid="column"]
Computed Styles:
  background-color: transparent (or rgb(18, 18, 18))

Selector: [data-testid="stVerticalBlock"]
Computed Styles:
  background-color: transparent (or rgb(18, 18, 18))
```

---

### Test 2: Monitoring Page (Heavy Container Usage)

**Page:** `/opt/tangerine/admin/pages/monitoring.py`

**Setup:**
1. Navigate to Monitoring page
2. Enable dark mode
3. Check all sections (ETL Logs, Recent Datasets, Runtime Stats)

**Expected:**
- ✅ All container sections have dark backgrounds
- ✅ Data tables have dark backgrounds (from existing CSS)
- ✅ No white flashes or light containers
- ✅ Tabs (if present) have dark backgrounds

---

### Test 3: Scheduler Page (Columns + Metrics)

**Page:** `/opt/tangerine/admin/pages/scheduler.py`

**Setup:**
1. Navigate to Scheduler page
2. Enable dark mode
3. Check metric cards section (uses columns)

**Expected:**
- ✅ Column containers wrapping metrics have dark backgrounds
- ✅ Metric cards themselves have dark backgrounds (from previous fix)
- ✅ All vertical containers (schedule listings) have dark backgrounds

---

### Test 4: Reference Data Page (Multiple Tabs + Containers)

**Page:** `/opt/tangerine/admin/pages/reference_data.py`

**Setup:**
1. Navigate to Reference Data page
2. Enable dark mode
3. Switch between tabs (Datasources, Dataset Types, Holidays)

**Expected:**
- ✅ Tab container has dark background
- ✅ Content within each tab has dark background
- ✅ All nested containers (if any) have dark backgrounds

---

### Test 5: Generic Container Test (st.container() usage)

**Check Pages:**
- Event System
- Imports
- Reports
- Run Jobs
- Inbox Rules

**Expected:**
- ✅ All pages using `st.container()` have dark backgrounds
- ✅ No white/light containers anywhere
- ✅ Consistent dark mode experience across all pages

---

### Test 6: Theme Toggle Persistence

**Setup:**
1. Toggle dark mode ON
2. Navigate between multiple pages
3. Refresh page (F5, not hard refresh)

**Expected:**
- ✅ Dark mode persists across navigation
- ✅ All containers remain dark after page transitions
- ✅ No flashing of white backgrounds during Streamlit reruns

---

### Troubleshooting

**If containers still show white backgrounds:**

1. **Hard refresh browser** (Ctrl+Shift+R / Cmd+Shift+R) to clear CSS cache

2. **Check DevTools → Elements → Computed Styles:**
   - Find a white container element
   - Check which CSS rule is setting the background
   - Note the specificity and source

3. **Verify `data-theme` attribute:**
   ```
   <html data-theme="dark">
   <body data-theme="dark">
   <div class="stApp" data-theme="dark">
   ```
   All three should have the attribute (from previous fix)

4. **Check CSS load order in DevTools → Network:**
   - Verify `custom.css` loads after Streamlit's default CSS
   - If not, the issue is load order - need to adjust how CSS is injected

5. **Try explicit background color instead of transparent:**
   If `background-color: transparent` doesn't work, change all new container rules to:
   ```css
   background-color: var(--bg-body) !important;  /* #121212 */
   ```

6. **Inspect nested divs:**
   - Use DevTools to find the exact element with white background
   - Copy its `data-testid` or class name
   - Add specific selector for that element

7. **Check for inline styles:**
   If any elements have `style="background-color: white"` in the HTML, the issue is Python code setting inline styles:
   - Search Python files for `style=` or `background` in st.markdown calls
   - Add dark mode awareness to those components

8. **Browser extensions:**
   - Test in incognito/private window to rule out extensions
   - Some extensions inject CSS that can override theming

---

## Alternative Solutions (if CSS doesn't fully work)

### Option 1: Use Streamlit's config.toml Theme

If CSS overrides prove insufficient, modify Streamlit's theme configuration:

**File:** `/.streamlit/config.toml` (create if doesn't exist)

```toml
[theme]
primaryColor = "#FF8C42"
backgroundColor = "#121212"
secondaryBackgroundColor = "#1E1E2E"
textColor = "#F0F0F0"
font = "sans serif"
```

**Pros:**
- Streamlit applies theme at component generation time
- No CSS specificity battles
- Works for all components automatically

**Cons:**
- Replaces Streamlit's default theme entirely
- No light/dark mode toggle - single theme only
- Requires app restart to change theme
- Doesn't support dynamic theme switching

**Verdict:** Not suitable for this use case since we need light/dark mode toggle

---

### Option 2: Custom Container Component Wrapper

Create a Python helper function that wraps containers with dark mode aware styling:

**File:** `/opt/tangerine/admin/utils/ui_helpers.py`

```python
def dark_container():
    """Create a container with dark mode aware background."""
    colors = get_theme_colors()
    container = st.container()
    if is_dark_mode():
        st.markdown(f"""
        <style>
        [data-testid="stVerticalBlock"]:last-of-type {{
            background-color: {colors['bg']} !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    return container
```

**Usage:**
```python
# Instead of: with st.container():
with dark_container():
    # content here
```

**Pros:**
- Guaranteed to work
- Explicit control over styling

**Cons:**
- Requires changing all existing code that uses `st.container()` or `st.columns()`
- 50+ locations to update across 10 files
- Maintenance burden

**Verdict:** Only use if CSS solution completely fails

---

### Option 3: JavaScript DOM Manipulation

Add JavaScript to dynamically apply dark backgrounds to containers:

**File:** `/opt/tangerine/admin/utils/ui_helpers.py` in `_apply_theme_css()`

```python
<script>
// Set dark backgrounds on all Streamlit containers
if (document.body.getAttribute('data-theme') === 'dark') {
    document.querySelectorAll('[data-testid^="st"]').forEach(el => {
        if (!['stMetric', 'stDataFrame', 'stSidebar'].includes(el.getAttribute('data-testid'))) {
            el.style.backgroundColor = 'transparent';
        }
    });
}
</script>
```

**Pros:**
- Catches all container types dynamically
- No CSS specificity issues

**Cons:**
- Runs on every page load/rerun
- Can cause flashing as elements are styled after render
- Performance impact on large pages

**Verdict:** Use only as last resort

---

## Recommended Approach

**Primary:** CSS selector additions (described in Implementation Plan)
- Cleanest solution
- No code changes required
- Leverages existing dark mode architecture
- Minimal performance impact

**Fallback:** If containers still white after CSS, use JavaScript DOM manipulation as a patch while investigating root cause

---

## Critical Files

**Files to Modify:**

1. **`/opt/tangerine/admin/styles/custom.css`**
   - Add container selectors after line 1022 (~20 lines)
   - Target: `[data-testid="stVerticalBlock"]`, `[data-testid="stHorizontalBlock"]`, `[data-testid="column"]`, and generic `div[data-testid^="st"]`

**Files Referenced (No Changes - For Testing Only):**
- `/opt/tangerine/admin/pages/home.py` - Test columns/containers
- `/opt/tangerine/admin/pages/monitoring.py` - Test heavy container usage
- `/opt/tangerine/admin/pages/scheduler.py` - Test columns + metrics
- `/opt/tangerine/admin/pages/reference_data.py` - Test tabs + containers
- `/opt/tangerine/admin/pages/event_system.py` - Test st.container() usage

---

## Success Criteria

**Dark Mode:**
✅ All container backgrounds are dark (transparent over dark parent, or explicit dark color)
✅ No white/light backgrounds visible on any page
✅ Vertical containers (st.container()) have dark backgrounds
✅ Horizontal containers (st.columns()) have dark backgrounds
✅ Individual columns have dark backgrounds
✅ All Streamlit wrapper divs have dark backgrounds

**Light Mode:**
✅ No regression - containers remain light/white as before
✅ All original styling preserved

**Overall:**
✅ User requirement satisfied: No white containers anywhere in dark mode
✅ Fix applies immediately on theme toggle
✅ Fix persists across page navigation and Streamlit reruns
✅ Consistent dark mode experience across all admin pages

---

## Implementation Summary

### Changes Required

**File: `/opt/tangerine/admin/styles/custom.css`**

1. **Add after line 1022** (after metric cards, before tabs section)
   - Vertical block container selectors
   - Horizontal block container selectors
   - Individual column selectors
   - Generic Streamlit container catch-all

**Total:** ~20 lines of CSS added

---

### Detailed Code Change

**Find (line 1022):**
```css
[data-theme="dark"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #FFA05C !important;
}

/* ===== TABS ===== */
```

**Replace with:**
```css
[data-theme="dark"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #FFA05C !important;
}

/* ===== CONTAINERS & WRAPPERS ===== */

/* Vertical block containers (from st.container, default layout) */
[data-theme="dark"] [data-testid="stVerticalBlock"],
[data-theme="dark"] div[data-testid="stVerticalBlock"] > div {
    background-color: transparent !important;
}

/* Horizontal block containers (from st.columns) */
[data-theme="dark"] [data-testid="stHorizontalBlock"],
[data-theme="dark"] div[data-testid="stHorizontalBlock"] > div {
    background-color: transparent !important;
}

/* Individual columns */
[data-theme="dark"] [data-testid="column"],
[data-theme="dark"] div[data-testid="column"] {
    background-color: transparent !important;
}

/* Generic Streamlit container wrappers - catch-all for any missed containers */
[data-theme="dark"] div[data-testid^="st"]:not([data-testid="stMetric"]):not([data-testid="stDataFrame"]):not([data-testid="stSidebar"]) {
    background-color: transparent !important;
}

/* ===== TABS ===== */
```

---

### Post-Implementation Steps

1. **Restart admin container:**
   ```bash
   docker compose restart admin
   ```

2. **Hard refresh browser:**
   - Windows/Linux: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

3. **Test on pages with containers:**
   - Home page (System Status columns)
   - Monitoring page (multiple sections)
   - Scheduler page (metrics in columns)
   - Reference Data page (tabs + containers)
   - All other admin pages

4. **If still seeing white backgrounds:**
   - Follow troubleshooting steps (section above)
   - Consider switching `transparent` to `var(--bg-body)` (explicit dark color)
   - Add specific selectors for missed elements

---

## Summary

### Problem
Container and card backgrounds (from `st.container()`, `st.columns()`, etc.) display white/light backgrounds in dark mode despite comprehensive dark mode CSS.

### Root Cause
Streamlit's container wrapper elements use runtime-generated `data-testid` attributes (`stVerticalBlock`, `stHorizontalBlock`, `column`) that aren't targeted by dark mode CSS selectors.

### Solution
Add CSS selectors targeting all Streamlit container types with transparent (or explicit dark) backgrounds in dark mode.

### Result
- ✅ All containers have dark backgrounds in dark mode
- ✅ No white/light backgrounds anywhere in the admin interface
- ✅ Consistent dark mode experience across all pages
- ✅ Pure CSS solution - no Python code changes needed
- ✅ Future-proof with generic `div[data-testid^="st"]` catch-all

### Files Modified
- `/opt/tangerine/admin/styles/custom.css` - Add ~20 lines of container selectors after line 1022

**Total Changes:** 1 edit in 1 file
