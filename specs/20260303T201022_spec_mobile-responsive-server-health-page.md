# Plan: Mobile-Responsive Server Health Page

## Context

The server monitor page was built with fixed multi-column Streamlit layouts that look fine on
desktop but are cramped or unreadable on mobile browsers. The page uses `st.columns()` heavily
(4-col metric cards, 3-col gauges, [1,2] gauge+table pairs, [4,2,1] header controls, [1,8,1]
per-core bars). On mobile, these columns squeeze together rather than stacking.

Streamlit's built-in CSS uses flexbox for columns but doesn't stack them on narrow viewports
by default — it requires explicit `@media` overrides. The `custom.css` file has only one
minimal breakpoint (768px) that adjusts font sizes and padding but doesn't stack columns.

## Approach: CSS Media Queries + Per-Core Bar Redesign

Inject page-specific responsive CSS via `st.markdown()` in `server_monitor.py`. This avoids
touching shared `custom.css` and keeps the fix scoped to this page.

Two targeted changes alongside CSS:
1. Redesign the per-core progress bars section to avoid `st.columns([1, 8, 1])` — replace
   with a clean HTML+CSS layout rendered via `st.markdown()` so it doesn't depend on column
   stacking behavior.
2. Restructure the refresh controls from `[4, 2, 1]` columns to a two-row layout: header text
   on its own line, then selectbox + button side-by-side in `[3, 1]`.

## Files to Modify

| File | Change |
|------|--------|
| `admin/pages/server_monitor.py` | Add mobile CSS injection, redesign per-core bars, restructure refresh controls |

No changes to `custom.css`, `app.py`, or service layer.

## CSS Injection (add near top of page, after `load_custom_css()`)

```python
st.markdown("""
<style>
@media (max-width: 768px) {
    /* Stack all Streamlit columns vertically */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="column"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
        width: 100% !important;
    }
    /* Shrink gauge charts on mobile */
    .js-plotly-plot .plot-container {
        max-height: 200px;
    }
    /* Compact tab labels */
    .stTabs [data-baseweb="tab"] {
        padding: 0.4rem 0.6rem !important;
        font-size: 0.78rem !important;
    }
    /* Reduce page header size */
    h1 { font-size: 1.6rem !important; }
}
@media (max-width: 480px) {
    .stTabs [data-baseweb="tab"] {
        padding: 0.3rem 0.4rem !important;
        font-size: 0.72rem !important;
    }
}
</style>
""", unsafe_allow_html=True)
```

## Refresh Controls Restructure

**Before:** `st.columns([4, 2, 1])` — all three elements side-by-side.

**After:** header caption on one line, then selectbox + button in `st.columns([3, 1])`:

```python
def _refresh_controls():
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    col_interval, col_btn = st.columns([3, 1])
    with col_interval:
        interval_label = st.selectbox(
            "Auto-refresh interval",
            ["Off", "10s", "30s", "60s"],
            key="refresh_interval_label",
            label_visibility="visible",
        )
        ...
    with col_btn:
        st.write("")  # vertical alignment spacer
        if st.button("↺ Refresh", use_container_width=True):
            st.rerun()
```

## Per-Core Progress Bars Redesign

**Before:** `st.columns([1, 8, 1])` per core — 3 columns with label, bar, percentage.

**After:** Single-column HTML rows with label + inline progress bar styled via CSS:

```python
st.subheader("Per-Core Usage")
rows_html = ""
for i, pct in enumerate(cpu["per_core"]):
    color = _health_color(pct)
    rows_html += f"""
    <div style="margin-bottom:0.5rem;">
        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:2px;">
            <span>Core {i}</span><span style="color:{color};font-weight:600;">{pct:.0f}%</span>
        </div>
        <div style="background:#e9ecef; border-radius:4px; height:8px; overflow:hidden;">
            <div style="width:{pct:.0f}%; background:{color}; height:100%; border-radius:4px;"></div>
        </div>
    </div>"""
st.markdown(rows_html, unsafe_allow_html=True)
```

This renders identically on desktop and mobile — no stacking needed.

## Gauge Height on Mobile

Plotly gauges use `height=250` — on mobile this can be too tall when stacked. The CSS rule
`max-height: 200px` on `.js-plotly-plot` reduces this. No Python change needed.

## Rebuild Required

Source is baked into the Docker image (not volume-mounted):
```bash
docker compose build admin && docker compose up -d admin
```

## Verification

1. Open `http://localhost:8501/server_monitor` on desktop — layout unchanged
2. Open on a mobile browser (or Chrome DevTools → mobile viewport ≤ 768px):
   - Top 4 metric cards stack to single column
   - 3 overview gauges stack vertically
   - CPU/Memory gauge+table pairs stack (gauge on top, table below)
   - Refresh controls show selectbox + button on one row with visible label
   - Per-core bars render cleanly as stacked HTML rows
   - All tabs remain accessible (may scroll horizontally — Streamlit handles this)
3. No layout errors in Docker logs
