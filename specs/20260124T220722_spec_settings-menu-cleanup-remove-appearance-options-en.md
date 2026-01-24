# Settings Menu Cleanup: Remove Appearance Options & Enforce Wide Mode

## Problem Summary

After fixing the sidebar toggle visibility, the settings menu needs cleanup:

1. **Remove appearance option from settings** - Users shouldn't access theme controls that conflict with custom toggle
2. **Remove custom app theme dropdown** - App theme should only be controlled by the custom dark/light mode toggle
3. **Enforce wide mode as default** - No user override for layout width

## Root Cause Analysis

### Current Situation

**Settings Menu Access:**
- Hamburger menu button is hidden via CSS (from previous fix)
- However, users may still access settings through browser keyboard shortcuts or other means
- The settings menu contains "Appearance" options that conflict with custom theme toggle

**Theme System Conflict:**
- Custom toggle in sidebar: Sets `st.session_state.theme` to 'light' or 'dark'
- Streamlit's built-in theme: Accessible via settings menu, can override custom theme
- Both systems can conflict if users access Streamlit's appearance settings

**Wide Mode:**
- Currently set via `st.set_page_config(layout="wide")` in `app.py`
- Users can change this in settings menu if accessible
- No config.toml setting to permanently enforce wide mode

### Streamlit Configuration Limitations

**Key Finding:** Streamlit's `config.toml` does NOT provide options to:
- Remove specific menu items (like "Appearance")
- Disable the custom app theme dropdown
- Prevent users from accessing theme settings via settings menu
- Lock wide mode to prevent user override

**Available Solutions:**
1. **CSS-based hiding** - Hide appearance-related UI elements in settings menu
2. **Config.toml base theme** - Set a default theme base to reduce conflicts
3. **Ensure custom CSS wins** - Use `!important` flags to override any Streamlit theme changes

---

## Fix Strategy

### Fix 1: Set Base Theme in Config.toml

**Approach:** Establish a default theme base to reduce conflicts with custom toggle

**Changes needed in `admin/.streamlit/config.toml`:**

Add `base` setting to force a specific theme foundation:

```toml
[theme]
base = "light"  # Set foundation - custom toggle will override with CSS
primaryColor = "#FF8C42"
backgroundColor = "#F8F9FA"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#2C3E50"
font = "sans serif"
```

**Rationale:** While this doesn't prevent users from changing themes in settings, it establishes a consistent baseline that our custom CSS can reliably override.

---

### Fix 2: Hide Appearance Settings UI with CSS

**Approach:** Use CSS to hide appearance-related controls in the settings menu if users somehow access it.

**Changes needed in `admin/utils/ui_helpers.py`:**

Add CSS rules to hide appearance options within settings dialog:

```css
/* Hide appearance settings section */
[data-testid="stSettingsDialog"] div[data-testid="stAppearanceSettings"],
[data-testid="stSettingsDialog"] button[data-testid="themeSettings"],
div[aria-label*="Appearance"],
div[aria-label*="Theme"],
section[aria-label*="Appearance"] {
    display: none !important;
}

/* Hide custom theme dropdown */
div[data-testid="stThemeManager"],
[data-baseweb="select"][aria-label*="theme"],
[data-baseweb="select"][aria-label*="Theme"] {
    display: none !important;
}

/* Hide layout width toggle (enforce wide mode) */
button[data-testid="layoutToggle"],
div[aria-label*="wide mode"],
div[aria-label*="Wide mode"] {
    display: none !important;
}
```

**Rationale:** Defense in depth - even if hamburger menu is accessible, hide the conflicting controls.

---

### Fix 3: Strengthen CSS Override Priority

**Approach:** Ensure custom theme CSS always wins over Streamlit's built-in theme system.

**Already implemented in `admin/utils/ui_helpers.py`:**
- `_apply_theme_css()` function uses `!important` flags ✅
- CSS is applied after Streamlit loads via `st.markdown()` ✅
- Theme reruns on toggle to reapply CSS ✅

**No changes needed** - current implementation is correct.

---

## Implementation Plan

### Step 1: Update Config.toml to Set Base Theme

**File:** `admin/.streamlit/config.toml`

**Actions:**
1. Add `base = "light"` to the `[theme]` section
2. This establishes a consistent foundation for the custom toggle to override

**Expected Result:** Default theme base is set, reducing potential conflicts

---

### Step 2: Add CSS to Hide Appearance Settings

**File:** `admin/utils/ui_helpers.py`
**Function:** `load_custom_css()` (around line 79-117)

**Actions:**
1. Locate the section where hamburger menu is hidden
2. Add new CSS rules to also hide appearance-related settings if users access the settings dialog
3. Target multiple possible selectors for appearance controls, theme dropdowns, and layout toggles

**CSS to add:**
```css
/* Hide appearance settings within settings dialog */
[data-testid="stSettingsDialog"] div[data-testid="stAppearanceSettings"],
[data-testid="stSettingsDialog"] button[data-testid="themeSettings"],
div[aria-label*="Appearance"],
div[aria-label*="Theme"],
section[aria-label*="Appearance"],
div[data-testid="stThemeManager"],
[data-baseweb="select"][aria-label*="theme"],
[data-baseweb="select"][aria-label*="Theme"],
button[data-testid="layoutToggle"],
div[aria-label*="wide mode"],
div[aria-label*="Wide mode"] {
    display: none !important;
}
```

**Expected Result:** Appearance options hidden from settings menu, wide mode enforced

---

### Step 3: Verify Wide Mode is Enforced in app.py

**File:** `admin/app.py`
**Location:** Line 18

**Actions:**
1. Confirm `st.set_page_config(layout="wide")` is present ✅ (already exists)
2. No changes needed - this is correct

**Expected Result:** Wide mode is the default layout

---

### Step 4: Test and Verify

**Testing steps:**
1. Restart the Streamlit container: `docker compose restart admin`
2. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
3. Verify hamburger menu is still hidden in header
4. If hamburger menu is accessible (keyboard shortcut, etc.), verify:
   - Appearance settings section is not visible
   - Custom theme dropdown is not visible
   - Wide mode toggle is not visible
5. Verify custom dark mode toggle works correctly in sidebar
6. Test theme switching between light and dark modes
7. Verify wide mode is active on all pages

---

## Critical Files to Modify

1. **`admin/.streamlit/config.toml`** (CONFIGURATION)
   - Add `base = "light"` to `[theme]` section
   - Establishes default theme foundation

2. **`admin/utils/ui_helpers.py`** (PRIMARY CSS FILE)
   - Lines 79-117: `load_custom_css()` function
   - Add CSS rules to hide appearance settings, theme dropdown, and layout toggle
   - Place after existing hamburger menu hiding rules

3. **No changes needed to:**
   - `admin/app.py` (wide mode already set, toggle code is correct)
   - `admin/styles/custom.css` (no conflicts there)
   - `admin/utils/ui_helpers.py` lines 120-391 (`_apply_theme_css()` function - already correct)

---

## Verification Steps

### After Implementation:

1. **Settings Menu Access:**
   - ✅ Hamburger menu button is hidden in header
   - ✅ If settings dialog is accessible (keyboard shortcut), appearance section is hidden
   - ✅ Custom theme dropdown is not visible in settings
   - ✅ Wide mode toggle is not visible in settings

2. **Wide Mode Enforcement:**
   - ✅ All pages display in wide mode by default
   - ✅ Content uses full width of browser window
   - ✅ No user option to switch to narrow mode

3. **Custom Theme Toggle:**
   - ✅ Dark mode toggle is visible at bottom of sidebar
   - ✅ Toggle switches between light and dark themes
   - ✅ Custom CSS overrides any Streamlit theme settings
   - ✅ Theme state persists during session
   - ✅ No conflicts with Streamlit's built-in theme system

4. **No Side Effects:**
   - ✅ All navigation links in sidebar work
   - ✅ Database connection status displays correctly
   - ✅ Page content displays normally
   - ✅ All other UI components function as expected
   - ✅ No visual artifacts from hidden elements

---

## Risk Assessment

**Risk Level:** LOW

**Why:**
- Changes are configuration + CSS only (no Python logic changes)
- Isolated to config file and UI helper file
- Easy to rollback if needed
- No data or functionality changes
- Wide mode already enforced in app.py

**Limitations:**
- CSS hiding is not a security feature - determined users with browser DevTools can bypass
- This is a UI/UX convenience to prevent confusion, not access control
- Acceptable for internal admin interface where users are trusted

**Mitigation:**
- Test immediately after container restart
- Keep browser dev tools open to inspect CSS and verify appearance settings are hidden
- Can quickly revert changes if issues arise
- Monitor for Streamlit version updates that might change selector names

---

## Implementation Notes

1. **Config.toml base setting:** Sets a foundation but doesn't prevent user override - CSS is the real enforcement
2. **CSS Specificity:** Using `!important` is acceptable here since we're overriding Streamlit's default styles intentionally
3. **Multiple Selectors:** Using multiple selectors for appearance settings ensures we hide it even if Streamlit changes the DOM structure
4. **Testing:** Always test in both light and dark modes after changes
5. **Container Restart:** Required for config.toml and CSS changes in Python files to take effect
6. **Streamlit Version Compatibility:** These selectors may need updates if Streamlit releases major version changes

---

## Success Criteria

✅ Base theme set in config.toml (light foundation)
✅ Appearance settings hidden from settings menu (if accessible)
✅ Custom theme dropdown not visible
✅ Wide mode toggle not visible
✅ Wide mode enforced across all pages
✅ Custom dark mode toggle works correctly
✅ No conflicts between custom toggle and Streamlit theme system
✅ No other UI elements affected

---

## Additional Context

**Why CSS-based hiding is the only option:**
- Streamlit's config.toml does not provide settings to disable specific menu items
- The hamburger menu and appearance settings are core Streamlit features
- Customizing Streamlit's source code would require forking the project
- CSS hiding is the industry-standard approach for this use case

**Alternative considered:**
- Fork Streamlit and modify source code to remove appearance settings
- **Rejected:** Too much maintenance overhead, breaks with upstream updates
