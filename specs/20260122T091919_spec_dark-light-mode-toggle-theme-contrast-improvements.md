# Dark/Light Mode Toggle & Theme Contrast Improvements

## Overview

Add a visible dark/light mode toggle button and improve color contrast for both themes based on WCAG accessibility best practices.

---

## Current State

- Theme toggle exists only in hamburger menu (Settings > Theme)
- Custom CSS at `admin/styles/custom.css` has basic dark mode support (lines 512-598)
- No `.streamlit/config.toml` exists - using Streamlit defaults
- Colors hardcoded for light mode; dark mode uses `prefers-color-scheme` media query

---

## Implementation Plan

### Phase 1: Add Theme Toggle Switch to Sidebar (Bottom)

**File:** `admin/app.py`

Add a toggle switch at the bottom of the sidebar, near the DB connection status:

```python
# Add sidebar content
with st.sidebar:
    st.markdown("---")

    # Database connection status
    if st.session_state.db_connected:
        st.success("Database Connected")
    else:
        st.error("Database Disconnected")
        st.caption("Check DB_URL environment variable")

    # Theme toggle at bottom
    st.markdown("---")

    # Initialize theme in session state
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'

    # Toggle switch with moon/sun label
    dark_mode = st.toggle(
        "🌙 Dark Mode",
        value=st.session_state.theme == 'dark',
        key="theme_toggle"
    )

    # Apply theme change
    if dark_mode != (st.session_state.theme == 'dark'):
        st.session_state.theme = 'dark' if dark_mode else 'light'
        # Apply theme via Streamlit config
        theme_settings = {
            'dark': {
                'theme.base': 'dark',
                'theme.backgroundColor': '#121212',
                'theme.secondaryBackgroundColor': '#1E1E2E',
                'theme.textColor': '#E8E8E8',
                'theme.primaryColor': '#FFA05C',
            },
            'light': {
                'theme.base': 'light',
                'theme.backgroundColor': '#F8F9FA',
                'theme.secondaryBackgroundColor': '#FFFFFF',
                'theme.textColor': '#2C3E50',
                'theme.primaryColor': '#FF8C42',
            }
        }
        for key, val in theme_settings[st.session_state.theme].items():
            st._config.set_option(key, val)
        st.rerun()
```

---

### Phase 2: Create Streamlit Config with Custom Themes

**New File:** `admin/.streamlit/config.toml`

Define proper light and dark themes with good contrast:

```toml
[theme]
# Light theme (default)
primaryColor = "#FF8C42"  # Tangerine orange

[theme.light]
backgroundColor = "#F8F9FA"  # Soft off-white (not pure white)
secondaryBackgroundColor = "#FFFFFF"
textColor = "#2C3E50"  # Dark blue-gray (good contrast)

[theme.dark]
backgroundColor = "#1A1A2E"  # Dark blue-gray (not pure black)
secondaryBackgroundColor = "#16213E"  # Slightly lighter
textColor = "#E8E8E8"  # Off-white (not pure white)
```

---

### Phase 3: Update CSS Color Palette

**File:** `admin/styles/custom.css`

#### Light Mode Colors (Best Practices)
| Element | Current | Improved | Reason |
|---------|---------|----------|--------|
| Background | `#F8F9FA` | `#F8F9FA` | Good - soft white |
| Text | `#2C3E50` | `#2C3E50` | Good - meets 4.5:1 |
| Cards | `white` | `#FFFFFF` | OK |

#### Dark Mode Colors (Best Practices)
| Element | Current | Improved | Reason |
|---------|---------|----------|--------|
| Background | `#1E1E1E` | `#121212` or `#1A1A2E` | Softer than pure black |
| Text | `#E0E0E0` | `#E8E8E8` | Off-white, better contrast |
| Cards | `#262626` | `#1E1E2E` | Matches background tone |
| Primary | `#FF8C42` | `#FFA05C` | Slightly desaturated for dark |
| Borders | `#404040` | `#2D2D3D` | Subtle, not harsh |

#### Specific CSS Changes

1. **Update `:root` variables for dark mode:**
```css
[data-theme="dark"],
.stApp[data-theme="dark"] {
    --bg-light: #121212;
    --text-dark: #E8E8E8;
    --text-light: #B0B0B0;
    --border-color: #2D2D3D;
    --tangerine-primary: #FFA05C;  /* Desaturated for dark */
    --tangerine-light: #3D2A1A;    /* Dark version */
}
```

2. **Fix metric cards contrast:**
```css
[data-theme="dark"] [data-testid="stMetric"] {
    background-color: #1E1E2E;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
```

3. **Fix tabs contrast:**
```css
[data-theme="dark"] .stTabs [aria-selected="true"] {
    background-color: #FFA05C;
    color: #121212;  /* Dark text on orange */
}
```

4. **Fix alert backgrounds:**
```css
[data-theme="dark"] .stSuccess { background-color: #1A3D25; }
[data-theme="dark"] .stError { background-color: #3D1A1A; }
[data-theme="dark"] .stWarning { background-color: #3D3D1A; }
[data-theme="dark"] .stInfo { background-color: #1A2A3D; }
```

---

### Phase 4: Update ui_helpers.py for Theme-Aware HTML

**File:** `admin/utils/ui_helpers.py`

Update functions that render inline HTML to respect theme:

```python
def render_stat_card(label: str, value: str, icon: str = "📊", color: str = "#FF8C42"):
    # Detect theme and adjust colors
    is_dark = st.session_state.get('theme', 'light') == 'dark'
    bg_color = "#1E1E2E" if is_dark else "white"
    text_color = "#B0B0B0" if is_dark else "#6C757D"
    # ... rest of function
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `admin/app.py` | Add theme toggle button in sidebar |
| `admin/.streamlit/config.toml` | Create with light/dark theme definitions |
| `admin/styles/custom.css` | Update dark mode colors for better contrast |
| `admin/utils/ui_helpers.py` | Make inline HTML theme-aware |

---

## Color Palette Reference

### Light Theme
- **Background:** `#F8F9FA` (soft white)
- **Cards:** `#FFFFFF`
- **Text Primary:** `#2C3E50` (dark blue-gray)
- **Text Secondary:** `#6C757D`
- **Accent:** `#FF8C42` (tangerine)
- **Borders:** `#DEE2E6`

### Dark Theme
- **Background:** `#121212` (Material dark)
- **Cards:** `#1E1E2E`
- **Text Primary:** `#E8E8E8` (off-white)
- **Text Secondary:** `#B0B0B0`
- **Accent:** `#FFA05C` (desaturated tangerine)
- **Borders:** `#2D2D3D`

---

## Verification

1. **Toggle functionality:**
   - Click toggle in sidebar
   - Theme should switch immediately
   - State should persist during session

2. **Light mode check:**
   - Text readable (contrast 4.5:1+)
   - Cards have subtle shadows
   - Buttons clearly visible

3. **Dark mode check:**
   - No pure black backgrounds
   - No pure white text
   - Orange accent visible but not harsh
   - Alerts readable with proper contrast

4. **Test pages:**
   - Dashboard (metrics, charts)
   - Reference Data (tables, tabs)
   - Scheduler (forms, buttons)

---

## Sources

- [Streamlit Theming Docs](https://docs.streamlit.io/develop/concepts/configuration/theming)
- [Streamlit Toggle Solution](https://discuss.streamlit.io/t/changing-the-streamlit-theme-with-a-toggle-button-solution/56842)
- [WCAG Color Contrast Guide 2025](https://www.allaccessible.org/blog/color-contrast-accessibility-wcag-guide-2025)
- [Inclusive Dark Mode Design - Smashing Magazine](https://www.smashingmagazine.com/2025/04/inclusive-dark-mode-designing-accessible-dark-themes/)
