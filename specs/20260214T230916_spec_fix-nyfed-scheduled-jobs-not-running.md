# Fix NYFed Scheduled Jobs Not Running

## Context

NYFed rate datasets stopped updating after 2/08. The scheduler jobs are configured in `dba.tscheduler` and `generate_crontab.py` can build a crontab from them, but **the `tangerine` container has no cron daemon installed or running**. The base image `python:3.11-slim` doesn't include cron, and the container's CMD is just `tail -f /dev/null`. So even if a crontab is applied, nothing executes it.

**Root cause:** No cron daemon in the tangerine container. The scheduling infrastructure (database config, crontab generator, admin UI) all exist, but there's no runtime to actually trigger jobs on schedule.

## Changes

### 1. Install cron and add entrypoint script to `Dockerfile`
**File:** `/opt/tangerine/Dockerfile`
- Add `apt-get install -y cron` to the image
- Create an entrypoint script that:
  1. Starts the cron daemon (`cron`)
  2. Generates and applies the crontab from the database (`generate_crontab.py --apply --update-next-run`)
  3. Falls back to `tail -f /dev/null` to keep the container alive (or exec's the original CMD)

### 2. Add entrypoint script
**New file:** `/opt/tangerine/scripts/entrypoint.sh`
```bash
#!/bin/bash
set -e

# Start cron daemon
service cron start

# Wait for database to be ready, then generate and apply crontab
python /app/etl/jobs/generate_crontab.py --apply --update-next-run || echo "Warning: crontab generation failed, will retry manually"

# Keep container running
exec tail -f /dev/null
```

### 3. Update `docker-compose.yml` for tangerine service
**File:** `/opt/tangerine/docker-compose.yml`
- Add `restart: unless-stopped` to the tangerine service (matches admin and pubsub services)

## Verification

1. `docker compose build tangerine` — rebuild the image
2. `docker compose up -d tangerine` — restart the container
3. `docker compose exec tangerine crontab -l` — confirm crontab is installed with NYFed jobs
4. `docker compose exec tangerine service cron status` — confirm cron daemon is running
5. Check the admin scheduler UI to confirm `next_run_at` timestamps are populated
6. Monitor `/app/logs/cron.log` for job execution at the next scheduled time
