# Fix Disconnected Database + Add Streamlit Recovery UI

## Context

`tangerine-db-1` (postgres:18) has been in `Exited (0)` state since 2026-05-10 19:42 UTC — a clean shutdown (`fast shutdown request` in the logs), not a crash. No data corruption is expected. While the DB is down, the `tangerine` and `pubsub` containers show `unhealthy` because their health checks can't reach the DB; the `admin` Streamlit is still up on port 8501 but `home.py:18` shows "Database: Disconnected."

This plan does two things:
1. **Immediate fix**: bring the DB back up so the stack is healthy again.
2. **Self-service recovery**: add a "🔌 Services" tab to the existing **Server Health** page (`admin/pages/server_monitor.py`) so this can be done from the UI next time, without shelling into the host.

## Immediate fix (one-time, manual)

Run from `/opt/tangerine` (host shell, requires user approval since it affects shared infra):

```bash
docker compose up -d db
# wait for healthy
docker compose ps
# tangerine + pubsub are restart:unless-stopped and depends_on db healthy,
# so they should self-recover. If not:
docker compose up -d tangerine pubsub
```

Verify by reloading the admin Home page — the "Database" stat card should flip to green/Connected.

## Streamlit recovery UI

### Files to modify

- **`admin/services/server_monitor_service.py`** — add 3 helper functions (Docker SDK; already has `_docker_client()` at line 147).
- **`admin/pages/server_monitor.py`** — add a 7th tab `🔌 Services` to the existing `st.tabs(...)` call at line 150.

### Service-layer additions (`server_monitor_service.py`)

Append after `run_docker_cleanup()` (~line 255). All three reuse the existing `_docker_client()` helper. The compose project label is `com.docker.compose.project=tangerine` (confirmed by container names `tangerine-*`).

```python
COMPOSE_PROJECT = "tangerine"
COMPOSE_SERVICES = ["db", "tangerine", "pubsub", "admin"]


def get_compose_services() -> list[dict]:
    """Return one row per tangerine-* container: service, name, state, status, health."""
    try:
        client = _docker_client()
        rows = []
        for c in client.containers.list(all=True,
                                         filters={"label": f"com.docker.compose.project={COMPOSE_PROJECT}"}):
            state = c.attrs.get("State", {})
            rows.append({
                "service": c.labels.get("com.docker.compose.service", c.name),
                "name": c.name,
                "state": state.get("Status", ""),
                "health": (state.get("Health") or {}).get("Status", "—"),
                "started_at": state.get("StartedAt", ""),
            })
        rows.sort(key=lambda r: COMPOSE_SERVICES.index(r["service"])
                  if r["service"] in COMPOSE_SERVICES else 99)
        return rows
    except Exception:
        return []


def start_compose_service(service: str) -> dict:
    """Start a single stopped compose service by its short name (e.g. 'db')."""
    try:
        client = _docker_client()
        name = f"{COMPOSE_PROJECT}-{service}-1"
        container = client.containers.get(name)
        container.start()
        return {"success": True, "output": f"Started {name}", "error": ""}
    except Exception as exc:
        return {"success": False, "output": "", "error": str(exc)}


def compose_up_all() -> dict:
    """Equivalent of `docker compose up -d` — start every stopped tangerine-* container."""
    started, failed = [], []
    for svc in COMPOSE_SERVICES:
        try:
            client = _docker_client()
            container = client.containers.get(f"{COMPOSE_PROJECT}-{svc}-1")
            if container.status != "running":
                container.start()
                started.append(svc)
        except Exception as exc:
            failed.append(f"{svc}: {exc}")
    if failed:
        return {"success": False, "output": f"Started: {started}", "error": "; ".join(failed)}
    return {"success": True, "output": f"Started: {started or 'all already running'}", "error": ""}
```

Note: we use `client.containers.get(...).start()` rather than shelling out to `docker compose`. The compose CLI isn't guaranteed inside the admin image, but the Docker socket is mounted (`docker-compose.yml:69`) and the SDK works — same pattern as the existing `run_docker_cleanup`. Starting the existing exited container is equivalent to `compose up -d` for that service because the container already has the right config attached.

### UI tab (`server_monitor.py`)

Modify the `st.tabs(...)` call at line 150 to add `"🔌 Services"`:

```python
tab_overview, tab_cpu, tab_mem, tab_disk, tab_net, tab_docker, tab_services, tab_cleanup = st.tabs([
    "📊 Overview", "🖥️ CPU", "🧠 Memory", "💾 Disk", "🌐 Network", "🐳 Docker", "🔌 Services", "🧹 Cleanup"
])
```

Add imports at the top alongside other service_monitor_service imports:

```python
from services.server_monitor_service import (
    ...,
    compose_up_all,
    get_compose_services,
    start_compose_service,
)
from common.db_utils import test_connection
```

Then implement the tab block (insert before `# ── Cleanup`):

```python
with tab_services:
    st.subheader("Tangerine Stack Services")
    rows = get_compose_services()

    # DB connectivity probe
    try:
        db_ok = test_connection()
    except Exception:
        db_ok = False
    if db_ok:
        show_success("Database connection: OK")
    else:
        show_error("Database connection: **disconnected** — start the `db` service below.")

    if not rows:
        render_info_box("No services found", "Could not list tangerine-* containers via Docker.", box_type="warning")
    else:
        # Primary: Start Database (only shown when db is not running)
        db_row = next((r for r in rows if r["service"] == "db"), None)
        if db_row and db_row["state"] != "running":
            st.warning(f"`{db_row['name']}` is **{db_row['state']}**.")
            if st.button("🔌 Start Database", type="primary", key="start_db"):
                with st.spinner("Starting database…"):
                    r = start_compose_service("db")
                if r["success"]:
                    show_success(r["output"])
                    st.rerun()
                else:
                    show_error(f"Failed: {r['error'][:300]}")

        # Full-stack recovery
        st.divider()
        st.markdown("**↻ Full Stack Recovery** — start every stopped tangerine-* container (equivalent to `docker compose up -d`).")
        if st.button("Bring Up Stack", key="compose_up_all"):
            with st.spinner("Starting services…"):
                r = compose_up_all()
            if r["success"]:
                show_success(r["output"])
                st.rerun()
            else:
                show_error(f"Partial: {r['output']} | {r['error'][:300]}")

        st.divider()
        st.dataframe(
            pd.DataFrame(rows).rename(columns={
                "service": "Service", "name": "Container", "state": "State",
                "health": "Health", "started_at": "Started",
            }),
            hide_index=True,
            use_container_width=True,
        )
```

### Patterns reused
- `_docker_client()` — existing Docker SDK helper (`server_monitor_service.py:147`).
- `show_success` / `show_error` / `render_info_box` — already imported in `server_monitor.py`.
- `test_connection` — already used by `home.py:18`.
- Tab + button + spinner + rerun pattern — mirrors the existing Cleanup tab (`server_monitor.py:337-440`).

## Verification

1. **Confirm the immediate fix worked**:
   - `docker ps` shows `tangerine-db-1` Up (healthy) and `tangerine`/`pubsub` healthy.
   - Reload http://<host>:8501 — Home page shows "Database: Connected" (green).
2. **Exercise the new UI**:
   - Open Server Health → 🔌 Services tab. The list should show all 4 services as `running`, DB probe green.
   - Force a regression: `docker stop tangerine-db-1` → reload the tab → red banner + warning + "🔌 Start Database" button appears → click it → DB returns to running, banner flips green after rerun.
   - Click "Bring Up Stack" while everything is already running — should report "all already running" without error.
3. **Run tests** (no new tests required, but keep existing green):
   ```bash
   docker compose exec tangerine pytest tests/ -v
   ```

## Out of scope
- Per-service restart of healthy-but-misbehaving containers (user didn't select this option).
- `docker compose down` / volume management — would be destructive; current Cleanup tab already covers prune actions.
- A separate `service_recovery.py` page — folded into existing Server Health page per user preference.
