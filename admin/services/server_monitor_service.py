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


def get_docker_containers() -> list[dict]:
    """Return running Docker containers via `docker ps --format json`. Returns [] on error."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return []

        containers = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return containers
    except Exception:
        return []


def _health_color(pct: float) -> str:
    """Map a usage percentage to a traffic-light color."""
    if pct >= 80:
        return "#DC3545"
    if pct >= 60:
        return "#FFC107"
    return "#28A745"
