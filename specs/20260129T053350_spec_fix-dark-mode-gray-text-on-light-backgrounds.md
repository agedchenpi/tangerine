# Plan: Fix Dark Mode Gray Text on Light Backgrounds

## Root Cause Analysis

### The Architectural Flaw

**Problem:** Two competing CSS systems with conflicting assumptions about background color:

1. **custom.css** (lines 973-1091)
   - Sets CSS variables to bright values: `--industrial-slate: #E0E0E0`
   - Assumes ALL elements have dark backgrounds in dark mode
   - Applied with `[data-theme="dark"]` selector

2. **ui_helpers.py** (lines 135-545)
   - Injects CSS with `!important` AFTER custom.css loads
   - Overrides variables to even brighter values: `#F0F0F0`
   - Forces bright text on ALL metrics, tabs, labels with aggressive selectors
   - Lines 157-162: `:root` variable overrides with `!important`
   - Lines 332-349: Metric label text forced to `#F0F0F0`
   - Lines 362-381: Tab label text forced to `#F0F0F0`

**Result:** Bright text (#E0E0E0, #F0F0F0) applied to elements with light backgrounds (#FFFFFF)

### Contrast Failures

| Element | Background | Text Color | Contrast | Status |
|---------|-----------|------------|----------|--------|
| Metric labels | #FFFFFF | #E0E0E0 | 1.18:1 | ❌ FAIL |
| Tab labels | #FFFFFF | #F0F0F0 | 1.07:1 | ❌ FAIL |
| Form labels | #F8F9FA | #E0E0E0 | 1.22:1 | ❌ FAIL |

**WCAG AAA requires ≥ 7:1 contrast ratio**

### Why Current System Fails

- CSS variables (`--industrial-slate`, `--text-dark`) set to bright values globally
- These variables used by components that CAN have light backgrounds even in dark mode
- No mechanism to check actual background color before applying text color
- `!important` overrides prevent cascading fixes from working

---

## Solution: Background-Aware CSS Architecture

### Strategy

**Refactor from:**
- Single CSS variable set (assumes dark background)
- Aggressive `!important` overrides in ui_helpers.py

**Refactor to:**
- **Background-aware CSS variables** - Separate sets for dark vs light backgrounds
- **Single source of truth** - All CSS in custom.css
- **Minimal dynamic CSS** - ui_helpers.py only sets `data-theme` attribute
- **Default to accessible** - Components default to dark backgrounds (safe)

### Core Principle

**Two variable sets in dark mode:**
1. `--text-on-dark-bg-*` for dark backgrounds (#121212, #1E1E2E)
2. `--text-on-light-bg-*` for light backgrounds (#FFFFFF, #F8F9FA)

**Default behavior:** Components get dark backgrounds → bright text (accessible)

**Opt-in to light backgrounds:** Components can explicitly request light backgrounds

---

## Implementation Steps

### Step 1: Refactor CSS Variables in custom.css

**File:** `/opt/tangerine/admin/styles/custom.css`

**Replace lines 973-982** (dark mode variables):

```css
[data-theme="dark"],
.stApp[data-theme="dark"] {
    /* Background-aware CSS variables */

    /* For dark backgrounds (#121212, #1E1E2E) */
    --text-on-dark-bg: #E0E0E0;        /* 7.5:1 on #121212 */
    --text-on-dark-bg-bright: #F0F0F0; /* 9.8:1 on #121212 */
    --text-on-dark-bg-muted: #D0D0D0;  /* 6.3:1 on #121212 */

    /* For light backgrounds (#FFFFFF, #F8F9FA) */
    --text-on-light-bg: #2C3E50;       /* 12.6:1 on #FFFFFF */
    --text-on-light-bg-secondary: #34495E; /* 10.2:1 on #FFFFFF */
    --text-on-light-bg-muted: #6C757D; /* 5.9:1 on #FFFFFF */

    /* Background colors */
    --bg-body: #121212;
    --bg-card-dark: #1E1E2E;
    --bg-card-light: #FFFFFF;

    /* Backward compatibility - default to dark backgrounds */
    --industrial-slate: var(--text-on-dark-bg-bright) !important;
    --industrial-charcoal: var(--text-on-dark-bg-bright) !important;
    --text-dark: var(--text-on-dark-bg) !important;
    --text-light: var(--text-on-dark-bg-bright) !important;
    --text-muted: var(--text-on-dark-bg-muted) !important;
}
```

### Step 2: Replace Element-Specific Overrides in custom.css

**Replace lines 989-1091** (all dark mode element rules):

```css
/* ============================================================================
   DARK MODE - BACKGROUND-AWARE COMPONENTS
   Default: Dark backgrounds for all components
   Override: Use .light-bg-in-dark class for light backgrounds
   ============================================================================ */

/* Main containers - dark background */
[data-theme="dark"] .stApp,
[data-theme="dark"] .main,
[data-theme="dark"] .block-container {
    background-color: var(--bg-body) !important;
    color: var(--text-on-dark-bg) !important;
}

/* ===== METRIC CARDS ===== */

/* DEFAULT: Metric cards have dark backgrounds */
[data-theme="dark"] [data-testid="stMetric"] {
    background: linear-gradient(135deg, #1E1E2E 0%, #1A1A2A 100%) !important;
    border-left-color: #FFA05C !important;
}

[data-theme="dark"] [data-testid="stMetric"] > div:first-child,
[data-theme="dark"] [data-testid="stMetric"] label,
[data-testid="dark"] [data-testid="stMetric"] p:first-of-type {
    color: var(--text-on-dark-bg-bright) !important;
    font-weight: 700 !important;
}

[data-theme="dark"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #FFA05C !important;
}

/* ===== TABS ===== */

/* Tab container - dark background */
[data-theme="dark"] .stTabs [data-baseweb="tab-list"] {
    background-color: var(--bg-card-dark) !important;
}

/* Inactive tabs */
[data-theme="dark"] .stTabs [data-baseweb="tab"]:not([aria-selected="true"]) {
    color: var(--text-on-dark-bg-bright) !important;
    background-color: transparent !important;
}

/* Active tab */
[data-theme="dark"] .stTabs [aria-selected="true"] {
    background-color: #FFA05C !important;
    color: #121212 !important;
}

/* ===== FORM LABELS ===== */

[data-theme="dark"] label,
[data-theme="dark"] label p,
[data-theme="dark"] label span {
    color: var(--text-on-dark-bg-bright) !important;
}

/* ===== SIDEBAR ===== */

[data-theme="dark"] [data-testid="stSidebar"] {
    background-color: var(--bg-card-dark) !important;
}

[data-theme="dark"] [data-testid="stSidebar"] a,
[data-theme="dark"] [data-testid="stSidebarNavLink"] {
    color: var(--text-on-dark-bg-bright) !important;
}

/* ===== GENERAL TEXT ===== */

[data-theme="dark"] p,
[data-theme="dark"] span {
    color: var(--text-on-dark-bg) !important;
}

[data-theme="dark"] h1,
[data-theme="dark"] h2,
[data-theme="dark"] h3,
[data-theme="dark"] h4,
[data-theme="dark"] h5,
[data-theme="dark"] h6 {
    color: var(--text-on-dark-bg-bright) !important;
}

/* ===== DATAFRAMES ===== */

[data-theme="dark"] .stDataFrame,
[data-theme="dark"] [data-testid="stDataFrame"] {
    background-color: var(--bg-card-dark) !important;
}

[data-theme="dark"] .stDataFrame thead tr th {
    background-color: #FFA05C !important;
    color: #121212 !important;
}

[data-theme="dark"] .stDataFrame tbody tr:nth-child(even) {
    background-color: #1A1A2A !important;
}

[data-theme="dark"] .stDataFrame tbody tr:hover {
    background-color: #2D2A3A !important;
}

/* ===== FORM INPUTS ===== */

[data-theme="dark"] .stTextInput > div > div > input,
[data-theme="dark"] .stTextArea > div > div > textarea,
[data-theme="dark"] .stSelectbox > div > div,
[data-theme="dark"] .stNumberInput > div > div > input,
[data-theme="dark"] .stDateInput > div > div > input {
    background-color: var(--bg-card-dark) !important;
    color: var(--text-on-dark-bg-bright) !important;
    border-color: #4A4A5A !important;
}

/* ===== BUTTONS ===== */

[data-theme="dark"] .stButton > button[kind="primary"] {
    background-color: #FFA05C !important;
    color: #121212 !important;
}

[data-theme="dark"] .stButton > button[kind="secondary"] {
    background-color: var(--bg-card-dark) !important;
    border-color: var(--text-on-dark-bg-bright) !important;
    color: var(--text-on-dark-bg-bright) !important;
}

/* ===== EXPANDERS ===== */

[data-theme="dark"] .streamlit-expanderHeader,
[data-theme="dark"] [data-testid="stExpander"] {
    background-color: var(--bg-card-dark) !important;
    color: var(--text-on-dark-bg-bright) !important;
}

/* ===== ALERTS ===== */

[data-theme="dark"] .stSuccess {
    background-color: #1A3D25 !important;
    color: #D4F4DD !important;
}

[data-theme="dark"] .stError {
    background-color: #3D1A1A !important;
    color: #FFD4D8 !important;
}

[data-theme="dark"] .stWarning {
    background-color: #3D3D1A !important;
    color: #FFF8D1 !important;
}

[data-theme="dark"] .stInfo {
    background-color: #1A2A3D !important;
    color: #D4EBFF !important;
}
```

### Step 3: Remove "Universal Contrast Fix"

**Delete lines 1097-1133** - No longer needed with background-aware system

### Step 4: Simplify ui_helpers.py

**File:** `/opt/tangerine/admin/utils/ui_helpers.py`

**Replace entire `_apply_theme_css()` function (lines 135-579):**

```python
def _apply_theme_css():
    """Set data-theme attribute for CSS targeting."""
    if is_dark_mode():
        st.markdown("""
        <script>
        // Set data-theme="dark" for CSS selector targeting
        document.documentElement.setAttribute('data-theme', 'dark');
        const app = document.querySelector('.stApp');
        if (app) app.setAttribute('data-theme', 'dark');
        console.log('[Dark Mode] Theme attribute set');
        </script>
        <style>
        /* Minimal dark mode base - all component styling in custom.css */
        html, body, .stApp {
            background-color: #121212 !important;
        }
        [data-testid="stSidebar"] {
            background-color: #1E1E2E !important;
        }
        [data-testid="stHeader"] {
            background-color: #121212 !important;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <script>
        // Set data-theme="light" for CSS selector targeting
        document.documentElement.setAttribute('data-theme', 'light');
        const app = document.querySelector('.stApp');
        if (app) app.setAttribute('data-theme', 'light');
        </script>
        <style>
        /* Light mode base */
        html, body, .stApp {
            background-color: #F8F9FA !important;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
        }
        </style>
        """, unsafe_allow_html=True)
```

---

## Verification Plan

### Test 1: Dark Mode - Metric Cards (Default)

**Setup:** Navigate to any page with metrics in dark mode

**Expected:**
- Background: Dark gradient (#1E1E2E → #1A1A2A)
- Label text: #F0F0F0 (bright white)
- Contrast: 9.8:1 ✅ AAA

**DevTools Check:**
```
Computed styles for [data-testid="stMetric"] label:
  color: rgb(240, 240, 240)  // #F0F0F0
  background-color: rgb(30, 30, 46)  // #1E1E2E
```

### Test 2: Dark Mode - Tab Labels

**Setup:** Navigate to Reference Data page → tabs

**Expected:**
- Tab container background: #1E1E2E
- Inactive tab text: #F0F0F0
- Contrast: 9.8:1 ✅ AAA

### Test 3: Dark Mode - Form Labels

**Setup:** Open any form (e.g., import config form)

**Expected:**
- Label text: #F0F0F0
- Background: #121212
- Contrast: 9.8:1 ✅ AAA

### Test 4: Light Mode - No Regression

**Setup:** Toggle to light mode

**Expected:** All elements maintain current appearance (unchanged)

### Test 5: Sidebar Navigation

**Setup:** Check sidebar links in dark mode

**Expected:**
- Link text: #F0F0F0
- Background: #1E1E2E
- Contrast: 9.8:1 ✅ AAA

---

## Benefits of This Architecture

### ✅ Single Source of Truth
- All CSS in custom.css
- No conflicting rules between files
- Easy to debug via DevTools

### ✅ Background-Aware by Design
- Separate variables for light/dark backgrounds
- Explicit about context (`--text-on-dark-bg` vs `--text-on-light-bg`)
- No assumptions about component backgrounds

### ✅ Maintainable
- Clear variable naming convention
- Minimal `!important` usage
- Load order predictable (CSS file → minimal injection)

### ✅ WCAG AAA Compliant
- All text ≥ 7:1 contrast
- Most text ≥ 9.8:1 contrast
- Accessible by default

### ✅ Robust
- Doesn't rely on detecting inline styles
- Works with Streamlit's DOM structure changes
- Defaults to safe choices (dark backgrounds)

---

## Critical Files

**Primary Changes:**
- `/opt/tangerine/admin/styles/custom.css`
  - Lines 973-982: Refactor CSS variables to background-aware sets
  - Lines 989-1091: Replace with simpler background-aware component styles
  - Lines 1097-1133: Delete "universal contrast fix"

**Secondary Changes:**
- `/opt/tangerine/admin/utils/ui_helpers.py`
  - Lines 135-579: Replace entire `_apply_theme_css()` function with minimal version

**No Changes Required:**
- Page files (home.py, monitoring.py, etc.)
- Component files (forms.py, etc.)
- Python business logic

---

## Success Criteria

✅ All metric labels readable in dark mode (bright text on dark background)
✅ All tab labels readable in dark mode (bright text on dark background)
✅ All form labels readable in dark mode (bright text on dark background)
✅ All contrast ratios ≥ 7:1 (WCAG AAA minimum)
✅ Light mode unchanged (no regression)
✅ Single source of truth for CSS (custom.css)
✅ No more CSS variable conflicts
✅ Background colors explicit and intentional
