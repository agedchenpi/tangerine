# Plan: Daily Database Backup Job

## Context
No automated database backups exist. The project has `drop_database.sh` and `rebuild_database.sh`
with ad-hoc `pg_dump` support, but nothing runs on a schedule. This adds a daily snapshot job that
produces compressed SQL dumps, retains 7 days of history (by file date), and is managed through the
existing database-driven scheduler.

**Chosen backup time: 03:00 UTC daily**
- CoinGecko job runs at 00:05; NewYorkFed batch starts at 09:00
- 01:00–08:59 has no dedicated data jobs (only the hourly smoketest)
- 03:00 is the deepest off-hours window and avoids the smoketest at :00 each hour

**Key constraint:** `pg_dump` is NOT installed in the tangerine ETL container — only in the `db`
PostgreSQL container and on the host. We'll install `postgresql-client` in the Dockerfile so the
ETL container can call `pg_dump` directly against the `db` service over the Docker network.

---

## Files to Create / Modify

| File | Action |
|---|---|
| `Dockerfile` | Add `postgresql-client` to apt-get install |
| `docker-compose.yml` | Add `./backups:/app/backups` bind mount to `tangerine` service |
| `etl/jobs/run_database_backup.py` | New backup script |
| `schema/data/scheduler/database_backup_scheduler_job.sql` | Scheduler seed entry |

---

## Implementation

### 1. `Dockerfile` — install postgresql-client

In the existing `apt-get install` line, add `postgresql-client`:

```dockerfile
RUN apt-get update && apt-get install -y cron postgresql-client && rm -rf /var/lib/apt/lists/*
```

This makes `pg_dump` available at `/usr/bin/pg_dump` inside the container, which can connect to
`db:5432` over the Docker bridge network.

---

### 2. `docker-compose.yml` — dedicated backup volume

Add one bind-mount line to the `tangerine` service volumes:

```yaml
- ./backups:/app/backups
```

This exposes `/opt/tangerine/backups/` on the host as `/app/backups` inside the container.
Docker creates the host directory automatically on first run if it doesn't exist.

---

### 3. `etl/jobs/run_database_backup.py`

Script structure follows the standard standalone-script pattern with `JobRunLogger`.

```
CONFIG_NAME  = 'DB_Backup'
BACKUP_DIR   = Path('/app/backups')
RETAIN_DAYS  = 7
```

**Logic:**

1. Parse `--dry-run` arg (standard flag, consistent with other scripts)
2. Open `JobRunLogger('run_database_backup', CONFIG_NAME, dry_run, triggered_by)`
3. **Step 1 — `db_backup` / "Database Dump":**
   - Build output path: `BACKUP_DIR / f"tangerine_{YYYY-MM-DD}.sql.gz"`
   - Run `pg_dump` via `subprocess.run`, piping stdout through `gzip.open()` to write compressed file
   - Connection: read `DB_URL` from environment (`os.environ['DB_URL']`)
   - On dry-run: log what would be written, skip subprocess
   - `complete_step(records_out=file_size_kb)` — use KB as a meaningful "output" metric
4. **Step 2 — `retention_cleanup` / "Retention Cleanup":**
   - Glob `BACKUP_DIR / "tangerine_*.sql.gz"`
   - For each file, parse date from filename (`tangerine_YYYY-MM-DD.sql.gz`)
   - If `file_date < today - 7 days` → delete
   - On dry-run: log files that would be deleted but don't remove
   - `complete_step(records_in=total_files, records_out=deleted_count)`
5. Return 0 on success, 1 on failure

**Date-based retention detail:**
Parse the date from the filename (not mtime) using `datetime.strptime(stem, 'tangerine_%Y-%m-%d')`.
This is more reliable than mtime (which can change on file copy/rsync). A file is removed when its
filename date is strictly older than today minus 7 days.

---

### 4. `schema/data/scheduler/database_backup_scheduler_job.sql`

Seed SQL that inserts the scheduler entry (INSERT ... ON CONFLICT DO NOTHING for idempotency):

```sql
INSERT INTO dba.tscheduler (
    job_name, job_type, cron_minute, cron_hour, cron_day, cron_month, cron_weekday,
    script_path, is_active, created_at, last_modified_at
) VALUES (
    'DB_Daily_Backup', 'custom', '0', '3', '*', '*', '*',
    'etl/jobs/run_database_backup.py', TRUE,
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
) ON CONFLICT (job_name) DO NOTHING;
```

Cron expression: `0 3 * * *` — 03:00 UTC every day.

---

## Backup Output

- **Path pattern:** `/opt/tangerine/backups/tangerine_YYYY-MM-DD.sql.gz`
- **Format:** gzip-compressed plain SQL (portable, human-readable, restoreable with `psql < dump.sql`)
- **Retention:** 7 files maximum; files with a filename date older than 7 days from today are deleted
- **Dry-run:** logs what would happen, creates no files, deletes nothing

---

## Verification

1. Rebuild Docker image to confirm `pg_dump` is available:
   ```bash
   docker compose build tangerine
   docker compose exec tangerine pg_dump --version
   ```
2. Run the script manually in dry-run mode:
   ```bash
   docker compose exec tangerine python etl/jobs/run_database_backup.py --dry-run
   ```
3. Run live to create a real backup:
   ```bash
   docker compose exec tangerine python etl/jobs/run_database_backup.py
   ls -lh /opt/tangerine/backups/
   ```
4. Confirm job appears in the scheduler UI (admin → Scheduler page) after regenerating crontab
5. Confirm `tjobrun` + `tjobstep` rows are created in the database
