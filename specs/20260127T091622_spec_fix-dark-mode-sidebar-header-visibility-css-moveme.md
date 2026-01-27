# Plan: Fix Dark Mode Sidebar Header Visibility & CSS Movement Issues

## Overview

Fix two critical issues in the Tangerine admin interface dark mode:
1. **Sidebar Navigation Headers Not Visible**: Group headers (Home, Configuration, Operations, System) are not visible in dark mode
2. **Unwanted CSS Movement on Click**: Headers/elements move/animate when clicked

---

## Problem Analysis

### Issue 1: Dark Mode Sidebar Navigation Headers Not Visible

**Current Behavior:**
- Navigation section headers `<header data-testid="stNavSectionHeader">` are not visible in dark mode
- Headers blend into the sidebar background (#1E1E2E)
- User cannot distinguish section groups (Home, Configuration, Operations, System)

**Root Cause - Streamlit Emotion CSS Override:**
After extensive investigation, the problem is NOT CSS specificity in custom.css, but rather:

1. **Streamlit uses Emotion (CSS-in-JS)** which generates styles at runtime
2. **Emotion-generated classes** (`st-emotion-cache-*`) have higher specificity than attribute selectors
3. **Potential inline styles** on header elements override external stylesheet rules
4. **CSS cascade timing**: Emotion CSS is injected after our custom.css loads

**Evidence from Investigation:**
- File: `/opt/tangerine/admin/styles/custom.css` (lines 1062-1130)
- Multiple CSS rules with `!important` targeting `[data-testid="stNavSectionHeader"]` exist
- These rules specify `color: #FFFFFF !important` and `opacity: 1 !important`
- **Despite correct CSS**, headers remain invisible due to Emotion CSS priority

**Expected Behavior:**
- Headers should be bright white (#FFFFFF) in dark mode
- Clear visual distinction from regular navigation links
- No CSS animations/transitions on headers
- Sufficient contrast against sidebar background (#1E1E2E)

### Issue 2: Unwanted CSS Movement on Click

**Current Behavior:**
- When clicking on sidebar elements, they move/shift/animate
- Creates jarring user experience
- Movement appears on headers or parent containers

**Root Cause:**
- File: `/opt/tangerine/admin/styles/custom.css` (line 330)
- `.element-container { transition: all 0.3s ... }` applies to ALL elements
- Streamlit's Emotion CSS adds state-change animations
- No explicit transition-disabling rules for sidebar headers

**Expected Behavior:**
- No movement, animation, or transitions on sidebar headers
- Static, stable navigation elements
- Immediate state changes without animation

### Issue 2: Theme Doesn't Persist Across Page Refreshes

**Current Behavior:**
- User toggles to dark mode → Refreshes browser → Resets to light mode
- Theme preference not remembered

**Root Cause:**
- **File**: `/opt/tangerine/admin/app.py`
- **Lines 27-28**: Theme stored in volatile `st.session_state`
```python
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'  # Always defaults to light on refresh
```
- **Lines 112-117**: Toggle only updates session_state, no persistence
- Streamlit session_state is cleared on browser refresh
- No localStorage, cookies, or database storage for theme preference

**Expected Behavior:**
- User toggles to dark mode → Refreshes browser → Remains in dark mode
- Theme preference persists until manually changed
- Fallback to 'light' only on first visit (no saved preference)

---

## Solution Design

### Solution 1: Fix Dark Mode Sidebar Visibility (JavaScript Direct Manipulation)

**Why CSS Alone Doesn't Work:**
- Streamlit's Emotion CSS generates runtime styles with higher specificity
- External stylesheet rules (even with `!important`) lose to emotion-generated classes and inline styles
- CSS cascade timing: Emotion CSS injects after custom.css loads

**Approach: JavaScript Post-Render Style Override**

Use JavaScript to directly manipulate header element styles AFTER Streamlit renders the DOM. This bypasses CSS specificity issues entirely.

**Implementation Strategy:**

```javascript
// Inject in app.py after theme initialization
st.markdown("""
<script>
(function() {
    // Function to fix navigation section header visibility
    const fixNavHeaders = () => {
        const headers = document.querySelectorAll('[data-testid="stNavSectionHeader"]');

        headers.forEach(header => {
            // Check if we're in dark mode
            const isDarkMode = document.body.getAttribute('data-theme') === 'dark' ||
                              document.querySelector('.stApp')?.getAttribute('data-theme') === 'dark';

            if (isDarkMode) {
                // Direct style override for dark mode
                header.style.setProperty('color', '#FFFFFF', 'important');
                header.style.setProperty('opacity', '1', 'important');
                header.style.setProperty('font-weight', '700', 'important');
                header.style.setProperty('font-size', '0.95rem', 'important');
                header.style.setProperty('letter-spacing', '0.5px', 'important');
                header.style.setProperty('text-transform', 'uppercase', 'important');

                // Disable transitions and animations
                header.style.setProperty('transition', 'none', 'important');
                header.style.setProperty('transform', 'none', 'important');
                header.style.setProperty('animation', 'none', 'important');
            }
        });
    };

    // Run immediately on script load
    fixNavHeaders();

    // Run after Streamlit reruns (wait for DOM update)
    setTimeout(fixNavHeaders, 100);
    setTimeout(fixNavHeaders, 500);

    // Watch for DOM mutations (Streamlit dynamic updates)
    const observer = new MutationObserver((mutations) => {
        // Debounce rapid mutations
        clearTimeout(window.headerFixTimeout);
        window.headerFixTimeout = setTimeout(fixNavHeaders, 50);
    });

    observer.observe(document.body, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ['data-theme']
    });

    console.log('[Dark Mode Fix] Navigation header visibility script loaded');
})();
</script>
""", unsafe_allow_html=True)
```

**Additional CSS Backup (Still Include in custom.css):**

```css
/* Fallback CSS rules - may not work alone but provide baseline */
[data-theme="dark"] [data-testid="stSidebar"] [data-testid="stNavSectionHeader"],
[data-theme="dark"] header[data-testid="stNavSectionHeader"],
.stApp[data-theme="dark"] [data-testid="stNavSectionHeader"] {
    color: #FFFFFF !important;
    opacity: 1 !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    transition: none !important;
    transform: none !important;
    animation: none !important;
}
```

### Solution 2: Disable Unwanted CSS Movement

**Approach: Explicit Transition Disabling**

Add CSS rules to prevent ANY transitions/animations on sidebar elements, especially headers.

**Implementation:**

```css
/* In custom.css - Add at the end of dark mode section */

/* Disable ALL transitions in sidebar to prevent movement */
[data-testid="stSidebar"],
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] [data-testid="stNavSectionHeader"],
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
[data-testid="stSidebar"] a,
.stApp[data-theme="dark"] [data-testid="stSidebar"],
.stApp[data-theme="dark"] [data-testid="stSidebar"] * {
    transition: none !important;
    transform: none !important;
    animation: none !important;
}

/* Override element-container transitions specifically in sidebar */
[data-testid="stSidebar"] .element-container {
    transition: none !important;
    transform: none !important;
}
```

**JavaScript Enhancement:**

The JavaScript code in Solution 1 already includes transition/transform disabling, providing double coverage.

### Solution 3: Theme Persistence (Already Implemented)

Theme persistence was already implemented in previous work using localStorage + query parameters. This solution focuses on the visibility and movement issues.

**Approach: Browser localStorage via JavaScript Bridge**

Since Streamlit doesn't have direct localStorage API, use JavaScript injection to bridge between localStorage and session_state.

**Implementation Steps:**

**Step 1: Read Theme from localStorage on Init**
```python
# admin/app.py, after line 27
if 'theme' not in st.session_state:
    # Inject JavaScript to read from localStorage
    st.markdown("""
        <script>
        const savedTheme = localStorage.getItem('tangerine_theme') || 'light';
        const themeData = document.createElement('div');
        themeData.id = 'theme-data';
        themeData.setAttribute('data-theme', savedTheme);
        themeData.style.display = 'none';
        document.body.appendChild(themeData);
        </script>
    """, unsafe_allow_html=True)

    # Default to light (will be synced by JS if saved preference exists)
    st.session_state.theme = 'light'
```

**Step 2: Save Theme to localStorage on Toggle**
```python
# admin/app.py, lines 112-117 - replace with:
if dark_mode and st.session_state.theme == 'light':
    st.session_state.theme = 'dark'
    # Save to localStorage
    st.markdown("""
        <script>
        localStorage.setItem('tangerine_theme', 'dark');
        </script>
    """, unsafe_allow_html=True)
    st.rerun()
elif not dark_mode and st.session_state.theme == 'dark':
    st.session_state.theme = 'light'
    # Save to localStorage
    st.markdown("""
        <script>
        localStorage.setItem('tangerine_theme', 'light');
        </script>
    """, unsafe_allow_html=True)
    st.rerun()
```

**Alternative Approach: Query Parameters**
Simpler but less elegant - appends `?theme=dark` to URL:
```python
# Initialize from query parameter
if 'theme' not in st.session_state:
    st.session_state.theme = st.query_params.get('theme', 'light')

# Update query parameter on toggle
if st.session_state.theme not in st.query_params.get('theme', ''):
    st.query_params['theme'] = st.session_state.theme
```

---

## Implementation Steps

### Step 1: Add JavaScript Header Visibility Fix

**File**: `/opt/tangerine/admin/app.py`
**Location**: After theme initialization and CSS loading (after line 64: `load_custom_css()`)

**Action**: INSERT JavaScript to override header styles post-render

```python
# After load_custom_css()

# JavaScript fix for dark mode sidebar header visibility
# This overrides Streamlit's Emotion CSS which has higher specificity than external stylesheets
if st.session_state.theme == 'dark':
    st.markdown("""
    <script>
    (function() {
        // Function to fix navigation section header visibility in dark mode
        const fixNavHeaders = () => {
            const headers = document.querySelectorAll('[data-testid="stNavSectionHeader"]');

            headers.forEach(header => {
                // Check current theme
                const isDarkMode = document.body.getAttribute('data-theme') === 'dark' ||
                                  document.querySelector('.stApp')?.getAttribute('data-theme') === 'dark';

                if (isDarkMode) {
                    // Direct style override - bypasses Emotion CSS specificity
                    header.style.setProperty('color', '#FFFFFF', 'important');
                    header.style.setProperty('opacity', '1', 'important');
                    header.style.setProperty('font-weight', '700', 'important');
                    header.style.setProperty('font-size', '0.95rem', 'important');
                    header.style.setProperty('letter-spacing', '0.5px', 'important');
                    header.style.setProperty('text-transform', 'uppercase', 'important');

                    // Disable transitions and animations to prevent movement
                    header.style.setProperty('transition', 'none', 'important');
                    header.style.setProperty('transform', 'none', 'important');
                    header.style.setProperty('animation', 'none', 'important');
                }
            });
        };

        // Run immediately
        fixNavHeaders();

        // Run after short delays to catch Streamlit's async rendering
        setTimeout(fixNavHeaders, 100);
        setTimeout(fixNavHeaders, 500);

        // Watch for DOM mutations (Streamlit reruns, theme changes)
        const observer = new MutationObserver((mutations) => {
            clearTimeout(window.headerFixTimeout);
            window.headerFixTimeout = setTimeout(fixNavHeaders, 50);
        });

        observer.observe(document.body, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['data-theme']
        });

        console.log('[Dark Mode Fix] Header visibility script initialized');
    })();
    </script>
    """, unsafe_allow_html=True)
```

### Step 2: Add CSS Fallback Rules (Backup)

**File**: `/opt/tangerine/admin/styles/custom.css`
**Location**: After existing dark mode sidebar rules (around line 1130)

**Action**: ADD comprehensive fallback CSS rules

```css
/* ============================================
   DARK MODE FIX: Navigation Section Headers
   ============================================
   NOTE: These rules may not work alone due to Streamlit Emotion CSS,
   but provide fallback coverage. JavaScript in app.py handles primary fix.
*/

/* Target stNavSectionHeader with maximum specificity */
[data-theme="dark"] [data-testid="stSidebar"] [data-testid="stNavSectionHeader"],
[data-theme="dark"] header[data-testid="stNavSectionHeader"],
.stApp[data-theme="dark"] [data-testid="stSidebar"] [data-testid="stNavSectionHeader"],
.stApp[data-theme="dark"] header[data-testid="stNavSectionHeader"] {
    color: #FFFFFF !important;
    opacity: 1 !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;

    /* Disable transitions/animations */
    transition: none !important;
    transform: none !important;
    animation: none !important;
}

/* Disable ALL transitions in sidebar to prevent movement on click */
[data-testid="stSidebar"],
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] [data-testid="stNavSectionHeader"],
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
[data-testid="stSidebar"] a,
.stApp[data-theme="dark"] [data-testid="stSidebar"],
.stApp[data-theme="dark"] [data-testid="stSidebar"] * {
    transition: none !important;
    transform: none !important;
    animation: none !important;
}

/* Specifically override element-container transitions in sidebar */
[data-testid="stSidebar"] .element-container,
.stApp[data-theme="dark"] [data-testid="stSidebar"] .element-container {
    transition: none !important;
    transform: none !important;
    animation: none !important;
}
```

### Step 3: Clean Up Existing Attempts

**File**: `/opt/tangerine/admin/styles/custom.css`
**Location**: Lines 1060-1130 (existing dark mode sidebar rules)

**Action**: REMOVE the following problematic rules if they exist:

1. Remove doubled selector attempts (lines ~1119-1130):
```css
/* DELETE - This doesn't work */
[data-theme="dark"][data-theme="dark"] [data-testid="stSidebar"] header[data-testid="stNavSectionHeader"][data-testid="stNavSectionHeader"]
```

2. Keep the general sidebar background and link color rules, but ensure they don't conflict

### Step 4: Verify Theme Persistence (Already Implemented)

**File**: `/opt/tangerine/admin/app.py`
**Check**: Lines 26-58 should have localStorage + query parameter sync
**Check**: Lines 141-163 should save theme to localStorage on toggle

If these are already in place, no changes needed. Theme persistence was implemented in previous work.

---

## Testing Strategy

### Visual Verification Test

**Manual Test Steps:**

1. **Toggle to Dark Mode:**
   - Click "🌙 Dark Mode" toggle in sidebar
   - Page should immediately change to dark theme

2. **Verify Header Visibility:**
   - Look at sidebar navigation section headers:
     - "Home" - Should be **bright white**, **clearly visible**
     - "Configuration" - Should be **bright white**, **clearly visible**
     - "Operations" - Should be **bright white**, **clearly visible**
     - "System" - Should be **bright white**, **clearly visible**
   - Headers should have:
     - Color: White (#FFFFFF)
     - Font: Bold, uppercase
     - High contrast against dark sidebar background

3. **Verify No CSS Movement:**
   - Click on each navigation header
   - Click on navigation links (Dashboard, Imports, etc.)
   - **Expected**: NO movement, shifting, or animation
   - Elements should remain statically positioned

4. **Compare with Navigation Links:**
   - Navigation links (Dashboard, Imports, etc.) should be dimmer gray (#E8E8E8)
   - Section headers should be noticeably brighter/bolder than links

### DevTools Console Test

**Check JavaScript Execution:**

```javascript
// Open DevTools Console (F12), run:

// 1. Verify script loaded
console.log('Checking for dark mode fix script...');

// 2. Check headers are targeted
const headers = document.querySelectorAll('[data-testid="stNavSectionHeader"]');
console.log(`Found ${headers.length} navigation headers`);

// 3. Inspect computed styles
headers.forEach(header => {
    const styles = getComputedStyle(header);
    console.log(`Header: "${header.textContent.trim()}"`);
    console.log(`  Color: ${styles.color}`);  // Should be: rgb(255, 255, 255)
    console.log(`  Opacity: ${styles.opacity}`);  // Should be: 1
    console.log(`  Font-weight: ${styles.fontWeight}`);  // Should be: 700
    console.log(`  Transition: ${styles.transition}`);  // Should be: none
    console.log('---');
});

// Expected output example:
// Header: "HOME"
//   Color: rgb(255, 255, 255)
//   Opacity: 1
//   Font-weight: 700
//   Transition: none
```

### Browser Compatibility Test

Test in multiple browsers to ensure JavaScript works consistently:

| Browser | Version | Expected Result |
|---------|---------|-----------------|
| Chrome | 90+ | Headers visible, no movement |
| Firefox | 88+ | Headers visible, no movement |
| Edge | 90+ | Headers visible, no movement |
| Safari | 14+ | Headers visible, no movement (if available) |

### Performance Test

**Check for Performance Impact:**

1. Open DevTools Performance tab
2. Toggle dark mode ON
3. Record performance for 5 seconds
4. **Verify**: No excessive DOM mutations
5. **Verify**: JavaScript execution time < 50ms
6. **Verify**: No layout thrashing

**MutationObserver Check:**
```javascript
// In console, verify observer isn't firing excessively
let mutationCount = 0;
const testObserver = new MutationObserver(() => mutationCount++);
testObserver.observe(document.body, { subtree: true, childList: true });

// Wait 5 seconds, then check count
setTimeout(() => {
    console.log(`Mutations in 5 seconds: ${mutationCount}`);
    testObserver.disconnect();
    // Expected: < 100 (reasonable for Streamlit's reactivity)
}, 5000);
```

### Theme Persistence Test (Already Implemented)

**Verify localStorage Integration:**

1. Toggle dark mode ON
2. Open DevTools Console
3. Check: `localStorage.getItem('tangerine_theme')` returns `'dark'`
4. Refresh browser (F5)
5. **Verify**: App loads in dark mode
6. **Verify**: Headers remain visible after refresh
7. Toggle light mode ON
8. Refresh browser
9. **Verify**: App loads in light mode

### Edge Cases

1. **JavaScript Disabled:**
   - Expected: Headers may not be visible (graceful degradation)
   - Fallback CSS rules provide partial coverage

2. **Slow Network:**
   - JavaScript loads with slight delay
   - Headers should fix themselves within 500ms

3. **Streamlit Rerun:**
   - Navigate between pages
   - **Verify**: Headers remain visible after page change

4. **Multiple Rapid Theme Toggles:**
   - Toggle dark → light → dark → light rapidly
   - **Verify**: No JavaScript errors
   - **Verify**: Headers always end up in correct state

---

## Success Criteria

### Header Visibility Success Criteria

✅ **Visual Verification:**
- [ ] All navigation section headers (Home, Configuration, Operations, System) are **clearly visible** in dark mode
- [ ] Headers display in **bright white** (#FFFFFF)
- [ ] Headers are **bold** (font-weight: 700)
- [ ] Headers have **sufficient contrast** against sidebar background (#1E1E2E)
- [ ] Headers are **uppercase** and properly styled
- [ ] Navigation links (Dashboard, Imports, etc.) remain distinct with **dimmer gray** (#E8E8E8)

✅ **No Movement Verification:**
- [ ] **Zero CSS movement** when clicking on headers
- [ ] **Zero CSS movement** when clicking on navigation links
- [ ] **No transitions** visible on sidebar elements
- [ ] **No animations** on hover or click
- [ ] Headers remain **statically positioned** during all interactions

✅ **Technical Verification:**
- [ ] JavaScript loads without errors
- [ ] Console shows: `[Dark Mode Fix] Header visibility script initialized`
- [ ] DevTools inspection shows computed styles:
  - `color: rgb(255, 255, 255)`
  - `opacity: 1`
  - `font-weight: 700`
  - `transition: none`
- [ ] MutationObserver doesn't cause performance issues
- [ ] Works in Chrome, Firefox, Edge, Safari

✅ **Persistence Verification:**
- [ ] Headers remain visible after page refresh (F5)
- [ ] Headers remain visible after navigating between pages
- [ ] Headers remain visible after toggling theme multiple times
- [ ] No console errors during Streamlit reruns

### Theme Persistence Success Criteria (Already Implemented)

✅ **Functional Verification:**
- [ ] Toggle to dark mode → Refresh → Remains dark
- [ ] Toggle to light mode → Refresh → Remains light
- [ ] localStorage contains `'tangerine_theme': 'dark'` or `'light'`
- [ ] Query parameter `?theme=dark` or `?theme=light` present in URL

---

## Critical Files

### Primary Files to Modify

1. **`/opt/tangerine/admin/app.py`**
   - **Line 64+**: INSERT JavaScript header visibility fix (after `load_custom_css()`)
   - **Lines 26-58**: Theme persistence (already implemented, verify)
   - **Lines 141-163**: Theme toggle with localStorage (already implemented, verify)

2. **`/opt/tangerine/admin/styles/custom.css`**
   - **Line 1130+**: ADD fallback CSS rules for header visibility
   - **Line 1140+**: ADD transition-disabling rules for sidebar
   - **Lines 1119-1130**: CLEAN UP doubled selector attempts (if present)

### Files to Verify (Already Implemented)

3. **`/opt/tangerine/admin/utils/ui_helpers.py`**
   - Lines 46-77: `load_custom_css()` function
   - Lines 116-386: `_apply_theme_css()` function
   - **No changes needed** - just verify CSS loading works correctly

---

## Risks & Mitigation

### JavaScript Approach Risks

**Risk: JavaScript Timing Issues**
- **Problem**: JavaScript may execute before Streamlit fully renders DOM
- **Mitigation**:
  - Run `fixNavHeaders()` immediately on script load
  - Add delayed retries (100ms, 500ms)
  - Use MutationObserver to catch late renders
- **Severity**: Low (multiple fallbacks in place)

**Risk: MutationObserver Performance**
- **Problem**: Observer could fire excessively, causing performance degradation
- **Mitigation**:
  - Debounce observer callback with 50ms timeout
  - Only observe necessary attributes (`data-theme`, `childList`)
  - Limit observer scope to `document.body`
- **Severity**: Low (debouncing prevents excessive calls)

**Risk: JavaScript Disabled**
- **Problem**: Users with JavaScript disabled won't see headers
- **Mitigation**:
  - Include fallback CSS rules (may partially work)
  - Document that JavaScript is required for full functionality
  - Most Streamlit users have JavaScript enabled
- **Severity**: Very Low (Streamlit requires JavaScript anyway)

**Risk: Browser Compatibility**
- **Problem**: `style.setProperty()` may not work in older browsers
- **Mitigation**:
  - Use standard DOM APIs (supported in all modern browsers)
  - Target Chrome 90+, Firefox 88+, Edge 90+ (current Streamlit support)
  - Fallback CSS provides partial coverage
- **Severity**: Very Low (targeting modern browsers)

### CSS Approach Limitations

**Known Issue: CSS Alone Insufficient**
- **Problem**: Streamlit Emotion CSS overrides external stylesheets
- **Mitigation**: JavaScript approach is primary fix, CSS is backup
- **Severity**: Medium (requires JavaScript solution)

**Known Issue: Transition Disabling May Affect Other Elements**
- **Problem**: Broad `transition: none` rules may disable wanted animations
- **Mitigation**: Scope rules specifically to sidebar with `[data-testid="stSidebar"]`
- **Severity**: Low (sidebar-specific rules)

### Theme Persistence Risks (Already Mitigated)

**Risk: localStorage Disabled**
- **Problem**: Incognito mode, corporate policies may block localStorage
- **Mitigation**: Graceful degradation to session-only theme (default behavior)
- **Severity**: Very Low (acceptable fallback)

**Risk: Query Parameter Pollution**
- **Problem**: `?theme=dark` in URL may be undesirable
- **Mitigation**: Use `history.replaceState()` to avoid URL changes (if needed)
- **Severity**: Very Low (query params are common pattern)

---

## Verification Steps (End-to-End)

### After Implementation

**Step 1: Deploy Changes**
```bash
docker compose restart admin
```

**Step 2: Clear Browser Cache**
- Hard refresh: `Ctrl + Shift + R` (Windows/Linux) or `Cmd + Shift + R` (Mac)
- Or clear browser cache manually

**Step 3: Verify Header Visibility**

1. Open admin interface in browser
2. Toggle dark mode ON
3. **Visual Check**:
   - Look at sidebar navigation section headers
   - "Home", "Configuration", "Operations", "System" should be **bright white**
   - Headers should be **clearly visible** and **bold**
   - High contrast against dark sidebar background
4. **DevTools Check**:
   - Open Console (F12)
   - Look for: `[Dark Mode Fix] Header visibility script initialized`
   - Run inspection script:
     ```javascript
     const headers = document.querySelectorAll('[data-testid="stNavSectionHeader"]');
     headers.forEach(h => {
         console.log(`${h.textContent}: color=${getComputedStyle(h).color}, opacity=${getComputedStyle(h).opacity}`);
     });
     ```
   - Expected output: `color=rgb(255, 255, 255), opacity=1`

**Step 4: Verify No CSS Movement**

1. Click on each section header (Home, Configuration, Operations, System)
2. Click on navigation links (Dashboard, Imports, etc.)
3. **Expected**: NO movement, shifting, or animation
4. **Expected**: Immediate, static click responses

**Step 5: Verify Theme Persistence**

1. Toggle dark mode ON
2. Verify headers are visible
3. Press `F5` to refresh browser
4. **Verify**: App loads in dark mode
5. **Verify**: Headers remain visible after refresh
6. **DevTools Check**:
   - Console: `localStorage.getItem('tangerine_theme')` returns `'dark'`
   - URL contains `?theme=dark` query parameter

**Step 6: Cross-Browser Testing**

Repeat Steps 3-5 in:
- Chrome (primary target)
- Firefox
- Edge
- Safari (if available)

**Step 7: Edge Case Testing**

1. **Rapid Theme Toggling**:
   - Toggle dark → light → dark → light rapidly (5 times)
   - Verify no JavaScript errors
   - Verify headers always end in correct state

2. **Page Navigation**:
   - Navigate to different pages (Dashboard → Imports → Scheduler)
   - Verify headers remain visible across all pages

3. **Incognito Mode**:
   - Open in incognito/private window
   - Theme may not persist (expected)
   - Headers should still be visible when dark mode enabled

---

## Quick Reference Summary

### What's Being Fixed

1. **Header Visibility**: Navigation section headers (Home, Configuration, Operations, System) are not visible in dark mode
2. **CSS Movement**: Unwanted animations/transitions when clicking sidebar elements

### Why CSS Alone Doesn't Work

- Streamlit uses **Emotion CSS** (CSS-in-JS) which generates runtime styles
- Emotion styles have **higher specificity** than external stylesheets
- External CSS rules (even with `!important`) are overridden by emotion-generated classes

### The Solution

**JavaScript Direct Manipulation:**
- Use JavaScript `style.setProperty()` to override styles after Streamlit renders
- MutationObserver watches for DOM changes and re-applies fixes
- Explicitly disable transitions/animations to prevent movement

**CSS Fallback:**
- Add comprehensive CSS rules as backup
- Disable all transitions in sidebar context
- Provide partial coverage if JavaScript fails

### Implementation Checklist

- [ ] Add JavaScript header fix in `app.py` (after line 64)
- [ ] Add fallback CSS rules in `custom.css` (after line 1130)
- [ ] Add transition-disabling CSS rules in `custom.css`
- [ ] Clean up old doubled selector attempts
- [ ] Test header visibility in dark mode
- [ ] Test no CSS movement on click
- [ ] Test theme persistence across refresh
- [ ] Test in multiple browsers

### Files to Modify

1. `/opt/tangerine/admin/app.py` - Add JavaScript fix (line 64+)
2. `/opt/tangerine/admin/styles/custom.css` - Add fallback CSS (line 1130+)

### Expected Outcome

✅ **Headers visible**: Bright white, bold, uppercase in dark mode
✅ **No movement**: Zero transitions/animations on sidebar elements
✅ **Persistent**: Theme persists across browser refreshes
✅ **Performant**: JavaScript execution < 50ms, no layout thrashing

---

## Timeline

- **JavaScript Implementation**: 15 minutes
- **CSS Fallback Implementation**: 10 minutes
- **Testing & Verification**: 20 minutes
- **Total**: ~45 minutes including thorough testing

---

**END OF PLAN - DARK MODE HEADER VISIBILITY FIX**
