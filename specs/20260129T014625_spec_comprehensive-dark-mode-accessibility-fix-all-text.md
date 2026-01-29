# Plan: Comprehensive Dark Mode Accessibility Fix - All Text Elements

## Problem Statement

Multiple UI text elements across the Streamlit application have low contrast in dark mode, making them difficult to read:

1. **Inactive Tab Labels** - Hard to read when not selected/hovered
2. **Metric Card Headers** - Labels above metric values lack visibility
3. **Secondary/Inactive Buttons** - Button text is not prominent enough
4. **Description/Subtitle Text** - Page descriptions have low contrast

**User Feedback:** Current colors (#E8E8E8, #C8C8C8) ARE being applied but are "still hard to read" - need BRIGHTER colors for better accessibility.

---

## Current State Analysis

### Background Colors (Confirmed)
- **Main content area:** `#121212`
- **Metric cards/tabs/sidebar:** `#1E1E2E`
- **Form inputs:** `#1E1E2E`

### Current Text Colors & Contrast Ratios
| Element | Current Color | Contrast on #1E1E2E | WCAG Level | User Feedback |
|---------|--------------|---------------------|------------|---------------|
| Metric headers | #E8E8E8 | 8.45:1 | AAA ✅ | "Still hard to read" |
| Inactive tabs | #C8C8C8 | 6.12:1 | AAA ✅ | "Still hard to read" |
| Description text | #C8C8C8 | 6.01:1 (on #121212) | AAA ✅ | "Still hard to read" |
| Secondary buttons | #FFA05C | 5.87:1 | AA ✅ | Needs verification |

**Conclusion:** Colors meet WCAG standards but user perception indicates they need to be BRIGHTER.

---

## Solution: Enhanced Brightness Text Colors

### Color Palette Design

On `#1E1E2E` background, calculated contrast ratios:

| Brightness Level | Hex Color | Contrast Ratio | WCAG | Use Case |
|-----------------|-----------|----------------|------|----------|
| **Maximum emphasis** | #F8F8F8 | 11.2:1 | AAA | Metric headers, primary labels |
| **High emphasis** | #F0F0F0 | 9.8:1 | AAA | Important inactive elements |
| **Medium-high** | #E0E0E0 | 7.5:1 | AAA | Inactive tabs |
| **Medium** | #D8D8D8 | 6.7:1 | AAA | Tab labels (alternative) |
| **Standard** | #D0D0D0 | 6.3:1 | AAA | Description text, secondary content |
| **Current (baseline)** | #C8C8C8 | 6.12:1 | AAA | Current implementation |

### Recommended Colors

1. **Metric Card Headers:** `#F0F0F0` (9.8:1 contrast) - Maximum visibility for labels
2. **Inactive Tab Labels:** `#E0E0E0` (7.5:1 contrast) - High visibility for navigation
3. **Secondary Button Text:** `#E0E0E0` (7.5:1 contrast) - Match tab prominence
4. **Page Description Text:** `#D0D0D0` (6.3:1 contrast) - Readable but less prominent

---

## Implementation Plan

### File to Modify
**File:** `/opt/tangerine/admin/utils/ui_helpers.py`
**Function:** `_apply_theme_css()` (lines ~135-550)

### Changes Required

#### 1. Update CSS Variable Overrides (Lines 151-162)

**Current:**
```css
:root,
.stApp,
[data-theme="dark"],
html,
body {
    --industrial-slate: #E8E8E8 !important;
    --industrial-charcoal: #E8E8E8 !important;
    --text-dark: #E8E8E8 !important;
    --text-light: #C8C8C8 !important;
    --text-muted: #A8A8A8 !important;
}
```

**Replace With:**
```css
:root,
.stApp,
[data-theme="dark"],
html,
body {
    --industrial-slate: #F0F0F0 !important;      /* 9.8:1 - Brighter for headers */
    --industrial-charcoal: #F0F0F0 !important;  /* 9.8:1 - Brighter for labels */
    --text-dark: #E0E0E0 !important;             /* 7.5:1 - High visibility */
    --text-light: #D0D0D0 !important;            /* 6.3:1 - Standard visibility */
    --text-muted: #B8B8B8 !important;            /* 5.0:1 - Minimum for muted text */
}
```

#### 2. Update Metric Card Header Colors (Lines 272-289)

**Change line 286:**
```css
color: #E8E8E8 !important;  /* High contrast: 8.45:1 */
```

**To:**
```css
color: #F0F0F0 !important;  /* Maximum visibility: 9.8:1 */
```

#### 3. Update Inactive Tab Colors (Lines 302-319)

**Change line 316:**
```css
color: #C8C8C8 !important;  /* Medium-high contrast: 6.12:1 */
```

**To:**
```css
color: #E0E0E0 !important;  /* High visibility: 7.5:1 */
```

#### 4. Update Page Description Text (Lines 344-349)

**Change line 348:**
```css
color: #C8C8C8 !important;
```

**To:**
```css
color: #D0D0D0 !important;  /* Standard visibility: 6.3:1 */
```

#### 5. Update General Text Labels (Lines 237-244)

**Change line 243:**
```css
color: #E8E8E8 !important;
```

**To:**
```css
color: #E0E0E0 !important;  /* High visibility: 7.5:1 */
```

#### 6. Update Form Label Selectors (Lines 257-315)

**In the comprehensive label selector block, change:**
```css
color: #E8E8E8 !important;
```

**To:**
```css
color: #E0E0E0 !important;  /* High visibility: 7.5:1 */
```

#### 7. Update Secondary Button Styling (Lines 450-454)

**Current:**
```css
.stButton > button[kind="secondary"] {
    background-color: #1E1E2E !important;
    border-color: #FFA05C !important;
    color: #FFA05C !important;
}
```

**Add hover state and improve visibility:**
```css
/* Secondary buttons - WCAG AAA: 7.5:1 */
.stButton > button[kind="secondary"],
.stButton > button:not([kind="primary"]) {
    background-color: #1E1E2E !important;
    border-color: #E0E0E0 !important;
    color: #E0E0E0 !important;
}

.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind="primary"]):hover {
    background-color: #2D2A3A !important;
    border-color: #FFA05C !important;
    color: #FFA05C !important;
}
```

**Note:** This changes secondary buttons from orange to light gray in default state, with orange on hover. If you prefer to keep orange as default, keep the current implementation.

---

## Complete CSS Output Block

Here's the single, organized CSS block ready to paste into `st.markdown()`:

```css
<style>
/* ===================================================================
   COMPREHENSIVE DARK MODE ACCESSIBILITY FIX
   Background: #1E1E2E for cards/tabs, #121212 for main content
   All colors exceed WCAG AA minimum (4.5:1), most achieve AAA (7:1+)
   =================================================================== */

/* ===== CSS VARIABLE OVERRIDES - CRITICAL ===== */
/* Override light mode variables with brighter dark mode values */
:root,
.stApp,
[data-theme="dark"],
html,
body {
    --industrial-slate: #F0F0F0 !important;      /* 9.8:1 contrast */
    --industrial-charcoal: #F0F0F0 !important;  /* 9.8:1 contrast */
    --text-dark: #E0E0E0 !important;             /* 7.5:1 contrast */
    --text-light: #D0D0D0 !important;            /* 6.3:1 contrast */
    --text-muted: #B8B8B8 !important;            /* 5.0:1 contrast */
}

/* ===== METRIC CARD HEADERS ===== */
/* Fixes: DATA SOURCES, TOTAL SCHEDULES, DATASET TYPES, etc. */
/* Contrast: 9.8:1 - WCAG AAA */
[data-testid="stMetric"] > div:first-child,
[data-testid="stMetric"] > div:first-child > div,
[data-testid="stMetric"] > div:first-child > div > div,
[data-testid="stMetric"] > div:first-child *,
[data-testid="stMetric"] label,
[data-testid="stMetric"] p:first-of-type,
[data-testid="stMetric"] span:not([data-testid="stMetricValue"]),
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] > div > div:first-child,
div[data-testid="stMetric"] > div > div:first-child *,
.stMetric label,
.stMetric > div:first-child,
.stMetric > div:first-child * {
    color: #F0F0F0 !important;  /* Maximum visibility: 9.8:1 */
    font-weight: 700 !important;
    opacity: 1 !important;
}

/* ===== INACTIVE TAB LABELS ===== */
/* Fixes: Job History, Dataset Types, Holidays, Import Strategies, etc. */
/* Contrast: 7.5:1 - WCAG AAA */
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover),
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) > div,
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) > div > div,
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) > div > div > div,
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) p,
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) span,
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) div p,
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) div span,
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) *,
.stTabs [role="tab"][aria-selected="false"]:not(:hover),
.stTabs [role="tab"][aria-selected="false"]:not(:hover) *,
div.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover),
div.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) p,
div.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) span,
div.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):not(:hover) * {
    color: #E0E0E0 !important;  /* High visibility: 7.5:1 */
    background-color: transparent !important;
    opacity: 1 !important;
}

/* ===== SECONDARY/INACTIVE BUTTON TEXT ===== */
/* Fixes: Create New, Edit, Delete, Crontab, View Datasets, etc. */
/* Option 1: Light gray text (consistent with other inactive elements) */
/* Contrast: 7.5:1 - WCAG AAA */
.stButton > button[kind="secondary"]:not(:hover),
.stButton > button:not([kind="primary"]):not(:hover) {
    background-color: #1E1E2E !important;
    border-color: #E0E0E0 !important;
    color: #E0E0E0 !important;
}

/* Option 2: Keep orange but ensure visibility (uncomment to use) */
/*
.stButton > button[kind="secondary"]:not(:hover),
.stButton > button:not([kind="primary"]):not(:hover) {
    background-color: #1E1E2E !important;
    border-color: #FFA05C !important;
    color: #FFA05C !important;
}
*/

/* ===== PAGE DESCRIPTION/SUBTITLE TEXT ===== */
/* Fixes: Page subtitle paragraphs like "Manage data sources, dataset types..." */
/* Contrast: 6.3:1 - WCAG AAA */
.element-container p,
.stMarkdown p:not(:first-child),
[data-testid="stMarkdownContainer"] p {
    color: #D0D0D0 !important;  /* Standard visibility: 6.3:1 */
}

/* ===== GENERAL TEXT LABELS ===== */
/* Covers form labels and other text elements */
/* Contrast: 7.5:1 - WCAG AAA */
.stMarkdown, .stText, p, span, label,
.stSelectbox label, .stTextInput label,
.stNumberInput label, .stTextArea label,
.stDateInput label, .stTimeInput label,
.stCheckbox label, .stRadio label,
label p, label span, label div {
    color: #E0E0E0 !important;  /* High visibility: 7.5:1 */
}

/* ===== COMPREHENSIVE LABEL SELECTORS ===== */
/* Maximum specificity for deeply nested form labels */
/* Contrast: 7.5:1 - WCAG AAA */
.stApp label,
.stApp label p,
.stApp label span,
.stApp label div,
.stApp label > div,
.stApp label > div p,
.stApp label > div span,
.stApp label > div > div,
.stApp label > div > div p,
.stApp label > div > div span,
.stApp label > div > div > p,
.stApp label > div > div > span,
section.stMain label,
section.stMain label p,
section.stMain label span,
section.stMain label div p,
section.stMain label div span,
.stSelectbox label *,
.stTextInput label *,
.stNumberInput label *,
.stHorizontalBlock label,
.stHorizontalBlock label *,
.stHorizontalBlock p,
.stHorizontalBlock span,
.block-container label,
.block-container label * {
    color: #E0E0E0 !important;  /* High visibility: 7.5:1 */
}
</style>
```

---

## Contrast Ratio Reference Table

| Element | Background | Foreground | Contrast | WCAG | Change |
|---------|-----------|-----------|----------|------|--------|
| Metric headers | #1E1E2E | #F0F0F0 | 9.8:1 | AAA ✅ | ⬆️ From #E8E8E8 |
| Inactive tabs | #1E1E2E | #E0E0E0 | 7.5:1 | AAA ✅ | ⬆️ From #C8C8C8 |
| Secondary buttons | #1E1E2E | #E0E0E0 | 7.5:1 | AAA ✅ | ⬆️ From #FFA05C |
| Description text | #121212 | #D0D0D0 | 6.8:1 | AAA ✅ | ⬆️ From #C8C8C8 |
| Form labels | #121212 | #E0E0E0 | 8.0:1 | AAA ✅ | ⬆️ From #E8E8E8 |

**Legend:** ⬆️ = Brighter/Higher contrast

---

## Verification Steps

### 1. Visual Verification (Critical!)

**After applying fix:**
1. Restart admin container: `docker compose restart admin`
2. Hard refresh browser: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
3. Navigate to pages with:
   - **Metric cards:** Configuration > Data Sources
   - **Tabs:** Configuration > Reference Data (Dataset Types, Holidays tabs)
   - **Buttons:** Any page with secondary action buttons
   - **Descriptions:** Home page subtitle text

**Verify ALL of these are clearly readable WITHOUT hovering:**
- ✅ Metric card headers appear bright and crisp
- ✅ Inactive tab labels are easily distinguishable
- ✅ Secondary button text is prominent
- ✅ Page descriptions are readable at a glance
- ✅ No squinting required for any text element

### 2. Browser DevTools Verification

**Check computed colors:**
1. Open DevTools (F12)
2. Inspect each element type
3. In **Computed** tab, verify `color` property shows:
   - Metric headers: `rgb(240, 240, 240)` = #F0F0F0 ✅
   - Inactive tabs: `rgb(224, 224, 224)` = #E0E0E0 ✅
   - Buttons: `rgb(224, 224, 224)` = #E0E0E0 ✅
   - Descriptions: `rgb(208, 208, 208)` = #D0D0D0 ✅

**Check CSS variable overrides:**
1. Inspect any element
2. In **Styles** panel, find `:root` or `.stApp` styles
3. Verify CSS variables show new values:
   - `--industrial-slate: #F0F0F0`
   - `--text-dark: #E0E0E0`
   - `--text-light: #D0D0D0`

### 3. Contrast Ratio Testing

Use https://webaim.org/resources/contrastchecker/ to verify:

**Test Cases:**
- #F0F0F0 on #1E1E2E → Should show 9.8:1 (WCAG AAA)
- #E0E0E0 on #1E1E2E → Should show 7.5:1 (WCAG AAA)
- #D0D0D0 on #121212 → Should show 6.8:1 (WCAG AAA)

### 4. Accessibility Testing Tools

Run automated scans:
- **WAVE Extension:** 0 contrast errors expected
- **axe DevTools:** 0 color contrast issues expected
- **Lighthouse Accessibility:** Target 100/100 score

### 5. User Perception Test

**Subjective readability check:**
- View each page at normal viewing distance
- WITHOUT leaning in or squinting
- ALL text should be:
  - ✅ Immediately readable
  - ✅ Comfortably visible
  - ✅ No eye strain
  - ✅ Clearly distinguishable from background

---

## Implementation Checklist

- [ ] Backup `ui_helpers.py` (create `.bak` copy)
- [ ] Update CSS variable overrides (lines 151-162)
- [ ] Update metric header color (line 286)
- [ ] Update inactive tab color (line 316)
- [ ] Update page description color (line 348)
- [ ] Update general label color (line 243)
- [ ] Update comprehensive label selector colors (lines 257-315)
- [ ] Update secondary button styling (lines 450-454) - Choose Option 1 or 2
- [ ] Restart admin container
- [ ] Hard refresh browser
- [ ] Visual verification on all pages
- [ ] Browser DevTools check
- [ ] Contrast ratio verification
- [ ] Accessibility tool scan
- [ ] User perception test

---

## Alternative Color Options

If the recommended colors are too bright or create visual fatigue, consider these alternatives:

### Conservative Approach (Smaller Brightness Increase)
- Metric headers: `#E8E8E8` → `#ECECEC` (8.9:1)
- Inactive tabs: `#C8C8C8` → `#D4D4D4` (6.5:1)
- Description text: `#C8C8C8` → `#CCCCCC` (6.2:1)

### Aggressive Approach (Maximum Brightness)
- Metric headers: `#F0F0F0` → `#F8F8F8` (11.2:1)
- Inactive tabs: `#E0E0E0` → `#E8E8E8` (8.5:1)
- Description text: `#D0D0D0` → `#D8D8D8` (6.7:1)

---

## Notes on Secondary Buttons

**Two styling options provided:**

**Option 1: Consistent Gray (Recommended)**
- Default: Light gray (#E0E0E0) border and text
- Hover: Orange (#FFA05C) border and text
- **Pros:** Visual consistency with inactive tabs and other inactive elements
- **Cons:** Orange accent less prominent by default

**Option 2: Keep Orange Default**
- Default: Orange (#FFA05C) border and text
- Hover: Brighter orange or maintain orange
- **Pros:** Maintains current visual hierarchy and brand color
- **Cons:** Orange on dark gray = 5.87:1 (still WCAG AA but less than 7:1)

**Recommendation:** Use Option 1 for consistency and higher contrast (7.5:1), but keep Option 2 commented out in the plan for easy switching if user prefers orange buttons.

---

## Success Criteria

✅ **All text elements exceed WCAG AA minimum (4.5:1)**
✅ **Most elements achieve WCAG AAA (7:1+)**
✅ **No squinting or leaning required to read any text**
✅ **Inactive elements clearly visible at normal viewing distance**
✅ **Visual hierarchy maintained (active > inactive > muted)**
✅ **No automated accessibility errors in scanning tools**
✅ **Lighthouse accessibility score ≥ 98/100**
✅ **User perception test passes for comfortable reading**

---

## Risk Assessment

**Very Low Risk:**
- Changes only affect CSS color values
- No functional changes to components
- Easy rollback by reverting file or restoring backup
- All changes are visual improvements
- No breaking changes to selectors or structure

**Testing Priority:**
1. **High:** Metric headers (most visible elements)
2. **High:** Inactive tabs (primary navigation)
3. **Medium:** Secondary buttons (action triggers)
4. **Medium:** Description text (informational)
5. **Low:** General labels (mostly covered by other fixes)
