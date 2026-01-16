---
name: logs
description: View Docker service logs
---

# Logs Command

View logs from Tangerine Docker services.

## Usage

Parse arguments to determine which service logs to show:

| Argument | Service | Description |
|----------|---------|-------------|
| (none) | all | Show logs from all services |
| `admin` | admin | Streamlit admin interface |
| `tangerine` | tangerine | ETL container |
| `db` | db | PostgreSQL database |
| `pubsub` | pubsub | Pub/sub event daemon |

## Commands

### All Services (Last 50 Lines)
```bash
docker compose logs --tail 50
```

### Follow Logs (Real-time)
```bash
docker compose logs -f {service}
```

### Admin Service
```bash
docker compose logs -f admin --tail 100
```

### ETL Container
```bash
docker compose logs -f tangerine --tail 100
```

### Database
```bash
docker compose logs -f db --tail 50
```

### Pub/Sub Daemon
```bash
docker compose logs -f pubsub --tail 100
```

### With Timestamps
```bash
docker compose logs -f --timestamps {service}
```

## Examples

- `/logs` → Last 50 lines from all services
- `/logs admin` → Admin interface logs (Streamlit)
- `/logs tangerine` → ETL job execution logs
- `/logs db` → PostgreSQL logs
- `/logs pubsub` → Event system daemon logs

## Troubleshooting

### Service Won't Start
```bash
docker compose ps          # Check service status
docker compose logs {svc}  # Check startup errors
```

### Database Connection Issues
```bash
docker compose logs db     # Check PostgreSQL logs
docker compose exec db pg_isready  # Check if accepting connections
```

### Job Execution Failures
```bash
docker compose logs tangerine --tail 200  # Recent ETL logs
```

## Notes

- Use `-f` flag to follow logs in real-time
- Use `--tail N` to limit output to last N lines
- Logs are also written to `dba.tlogentry` table for ETL jobs
- Check the Monitoring page in admin UI for structured log viewing
