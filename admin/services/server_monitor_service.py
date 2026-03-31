"""Service layer for server health monitoring — pure psutil calls, no st.* imports"""

import platform
import socket
import subprocess
import json
from datetime import datetime, timezone


def get_cpu_info() -> dict:
    """Return CPU usage stats: overall %, per-core %, frequency, load average, core counts."""
    import psutil

    overall_pct = psutil.cpu_percent(interval=0.5)
    per_core = psutil.cpu_percent(interval=None, percpu=True)

    freq = psutil.cpu_freq()
    freq_current = round(freq.current, 0) if freq else None
    freq_max = round(freq.max, 0) if freq and freq.max else None

    try:
        load_avg = [round(x, 2) for x in psutil.getloadavg()]
    except AttributeError:
        load_avg = [0.0, 0.0, 0.0]

    return {
        "overall_pct": overall_pct,
        "per_core": per_core,
        "freq_current": freq_current,
        "freq_max": freq_max,
        "load_avg_1m": load_avg[0],
        "load_avg_5m": load_avg[1],
        "load_avg_15m": load_avg[2],
        "logical_count": psutil.cpu_count(logical=True),
        "physical_count": psutil.cpu_count(logical=False),
    }


def get_memory_info() -> dict:
    """Return RAM and swap usage stats."""
    import psutil

    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "ram": {
            "total": ram.total,
            "used": ram.used,
            "free": ram.free,
            "available": ram.available,
            "pct": ram.percent,
        },
        "swap": {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "pct": swap.percent,
        },
    }


def get_disk_info() -> list[dict]:
    """Return per-partition disk usage stats.

    Keeps only meaningful mounts: the overlay root (/) and real block devices
    (/dev/*). Bind mounts of host directories are skipped — they duplicate the
    stats of the underlying host partition and clutter the view.
    """
    import psutil

    seen_devices: set[str] = set()
    partitions = []
    for part in psutil.disk_partitions(all=False):
        is_root = part.mountpoint == "/"
        is_block_device = part.device.startswith("/dev/")
        if not (is_root or is_block_device):
            continue
        if part.device in seen_devices:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        seen_devices.add(part.device)
        partitions.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "pct": usage.percent,
        })
    return partitions


def get_network_info() -> list[dict]:
    """Return per-interface network I/O counters."""
    import psutil

    stats = psutil.net_io_counters(pernic=True)
    interfaces = []
    for name, counters in stats.items():
        interfaces.append({
            "name": name,
            "bytes_sent": counters.bytes_sent,
            "bytes_recv": counters.bytes_recv,
            "packets_sent": counters.packets_sent,
            "packets_recv": counters.packets_recv,
            "errin": counters.errin,
            "errout": counters.errout,
        })
    return interfaces


def get_system_info() -> dict:
    """Return hostname, OS, Python version, boot time, and uptime string."""
    import psutil

    boot_ts = psutil.boot_time()
    boot_dt = datetime.fromtimestamp(boot_ts, tz=timezone.utc)
    uptime_secs = int((datetime.now(tz=timezone.utc) - boot_dt).total_seconds())

    days = uptime_secs // 86400
    hours = (uptime_secs % 86400) // 3600
    minutes = (uptime_secs % 3600) // 60

    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m"
    else:
        uptime_str = f"{minutes}m"

    return {
        "hostname": socket.gethostname(),
        "platform": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "boot_time": boot_dt.strftime("%Y-%m-%d %H:%M UTC"),
        "uptime_str": uptime_str,
        "uptime_days": days,
        "uptime_hours": hours,
    }


def _docker_client():
    """Return a docker.DockerClient connected via the Unix socket."""
    import docker
    return docker.from_env()


def get_docker_containers() -> list[dict]:
    """Return running Docker containers via the Docker SDK. Returns [] on error."""
    try:
        client = _docker_client()
        containers = []
        for c in client.containers.list():
            attrs = c.attrs
            containers.append({
                "Names": c.name,
                "Image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "State": attrs.get("State", {}).get("Status", ""),
                "Status": attrs.get("State", {}).get("Status", ""),
                "Ports": ", ".join(
                    f"{v[0]['HostPort']}->{k}" for k, v in (attrs.get("NetworkSettings", {}).get("Ports") or {}).items() if v
                ),
            })
        return containers
    except Exception:
        return []


def get_docker_disk_usage() -> list[dict] | None:
    """Return Docker disk usage via the SDK (GET /system/df).

    Returns a list of dicts with keys: type, total, active, size, reclaimable.
    Returns None if Docker is unavailable.
    """
    def _fmt(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.2f} {unit}" if unit != "B" else f"{n} B"
            n /= 1024
        return f"{n:.2f} PB"

    try:
        client = _docker_client()
        df = client.df()

        images      = df.get("Images") or []
        containers  = df.get("Containers") or []
        volumes     = df.get("Volumes") or []
        build_cache = df.get("BuildCache") or []

        img_size   = sum(i.get("Size", 0) for i in images)
        img_shared = sum(i.get("SharedSize", 0) for i in images)
        img_reclaimable = sum(i.get("Size", 0) for i in images if not i.get("Containers"))

        cnt_size = sum(c.get("SizeRw", 0) or 0 for c in containers)
        cnt_reclaimable = sum(c.get("SizeRw", 0) or 0 for c in containers if c.get("State") != "running")

        vol_size = sum(v.get("UsageData", {}).get("Size", 0) or 0 for v in volumes)
        vol_reclaimable = sum(v.get("UsageData", {}).get("Size", 0) or 0 for v in volumes if v.get("UsageData", {}).get("RefCount", 1) == 0)

        cache_size = sum(b.get("Size", 0) for b in build_cache)
        cache_reclaimable = sum(b.get("Size", 0) for b in build_cache if not b.get("InUse"))

        return [
            {"type": "Images",        "total": str(len(images)),      "active": str(sum(1 for i in images if i.get("Containers"))),      "size": _fmt(img_size),   "reclaimable": _fmt(img_reclaimable)},
            {"type": "Containers",    "total": str(len(containers)),   "active": str(sum(1 for c in containers if c.get("State") == "running")), "size": _fmt(cnt_size),   "reclaimable": _fmt(cnt_reclaimable)},
            {"type": "Local Volumes", "total": str(len(volumes)),      "active": str(sum(1 for v in volumes if (v.get("UsageData") or {}).get("RefCount", 0) > 0)), "size": _fmt(vol_size),   "reclaimable": _fmt(vol_reclaimable)},
            {"type": "Build Cache",   "total": str(len(build_cache)),  "active": str(sum(1 for b in build_cache if b.get("InUse"))),      "size": _fmt(cache_size), "reclaimable": _fmt(cache_reclaimable)},
        ]
    except Exception:
        return None


def run_docker_cleanup(action: str) -> dict:
    """Run a Docker cleanup via the SDK. Returns {success, output, error}.

    action: one of build_cache | images | containers | volumes | system
    """
    if action not in ("build_cache", "images", "containers", "volumes", "system"):
        return {"success": False, "output": "", "error": f"Unknown action: {action}"}
    try:
        client = _docker_client()
        parts = []

        if action in ("build_cache", "system"):
            result = client.api.prune_builds()
            reclaimed = result.get("SpaceReclaimed", 0)
            parts.append(f"Build cache: {reclaimed // 1024 // 1024} MB reclaimed")

        if action in ("containers", "system"):
            result = client.containers.prune()
            reclaimed = result.get("SpaceReclaimed", 0)
            removed = result.get("ContainersDeleted") or []
            parts.append(f"Containers: {len(removed)} removed, {reclaimed // 1024 // 1024} MB reclaimed")

        if action in ("images", "system"):
            result = client.images.prune()
            reclaimed = result.get("SpaceReclaimed", 0)
            removed = result.get("ImagesDeleted") or []
            parts.append(f"Images: {len(removed)} removed, {reclaimed // 1024 // 1024} MB reclaimed")

        if action == "volumes":
            result = client.volumes.prune()
            reclaimed = result.get("SpaceReclaimed", 0)
            removed = result.get("VolumesDeleted") or []
            parts.append(f"Volumes: {len(removed)} removed, {reclaimed // 1024 // 1024} MB reclaimed")

        return {"success": True, "output": " | ".join(parts) if parts else "Done.", "error": ""}
    except Exception as exc:
        return {"success": False, "output": "", "error": str(exc)}


def _health_color(pct: float) -> str:
    """Map a usage percentage to a traffic-light color."""
    if pct >= 80:
        return "#DC3545"
    if pct >= 60:
        return "#FFC107"
    return "#28A745"
