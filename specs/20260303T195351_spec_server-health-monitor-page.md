# Plan: Server Health Monitor Page

## Context

The admin interface has no visibility into host server resources. The user wants a dedicated
Streamlit page to monitor RAM, CPU, disk, and other system vitals in real-time. The existing
`monitoring.py` covers ETL logs/statistics — this is a separate, infrastructure-level concern.

`psutil` is not yet in requirements and must be added. `plotly` (5.18.0) is already available
for gauges and charts.

## Files to Create / Modify

| File | Action |
|------|--------|
| `requirements/admin.txt` | Add `psutil>=5.9.0` |
| `admin/services/server_monitor_service.py` | **New** — all psutil calls |
| `admin/pages/server_monitor.py` | **New** — Streamlit UI |

No changes needed to routing — Streamlit auto-discovers files in `admin/pages/`.

## Service Layer: `server_monitor_service.py`

Pure functions, no `st.*` calls. Returns plain dicts/lists.

```python
def get_cpu_info() -> dict
    # overall_pct, per_core (list), freq_current, freq_max, load_avg (1/5/15m), logical_count, physical_count

def get_memory_info() -> dict
    # ram: total, used, free, available, pct
    # swap: total, used, free, pct

def get_disk_info() -> list[dict]
    # per partition: device, mountpoint, fstype, total, used, free, pct

def get_network_info() -> list[dict]
    # per interface: name, bytes_sent, bytes_recv, packets_sent, packets_recv, errin, errout

def get_system_info() -> dict
    # hostname, platform, python_version, boot_time, uptime_str

def get_docker_containers() -> list[dict]
    # via subprocess `docker ps --format json` → name, status, image, ports, state
    # returns [] on error (Docker unavailable)
```

## Page Layout: `server_monitor.py`

### Header + Controls
```
Server Health                  [Auto-refresh ▾]  [↺ Refresh Now]
Last updated: 14:32:05
```
Auto-refresh options: Off / 10s / 30s / 60s (stored in session state, triggers `st.rerun()` via `time.sleep()`).

### Top Metric Cards (4 columns)
```
[🖥 CPU  34%]  [🧠 RAM  67%]  [💾 Disk  45%]  [⏱ Uptime 12d 4h]
```
Color logic: < 60% → `#28A745` (green), 60–80% → `#FFC107` (yellow), > 80% → `#DC3545` (red).

### Tabs
```
[📊 Overview] [🖥 CPU] [🧠 Memory] [💾 Disk] [🌐 Network] [🐳 Docker]
```

**Overview tab** — 3 Plotly gauge charts in a row (CPU %, RAM %, top disk %),
plus a system info box (hostname, OS, boot time, Python version).

**CPU tab** — Overall gauge + per-core progress bars + load average (1/5/15 min) in 3 metric widgets.

**Memory tab** — RAM gauge + table (Total / Used / Free / Available + %). Swap section below with same layout.

**Disk tab** — DataFrame table per mount point. `%` column color-coded using `st.dataframe` column config with progress bars. Units formatted via existing `format_file_size()` from `ui_helpers`.

**Network tab** — Per-interface table: bytes sent/recv (human-readable), packets, errors. Excludes loopback `lo` by default with a toggle to include it.

**Docker tab** — Table of running containers (name, image, state, status, ports). Shows "Docker unavailable" info box if subprocess fails.

## Reuse Existing Utilities

- `from utils.ui_helpers import load_custom_css, add_page_header, render_stat_card, render_info_box, render_empty_state, format_file_size`
- `from components.notifications import show_error`
- Color constants: `#28A745`, `#FFC107`, `#DC3545`, `#17A2B8`

## Color Helper (inline in service or page)

```python
def _health_color(pct: float) -> str:
    if pct >= 80: return "#DC3545"
    if pct >= 60: return "#FFC107"
    return "#28A745"
```

## Plotly Gauge Pattern (reused for CPU/RAM/Disk)

```python
import plotly.graph_objects as go

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=pct,
    number={"suffix": "%"},
    gauge={
        "axis": {"range": [0, 100]},
        "bar": {"color": color},
        "steps": [
            {"range": [0, 60], "color": "#e8f5e9"},
            {"range": [60, 80], "color": "#fff9c4"},
            {"range": [80, 100], "color": "#ffebee"},
        ],
    },
    title={"text": label},
))
fig.update_layout(height=250, margin=dict(t=40, b=0, l=20, r=20))
st.plotly_chart(fig, use_container_width=True)
```

## Auto-refresh Implementation

```python
refresh_interval = st.session_state.get("refresh_interval", 0)  # seconds, 0 = off
if refresh_interval > 0:
    time.sleep(refresh_interval)
    st.rerun()
```

## Docker Rebuild Required

After adding `psutil` to `requirements/admin.txt`:
```bash
docker compose build admin && docker compose up -d admin
```

## Verification

1. Visit `http://localhost:8501` → new "Server Health" page appears in sidebar
2. Top cards show live CPU %, RAM %, Disk %, Uptime
3. Each tab loads without error
4. Docker tab shows running containers (or graceful fallback)
5. Auto-refresh cycles the page at the selected interval
6. High-usage metrics (> 80%) display in red
