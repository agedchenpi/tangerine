"""Server Health Monitor — real-time RAM, CPU, disk, and system vitals"""

import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.notifications import show_error
from services.server_monitor_service import (
    _health_color,
    get_cpu_info,
    get_disk_info,
    get_docker_containers,
    get_memory_info,
    get_network_info,
    get_system_info,
)
from utils.ui_helpers import (
    add_page_header,
    format_file_size,
    load_custom_css,
    render_info_box,
    render_stat_card,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
load_custom_css()
add_page_header("Server Health", icon="🖥️", subtitle="Real-time infrastructure vitals")

st.markdown("""
<style>
@media (max-width: 768px) {
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    [data-testid="stColumn"] {
        min-width: 100% !important;
        flex: 1 1 100% !important;
        width: 100% !important;
    }
    .js-plotly-plot .plot-container {
        max-height: 200px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.4rem 0.6rem !important;
        font-size: 0.78rem !important;
    }
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


# ---------------------------------------------------------------------------
# Auto-refresh controls
# ---------------------------------------------------------------------------
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
        interval_map = {"Off": 0, "10s": 10, "30s": 30, "60s": 60}
        st.session_state["refresh_interval"] = interval_map[interval_label]

    with col_btn:
        st.write("")  # vertical alignment spacer
        if st.button("↺ Refresh", use_container_width=True):
            st.rerun()


_refresh_controls()
st.divider()

# ---------------------------------------------------------------------------
# Collect data (once per page run)
# ---------------------------------------------------------------------------
try:
    cpu = get_cpu_info()
    mem = get_memory_info()
    disks = get_disk_info()
    sys_info = get_system_info()
except Exception as exc:
    show_error(f"Failed to collect system metrics: {exc}")
    st.stop()

# Top disk % (highest used partition)
top_disk_pct = max((d["pct"] for d in disks), default=0.0)

# ---------------------------------------------------------------------------
# Top metric cards
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_stat_card("CPU", f"{cpu['overall_pct']:.0f}%", icon="🖥️", color=_health_color(cpu["overall_pct"]))
with c2:
    render_stat_card("RAM", f"{mem['ram']['pct']:.0f}%", icon="🧠", color=_health_color(mem["ram"]["pct"]))
with c3:
    render_stat_card("Disk", f"{top_disk_pct:.0f}%", icon="💾", color=_health_color(top_disk_pct))
with c4:
    render_stat_card("Uptime", sys_info["uptime_str"], icon="⏱️", color="#17A2B8")

st.divider()

# ---------------------------------------------------------------------------
# Helper: Plotly gauge
# ---------------------------------------------------------------------------
def _gauge(label: str, pct: float, key: str = None):
    color = _health_color(pct)
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
    chart_key = key or f"gauge_{label}"
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_cpu, tab_mem, tab_disk, tab_net, tab_docker = st.tabs([
    "📊 Overview", "🖥️ CPU", "🧠 Memory", "💾 Disk", "🌐 Network", "🐳 Docker"
])

# ── Overview ────────────────────────────────────────────────────────────────
with tab_overview:
    g1, g2, g3 = st.columns(3)
    with g1:
        _gauge("CPU Usage", cpu["overall_pct"], key="overview_cpu")
    with g2:
        _gauge("RAM Usage", mem["ram"]["pct"], key="overview_ram")
    with g3:
        _gauge("Disk Usage", top_disk_pct, key="overview_disk")

    st.subheader("System Info")
    render_info_box(
        "Host Details",
        (
            f"<b>Hostname:</b> {sys_info['hostname']}<br>"
            f"<b>OS:</b> {sys_info['platform']}<br>"
            f"<b>Python:</b> {sys_info['python_version']}<br>"
            f"<b>Boot time:</b> {sys_info['boot_time']}<br>"
            f"<b>Uptime:</b> {sys_info['uptime_str']}"
        ),
        box_type="info",
    )

# ── CPU ─────────────────────────────────────────────────────────────────────
with tab_cpu:
    col_gauge, col_details = st.columns([1, 2])

    with col_gauge:
        _gauge("Overall CPU", cpu["overall_pct"], key="cpu_tab_overall")

    with col_details:
        st.subheader("Load Average")
        la1, la5, la15 = st.columns(3)
        with la1:
            st.metric("1 min", cpu["load_avg_1m"])
        with la5:
            st.metric("5 min", cpu["load_avg_5m"])
        with la15:
            st.metric("15 min", cpu["load_avg_15m"])

        st.subheader("Core Info")
        st.write(f"**Logical cores:** {cpu['logical_count']}  |  **Physical cores:** {cpu['physical_count']}")
        if cpu["freq_current"]:
            st.write(f"**Frequency:** {cpu['freq_current']:.0f} MHz (max {cpu['freq_max']:.0f} MHz)")

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

# ── Memory ──────────────────────────────────────────────────────────────────
with tab_mem:
    ram = mem["ram"]
    swap = mem["swap"]

    col_gauge, col_table = st.columns([1, 2])

    with col_gauge:
        _gauge("RAM Usage", ram["pct"], key="mem_tab_ram")

    with col_table:
        st.subheader("RAM")
        ram_df = pd.DataFrame([
            {"": "Total",     "Size": format_file_size(ram["total"])},
            {"": "Used",      "Size": format_file_size(ram["used"])},
            {"": "Free",      "Size": format_file_size(ram["free"])},
            {"": "Available", "Size": format_file_size(ram["available"])},
            {"": "Used %",    "Size": f"{ram['pct']:.1f}%"},
        ])
        st.dataframe(ram_df, hide_index=True, use_container_width=True)

    st.subheader("Swap")
    if swap["total"] == 0:
        st.info("No swap configured.")
    else:
        scol_gauge, scol_table = st.columns([1, 2])
        with scol_gauge:
            _gauge("Swap Usage", swap["pct"], key="mem_tab_swap")
        with scol_table:
            swap_df = pd.DataFrame([
                {"": "Total", "Size": format_file_size(swap["total"])},
                {"": "Used",  "Size": format_file_size(swap["used"])},
                {"": "Free",  "Size": format_file_size(swap["free"])},
                {"": "Used %", "Size": f"{swap['pct']:.1f}%"},
            ])
            st.dataframe(swap_df, hide_index=True, use_container_width=True)

# ── Disk ────────────────────────────────────────────────────────────────────
with tab_disk:
    if not disks:
        st.info("No disk partitions found.")
    else:
        disk_rows = [
            {
                "Mount": d["mountpoint"],
                "Device": d["device"],
                "FS": d["fstype"],
                "Total": format_file_size(d["total"]),
                "Used": format_file_size(d["used"]),
                "Free": format_file_size(d["free"]),
                "Used %": d["pct"],
            }
            for d in disks
        ]
        disk_df = pd.DataFrame(disk_rows)
        st.dataframe(
            disk_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Used %": st.column_config.ProgressColumn(
                    "Used %",
                    min_value=0,
                    max_value=100,
                    format="%.1f%%",
                ),
            },
        )

# ── Network ─────────────────────────────────────────────────────────────────
with tab_net:
    net_data = get_network_info()

    show_lo = st.toggle("Include loopback (lo)", value=False, key="net_show_lo")
    if not show_lo:
        net_data = [n for n in net_data if n["name"] != "lo"]

    if not net_data:
        st.info("No network interfaces found.")
    else:
        net_rows = [
            {
                "Interface": n["name"],
                "Sent": format_file_size(n["bytes_sent"]),
                "Received": format_file_size(n["bytes_recv"]),
                "Pkts Sent": n["packets_sent"],
                "Pkts Recv": n["packets_recv"],
                "Err In": n["errin"],
                "Err Out": n["errout"],
            }
            for n in net_data
        ]
        st.dataframe(pd.DataFrame(net_rows), hide_index=True, use_container_width=True)

# ── Docker ──────────────────────────────────────────────────────────────────
with tab_docker:
    containers = get_docker_containers()

    if containers is None or (isinstance(containers, list) and len(containers) == 0):
        # Try to distinguish "no containers" from "docker unavailable"
        try:
            import subprocess
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
            docker_available = result.returncode == 0
        except Exception:
            docker_available = False

        if docker_available:
            st.info("No running containers found.")
        else:
            render_info_box("Docker Unavailable", "Could not connect to Docker daemon.", box_type="warning")
    else:
        docker_rows = []
        for c in containers:
            docker_rows.append({
                "Name": c.get("Names", c.get("Name", "")),
                "Image": c.get("Image", ""),
                "State": c.get("State", ""),
                "Status": c.get("Status", ""),
                "Ports": c.get("Ports", ""),
            })
        st.dataframe(pd.DataFrame(docker_rows), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Auto-refresh loop (must be last)
# ---------------------------------------------------------------------------
refresh_interval = st.session_state.get("refresh_interval", 0)
if refresh_interval > 0:
    time.sleep(refresh_interval)
    st.rerun()
