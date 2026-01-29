# Plan: Fix Dark Mode Tab Text Contrast

## Problem Statement

Tab text elements like `<p>➕ Create New</p>` in dark mode have insufficient contrast and are hard to read. Despite CSS rules being in place with proper colors (`#C8C8C8` for 6.5:1 contrast ratio), the styling is not being applied.

**User observation**: "it looks the same" after adding CSS rules and restarting the container.

## Root Cause Analysis

### Current Implementation Issues

1. **JavaScript Approach (Lines 79-118 in ui_helpers.py)**
   - JavaScript was added to set `data-theme` attribute on DOM elements
   - This creates a parallel theming system alongside the inline CSS approach
   - **Problem**: Race conditions between JavaScript execution and Streamlit rendering
   - **Problem**: The `data-theme` attribute approach requires matching CSS selectors with `[data-theme="dark"]` prefix, but the inline CSS in `_apply_theme_css()` doesn't use this prefix

2. **Dual CSS Systems**
   - **File-based CSS** (`admin/styles/custom.css`): Uses `[data-theme="dark"]` selectors (lines 974-1500)
   - **Inline CSS** (`_apply_theme_css()` function): Uses direct selectors like `.stTabs [data-baseweb="tab"]` without `[data-theme]` prefix (lines 291-316)
   - **Conflict**: These two systems don't align, causing styling inconsistency

3. **Streamlit Emotion CSS Specificity**
   - Streamlit uses Emotion CSS which generates high-specificity class names
   - Tab text might have inline styles or dynamic classes that override the custom CSS
   - Even with `!important`, the selectors might not match the actual DOM structure

### Why the Inline CSS Isn't Working

The `_apply_theme_css()` function (lines 176-473 in ui_helpers.py) injects this CSS:

```css
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #C8C8C8 !important;
}
```

**Potential reasons this fails:**
1. **Selector mismatch**: The actual DOM structure might be `.stTabs > div > div > [data-baseweb="tab"] > div > p`, requiring more specific selectors
2. **Emotion CSS class names**: Streamlit might wrap tab text in elements with dynamically generated class names like `.st-emotion-cache-xxxxx`
3. **Inline styles**: Streamlit might apply `style="color: rgb(...);"` directly on the `<p>` or `<span>` tags, which always wins over CSS selectors
4. **CSS injection order**: The inline CSS is injected after the file-based CSS, but Streamlit might re-render and lose the injected styles

## Recommended Solution

### Step 1: Remove JavaScript (Lines 79-118)

**File**: `admin/utils/ui_helpers.py`

Remove the entire JavaScript block that sets `data-theme` attributes:
- Lines 79-118: Delete the `st.markdown()` call with JavaScript

**Reason**: This creates conflicts and doesn't actually help since the inline CSS doesn't use `[data-theme]` selectors.

### Step 2: Use Maximum Specificity CSS Selectors

**File**: `admin/utils/ui_helpers.py` → `_apply_theme_css()` function

**Current tab CSS (lines 291-316):**
```css
.stTabs [data-baseweb="tab"] {
    color: #C8C8C8 !important;
}
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #C8C8C8 !important;
}
```

**Replace with ultra-specific selectors:**
```css
/* Tabs - maximum specificity to override Streamlit Emotion CSS */
.stTabs [data-baseweb="tab-list"] {
    background-color: #1E1E2E !important;
    gap: 8px;
}

/* Target ALL possible text elements in tabs with maximum specificity */
.stTabs [data-baseweb="tab"],
.stTabs [data-baseweb="tab"] > div,
.stTabs [data-baseweb="tab"] > div > div,
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"] div p,
.stTabs [data-baseweb="tab"] div span,
div.stTabs [data-baseweb="tab"],
div.stTabs [data-baseweb="tab"] p,
div.stTabs [data-baseweb="tab"] span {
    color: #C8C8C8 !important;
    background-color: transparent !important;
}

/* Active tab */
.stTabs [aria-selected="true"],
.stTabs [aria-selected="true"] > div,
.stTabs [aria-selected="true"] > div > div {
    background-color: #FFA05C !important;
    color: #121212 !important;
}

/* Active tab text elements */
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span,
.stTabs [aria-selected="true"] div p,
.stTabs [aria-selected="true"] div span,
div.stTabs [aria-selected="true"] p,
div.stTabs [aria-selected="true"] span {
    color: #121212 !important;
}

/* Tab hover state */
.stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
    background-color: #2D2A3A !important;
}
```

### Step 3: Add Universal Text Color Fallback

**File**: `admin/utils/ui_helpers.py` → `_apply_theme_css()` function

Add after line 267 (general text styling):

```css
/* Universal dark mode text fallback - catch any missed elements */
.stApp p,
.stApp span,
.stApp div,
.stApp label,
section p,
section span,
section div {
    color: #E8E8E8 !important;
}

/* But allow specific components to override */
[data-testid="stMetric"] span:not([data-testid="stMetricValue"]) {
    color: #C8C8C8 !important;
}
```

### Step 4: Remove Redundant CSS from custom.css

**File**: `admin/styles/custom.css`

The `[data-theme="dark"]` rules (lines 974-1500) are not being used because `data-theme` attribute is never reliably set. These can be:
1. **Option A**: Kept as fallback (no harm)
2. **Option B**: Removed to reduce file size (recommended)

**If removing**: Delete lines 974-1500 (entire `[data-theme="dark"]` section)

**Reasoning**: The inline CSS from `_apply_theme_css()` is the source of truth for dark mode styling, not the file-based CSS.

### Step 5: Debug Verification

Add console logging to verify CSS is being injected:

**File**: `admin/utils/ui_helpers.py` → `_apply_theme_css()` function

Add at line 178 (start of dark mode block):

```python
if is_dark_mode():
    print(f"[Dark Mode CSS] Applying dark mode styles")  # Debug log
    st.markdown("""
    <script>
    console.log('[Dark Mode] Theme CSS injected');
    console.log('[Dark Mode] Current theme:', '{theme}');
    </script>
    """.format(theme='dark'), unsafe_allow_html=True)
    st.markdown("""
```

## Implementation Steps

1. **Remove JavaScript** (Lines 79-118 in `admin/utils/ui_helpers.py`)
2. **Update tab CSS selectors** (Lines 291-316 in `admin/utils/ui_helpers.py` → `_apply_theme_css()`)
3. **Add universal text fallback** (After line 267 in `admin/utils/ui_helpers.py`)
4. **(Optional) Remove `[data-theme]` CSS** (Lines 974-1500 in `admin/styles/custom.css`)
5. **Add debug logging** (Line 178 in `admin/utils/ui_helpers.py`)
6. **Restart container**: `docker compose restart admin`
7. **Test**: Toggle dark mode and inspect browser DevTools

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `admin/utils/ui_helpers.py` | 79-118 | **DELETE**: JavaScript block |
| `admin/utils/ui_helpers.py` | 291-316 | **REPLACE**: Tab CSS with ultra-specific selectors |
| `admin/utils/ui_helpers.py` | 267 | **ADD**: Universal text color fallback |
| `admin/utils/ui_helpers.py` | 178 | **ADD**: Debug logging |
| `admin/styles/custom.css` | 974-1500 | **OPTIONAL DELETE**: `[data-theme]` CSS rules |

## Verification Steps

### Browser DevTools Inspection

1. Toggle dark mode ON
2. Open browser DevTools (F12) → Elements tab
3. Inspect a tab element (e.g., "➕ Create New")
4. Check **Computed** styles:
   - Should show `color: rgb(200, 200, 200)` (which is `#C8C8C8`)
5. Check **Styles** tab:
   - Should see inline `<style>` block from `_apply_theme_css()`
   - Should see the tab color rule with `!important`
   - Verify no strikethrough (which means it's not overridden)

### Console Logs

Check browser console for:
- `[Dark Mode] Theme CSS injected`
- `[Dark Mode] Current theme: dark`

### Visual Test

1. Navigate to any page with tabs (e.g., `admin/pages/imports.py`)
2. Tabs should show:
   - **Inactive tabs**: Light gray text `#C8C8C8` on dark background
   - **Active tab**: Dark text `#121212` on tangerine background `#FFA05C`
   - **High contrast**: Text should be clearly readable

## Alternative Approach (If Above Fails)

If Streamlit's Emotion CSS still overrides, use the "nuclear option":

### Nuclear Option: CSS `all: unset` + Re-style

```css
.stTabs [data-baseweb="tab"] * {
    all: unset !important;
    display: inline !important;
    color: #C8C8C8 !important;
}
```

This resets ALL inherited styles and forces the color. Use only if the refined selectors don't work.

## Success Criteria

✅ Tab text "➕ Create New" and similar elements are clearly visible in dark mode
✅ Contrast ratio ≥ 6.5:1 (WCAG AA compliant)
✅ No JavaScript conflicts or race conditions
✅ Dark mode toggle works immediately without page reload
✅ All pages with tabs show correct styling

## Risk Assessment

**Low risk**: Changes only affect dark mode CSS, not functionality
**Rollback**: If issues occur, revert `admin/utils/ui_helpers.py` changes and restart container
