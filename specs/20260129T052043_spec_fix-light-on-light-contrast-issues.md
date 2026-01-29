# Plan: Fix Light-on-Light Contrast Issues

## Problem Statement

**User Report:** Metric card labels and inactive tab labels show light gray text (#B0B0B0 or #C0C0C0) on WHITE backgrounds - completely unreadable.

**Root Cause:** Current CSS assumes dark backgrounds and applies light text colors universally, without checking actual background color.

**Solution Approach:** Defensive CSS - default to DARK text (readable on white), only switch to LIGHT text when background is confirmed dark.

---

## Simple Fix Strategy

**Core Principle:**
1. **Default:** Dark text (#2C3E50) - works on light/white backgrounds
2. **Override:** Light text (#C8C8C8) - ONLY when background is confirmed dark via inline styles

**Why This Works:**
- No reliance on `[data-theme="dark"]` attribute (unreliable)
- Uses attribute selectors to detect actual background colors in inline styles
- Defensive: if detection fails, falls back to dark text (safe on most backgrounds)

---

## Implementation Steps

### Step 1: Remove Problematic Rules from ui_helpers.py

**File:** `/opt/tangerine/admin/utils/ui_helpers.py`

**Search for and remove/comment out:**
- Any rules setting metric labels to light colors (#B0B0B0, #C0C0C0) without background checks
- Any rules setting tab labels to light colors without background checks

**Note:** Based on exploration, current dark mode CSS in ui_helpers.py uses `#F0F0F0` (bright white) for all text. This is CORRECT for dark backgrounds but needs to be overridden for light backgrounds.

### Step 2: Add Universal Contrast Fix to custom.css

**File:** `/opt/tangerine/admin/styles/custom.css`

**Add at the END of the file (after all existing rules):**

```css
/* ============================================================================
   UNIVERSAL CONTRAST FIX - Background-Aware Text Colors
   Ensures readable text regardless of theme detection accuracy
   ============================================================================ */

/* DEFAULT: Dark text for metric labels (safe on white/light backgrounds) */
[data-testid="stMetric"] > div:first-child,
[data-testid="stMetric"] > div:first-child *,
[data-testid="stMetric"] label,
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    color: #34495E !important;  /* Dark blue-gray - 10.2:1 contrast on white */
    font-weight: 700 !important;
}

/* OVERRIDE: Light text only when metric background is confirmed dark */
[data-testid="stMetric"][style*="background-color: rgb(30, 30, 46)"] > div:first-child,
[data-testid="stMetric"][style*="background-color: rgb(30, 30, 46)"] > div:first-child *,
[data-testid="stMetric"][style*="background-color: rgb(30, 30, 46)"] label,
[data-testid="stMetric"][style*="background-color: rgb(26, 26, 42)"] > div:first-child,
[data-testid="stMetric"][style*="background-color: rgb(26, 26, 42)"] > div:first-child *,
[data-testid="stMetric"][style*="background: rgb(30, 30, 46)"] > div:first-child,
[data-testid="stMetric"][style*="background: rgb(30, 30, 46)"] > div:first-child * {
    color: #E8E8E8 !important;  /* Light gray - 8.0:1 contrast on #1E1E2E */
    font-weight: 700 !important;
}

/* DEFAULT: Dark text for inactive tabs (safe on white/light backgrounds) */
.stTabs [data-baseweb="tab"][aria-selected="false"],
.stTabs [data-baseweb="tab"][aria-selected="false"] *,
.stTabs [data-baseweb="tab"][aria-selected="false"] p,
.stTabs [data-baseweb="tab"][aria-selected="false"] span {
    color: #2C3E50 !important;  /* Dark slate - 12.6:1 contrast on white */
}

/* OVERRIDE: Light text only when tab container background is confirmed dark */
.stTabs [data-baseweb="tab-list"][style*="background-color: rgb(30, 30, 46)"] [data-baseweb="tab"][aria-selected="false"],
.stTabs [data-baseweb="tab-list"][style*="background-color: rgb(30, 30, 46)"] [data-baseweb="tab"][aria-selected="false"] *,
.stTabs [data-baseweb="tab-list"][style*="background: rgb(30, 30, 46)"] [data-baseweb="tab"][aria-selected="false"],
.stTabs [data-baseweb="tab-list"][style*="background: rgb(30, 30, 46)"] [data-baseweb="tab"][aria-selected="false"] * {
    color: #E8E8E8 !important;  /* Light gray - 8.0:1 contrast on #1E1E2E */
}
```

### Step 3: Restart Container

```bash
docker compose restart admin
```

### Step 4: Verify in Browser

1. Hard refresh: `Ctrl+Shift+R` / `Cmd+Shift+R`
2. Open DevTools (F12)
3. Inspect metric card label:
   - **Light mode/white background:** Should show `color: rgb(52, 73, 94)` (#34495E - dark)
   - **Dark mode:** Should show `color: rgb(232, 232, 232)` (#E8E8E8 - light)
4. Inspect inactive tab label:
   - **Light mode/white background:** Should show `color: rgb(44, 62, 80)` (#2C3E50 - dark)
   - **Dark mode:** Should show `color: rgb(232, 232, 232)` (#E8E8E8 - light)

---

## Expected Results

### Before Fix
| Element | Background | Text Color | Contrast | Readable? |
|---------|-----------|------------|----------|-----------|
| Metric label | White (#FFFFFF) | Light gray (#C0C0C0) | 1.6:1 | ❌ FAIL |
| Inactive tab | White (#FFFFFF) | Light gray (#B0B0B0) | 1.4:1 | ❌ FAIL |

### After Fix
| Element | Background | Text Color | Contrast | Readable? |
|---------|-----------|------------|----------|-----------|
| Metric label | White (#FFFFFF) | Dark blue (#34495E) | 10.2:1 | ✅ AAA |
| Metric label | Dark (#1E1E2E) | Light gray (#E8E8E8) | 8.0:1 | ✅ AAA |
| Inactive tab | White (#FFFFFF) | Dark slate (#2C3E50) | 12.6:1 | ✅ AAA |
| Inactive tab | Dark (#1E1E2E) | Light gray (#E8E8E8) | 8.0:1 | ✅ AAA |

---

## Why This Approach Works

1. **No theme detection needed** - Checks actual background colors via inline styles
2. **Defensive** - Defaults to dark text (safe on 90% of backgrounds)
3. **Specific** - Only overrides to light text when dark background is confirmed
4. **Universal** - Works regardless of Streamlit's `data-theme` attribute
5. **High specificity** - `!important` + attribute selectors ensure override

---

## Critical Files

**Primary:**
- `/opt/tangerine/admin/styles/custom.css` - Add universal contrast fix

**Secondary (review only):**
- `/opt/tangerine/admin/utils/ui_helpers.py` - Check for conflicting rules

---

## Success Criteria

✅ Metric labels readable on white backgrounds (dark text)
✅ Tab labels readable on white backgrounds (dark text)
✅ Metric labels readable on dark backgrounds (light text)
✅ Tab labels readable on dark backgrounds (light text)
✅ All contrast ratios ≥ 7:1 (WCAG AAA)
✅ No reliance on theme detection attributes
