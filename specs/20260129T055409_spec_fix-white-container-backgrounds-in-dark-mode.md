# Plan: Fix White Container Backgrounds in Dark Mode

## Problem Summary

After implementing the initial dark mode fixes, several containers still have **white backgrounds with gray text** in dark mode, causing severe contrast violations.

**User Requirement:**
- White background → Black text (light mode or light containers)
- Dark background → White text (dark mode)

**Current Issue:**
- Some containers keep white backgrounds in dark mode
- Dark mode CSS applies gray/white text colors globally
- Result: White background + Gray text = **1.2:1 contrast** (WCAG FAIL)

---

## Root Cause

The dark mode CSS implementation (lines 974-1160) is **incomplete**. While major components have dark mode overrides, several container elements are missing from the `[data-theme="dark"]` ruleset.

### Missing Dark Mode Overrides

| Component | Line | Light Mode Background | Dark Mode Override | Status |
|-----------|------|----------------------|-------------------|--------|
| `.stPlotlyChart` | 791-796 | `white` | ❌ MISSING | BROKEN |
| `.streamlit-expanderContent` | 581-587 | `var(--bg-card)` (#FFFFFF) | ❌ MISSING | BROKEN |
| `.stCodeBlock` | 683-687 | `#F5F5F5` | ❌ MISSING | BROKEN |

---

## Detailed Analysis

### Issue 1: Plotly Charts (Lines 791-796)

**Current Code:**
```css
.stPlotlyChart {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    padding: 1rem;
    background-color: white;  /* ← Hard-coded white */
}
```

**Problem:**
- Chart container background is hard-coded to `white`
- No `[data-theme="dark"] .stPlotlyChart` override exists anywhere in the file
- In dark mode: White background + dark mode text colors = poor contrast

**Required Fix:**
Add dark mode override after line 1139 (in the dark mode section):
```css
[data-theme="dark"] .stPlotlyChart {
    background-color: var(--bg-card-dark) !important;
}
```

---

### Issue 2: Expander Content (Lines 581-587)

**Current Code:**
```css
.streamlit-expanderContent {
    border: 2px solid var(--border-color);
    border-top: none;
    border-radius: 0 0 10px 10px;
    padding: 1.25rem;
    background-color: var(--bg-card);  /* ← Resolves to #FFFFFF in both modes */
}
```

**Problem:**
- Uses `var(--bg-card)` which is defined as `#FFFFFF` in light mode (line 44)
- `--bg-card` variable is NOT redefined for dark mode
- Expander **header** has dark mode override (line 1135-1139)
- Expander **content** does NOT have dark mode override
- Result: Dark header + white content = broken UI

**Required Fix:**
Add dark mode override after line 1139:
```css
[data-theme="dark"] .streamlit-expanderContent {
    background-color: var(--bg-card-dark) !important;
    border-color: #4A4A5A !important;
}
```

---

### Issue 3: Code Block Containers (Lines 683-687)

**Current Code:**
```css
.stCodeBlock {
    border-radius: 8px;
    border: 1px solid var(--border-color);
    background-color: #F5F5F5;  /* ← Light gray */
}
```

**Problem:**
- Background hard-coded to light gray `#F5F5F5`
- No dark mode override exists
- Note: Fenced code blocks (`<pre>` tags, lines 691-736) DO have dark mode styling
- But the `.stCodeBlock` wrapper container remains light gray

**Required Fix:**
Add dark mode override after line 1139:
```css
[data-theme="dark"] .stCodeBlock {
    background-color: #1E1E1E !important;
    border-color: #444444 !important;
}
```

---

## Implementation Plan

### Step 1: Add Missing Dark Mode Overrides to custom.css

**File:** `/opt/tangerine/admin/styles/custom.css`

**Location:** After line 1139 (after the existing expanders section)

**Action:** Add the following rules to the dark mode section:

```css
/* ===== EXPANDERS - CONTENT ===== */

[data-theme="dark"] .streamlit-expanderContent {
    background-color: var(--bg-card-dark) !important;
    border-color: #4A4A5A !important;
}

/* ===== CHARTS ===== */

[data-theme="dark"] .stPlotlyChart {
    background-color: var(--bg-card-dark) !important;
}

/* ===== CODE BLOCKS ===== */

[data-theme="dark"] .stCodeBlock {
    background-color: #1E1E1E !important;
    border-color: #444444 !important;
}
```

**Why after line 1139?**
- Line 1139 is the end of the existing expander section
- Keeps related rules grouped together
- Maintains consistent organization (all dark mode rules in one section)

---

## Verification Plan

### Test 1: Plotly Charts in Dark Mode

**Setup:**
1. Enable dark mode
2. Navigate to Monitoring page (has charts)

**Expected:**
- Chart container background: `#1E1E2E` (dark)
- Chart text: Bright colors appropriate for dark backgrounds
- NO white chart backgrounds

**DevTools Check:**
```
Selector: .stPlotlyChart
Computed: background-color: rgb(30, 30, 46)  // #1E1E2E
```

---

### Test 2: Expander Content in Dark Mode

**Setup:**
1. Enable dark mode
2. Navigate to any page with expanders (Reference Data, Import Configs)
3. Open an expander

**Expected:**
- Expander header background: `#1E1E2E` (already working)
- Expander content background: `#1E1E2E` (should now match header)
- NO white content area inside dark header
- Text inside expander: Bright white (`#F0F0F0`)

**DevTools Check:**
```
Selector: .streamlit-expanderContent
Computed: background-color: rgb(30, 30, 46)  // #1E1E2E
Computed: border-color: rgb(74, 74, 90)     // #4A4A5A
```

---

### Test 3: Code Block Containers in Dark Mode

**Setup:**
1. Enable dark mode
2. Navigate to any page with code blocks (if any exist)

**Expected:**
- Code block container background: `#1E1E1E` (very dark gray)
- Code text: Appropriate syntax highlighting colors
- NO light gray (#F5F5F5) backgrounds

**DevTools Check:**
```
Selector: .stCodeBlock
Computed: background-color: rgb(30, 30, 30)  // #1E1E1E
Computed: border-color: rgb(68, 68, 68)      // #444444
```

---

### Test 4: Light Mode - No Regression

**Setup:**
1. Toggle to light mode
2. Check all three component types

**Expected:**
- `.stPlotlyChart`: `white` background (unchanged)
- `.streamlit-expanderContent`: `#FFFFFF` background (unchanged)
- `.stCodeBlock`: `#F5F5F5` background (unchanged)
- All text colors remain appropriate for light backgrounds

---

## Expected Results

### Contrast Ratios (Dark Mode)

After fixes, all containers will have proper contrast:

| Component | Background | Text Color | Contrast | Status |
|-----------|-----------|------------|----------|--------|
| Plotly charts | #1E1E2E | #F0F0F0 | **9.8:1** | ✅ WCAG AAA |
| Expander content | #1E1E2E | #F0F0F0 | **9.8:1** | ✅ WCAG AAA |
| Code blocks | #1E1E1E | #F0F0F0 | **9.5:1** | ✅ WCAG AAA |

All exceed WCAG AAA minimum of 7:1.

---

## Why This Fix Works

### 1. **Follows Existing Pattern**
- Uses same CSS variable system (`var(--bg-card-dark)`)
- Placed in the dark mode section with other overrides
- Consistent with other component fixes

### 2. **Background-Aware Architecture**
- Dark containers get bright text (via existing rules)
- Light containers get dark text (via light mode defaults)
- No assumptions about defaults

### 3. **Minimal Changes**
- Only adds 3 new CSS rulesets
- No changes to existing rules
- No Python code changes needed

### 4. **Maintainable**
- All dark mode rules in one place (lines 974-1160+)
- Clear comments for each section
- Easy to debug via DevTools

---

## Critical Files

**Primary Change:**
- `/opt/tangerine/admin/styles/custom.css`
  - Add ~15 lines after line 1139 (dark mode overrides section)

**No Changes Required:**
- `/opt/tangerine/admin/utils/ui_helpers.py` (already minimal)
- Python page files
- Component files

---

## Success Criteria

✅ No white container backgrounds in dark mode
✅ All container text has ≥ 7:1 contrast ratio (WCAG AAA)
✅ Expander content matches expander header styling
✅ Chart containers have dark backgrounds
✅ Code block containers have dark backgrounds
✅ Light mode unchanged (no regression)
✅ User requirement satisfied: Black text on white, white text on dark
