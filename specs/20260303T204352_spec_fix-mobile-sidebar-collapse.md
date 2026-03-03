# Plan: Fix Mobile Sidebar Collapse

## Context

The sidebar is not collapsible on mobile because `ui_helpers.py` injects CSS that
permanently defeats Streamlit's native collapse mechanism on ALL viewports:

1. **Forces sidebar always visible** — `[data-testid="stSidebar"][aria-expanded="false"]`
   gets `transform: none !important; margin-left: 0 !important`, preventing the sidebar
   from sliding off-screen even when Streamlit marks it as collapsed.

2. **Hides all toggle buttons** — `[data-testid="collapsedControl"]` and
   `button[kind="header"][aria-label*="Open/Close sidebar"]` are all `display: none !important`.
   Users have no button to open or close the sidebar.

3. **Our previous CSS patch** added `position: fixed; z-index: 999` to the sidebar, but the
   Streamlit header sits at a higher z-index (~1000), so the close button we styled appears
   hidden behind the header bar — exactly what the user reported.

**Goal:** Keep desktop behavior unchanged (sidebar always visible, no toggle buttons). On
mobile (≤ 768px), restore native Streamlit collapse/expand so users can dismiss the sidebar
and navigate freely.

## Root Cause Summary

| CSS rule in `ui_helpers.py` | Desktop intent | Mobile effect |
|-----------------------------|----------------|---------------|
| `stSidebar[aria-expanded=false] { transform: none }` | Keep sidebar pinned | Sidebar always blocks content |
| `stSidebar { min-width: 244px }` | Prevent shrinking | Sidebar takes full-width on small screens |
| `collapsedControl { display: none }` | Hide Streamlit's toggle | No button to open/close sidebar |

## Files to Modify

| File | Change |
|------|--------|
| `admin/utils/ui_helpers.py` | Add `@media (max-width: 768px)` overrides to un-do the forced-expand rules |
| `admin/styles/custom.css` | Fix sidebar z-index (999 → 1001), style `collapsedControl` button, remove broken orange close button |

## Change 1 — `ui_helpers.py` (lines 91–108 area)

Append a mobile override block inside the same `st.markdown` CSS injection, **after** the
existing sidebar rules:

```css
/* ── Mobile: restore native sidebar collapse (overrides desktop rules above) ── */
@media (max-width: 768px) {
    /* Allow sidebar to slide off-screen when collapsed */
    [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(-110%) !important;
        margin-left: 0 !important;
    }

    /* Remove min-width so sidebar doesn't overflow viewport */
    [data-testid="stSidebar"] {
        min-width: unset !important;
        width: 85vw !important;
        max-width: 300px !important;
    }

    /* Show the expand button (hamburger) when sidebar is closed */
    [data-testid="collapsedControl"],
    button[kind="header"][aria-label*="Open sidebar"] {
        display: flex !important;
    }

    /* Show the close button inside the open sidebar */
    button[kind="header"][aria-label*="Close sidebar"] {
        display: flex !important;
    }
}
```

## Change 2 — `custom.css` mobile section (lines 933–961)

Replace the current sidebar block with a corrected version:

```css
/* Sidebar: overlay content on mobile, above the header */
section[data-testid="stSidebar"] {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    height: 100dvh !important;
    z-index: 1001 !important;   /* above Streamlit header (~1000) */
    width: 85vw !important;
    max-width: 300px !important;
    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.3) !important;
}

/* Full-width content area regardless of sidebar state */
.main .block-container {
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}

/* Large tappable open/close button (collapsedControl + close) */
[data-testid="collapsedControl"] button,
button[kind="header"][aria-label*="Open sidebar"],
button[kind="header"][aria-label*="Close sidebar"] {
    width: 2.75rem !important;
    height: 2.75rem !important;
    min-width: 2.75rem !important;
    background: var(--tangerine-primary) !important;
    border-radius: 50% !important;
    color: white !important;
    font-size: 1.25rem !important;
    border: none !important;
    box-shadow: var(--shadow-md) !important;
}

/* Remove the old stSidebarCollapseButton override (was hidden behind header) */
[data-testid="stSidebarCollapseButton"] button {
    width: unset !important;
    height: unset !important;
    background: unset !important;
    border-radius: unset !important;
    color: unset !important;
    font-size: unset !important;
    border: unset !important;
    box-shadow: unset !important;
}
```

## Desktop Behavior (unchanged)

The desktop sidebar rules in `ui_helpers.py` (no media query) continue to:
- Force sidebar always visible
- Hide toggle buttons
- Keep sidebar at min-width 244px

The `@media (max-width: 768px)` block overrides these only on narrow viewports.

## Rebuild

```bash
docker compose build admin && docker compose up -d admin
```

## Verification

**Desktop (> 768px):**
- Sidebar always visible, no toggle buttons — same as before

**Mobile (≤ 768px):**
1. Page loads with sidebar collapsed (hidden) — full content visible
2. A tangerine circular button appears in the top-left (collapsedControl) — tap to open sidebar
3. Sidebar slides in as overlay (85vw, max 300px) — content still visible behind it
4. A tangerine circular X/close button is accessible inside or near the sidebar — tap to dismiss
5. Navigating to another page: sidebar stays closed
