"""
Create a compressed daily snapshot of the Tangerine PostgreSQL database.

Runs pg_dump against the db service over the Docker bridge network, writes a
gzip-compressed SQL file to /app/backups/, and prunes backups older than 7 days
by filename date.

Usage:
    python etl/jobs/run_database_backup.py
    python etl/jobs/run_database_backup.py --dry-run
"""

import argparse
import gzip
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from common.logging_utils import get_logger
from etl.base.import_utils import JobRunLogger

CONFIG_NAME = 'DB_Backup'
BACKUP_DIR = Path('/app/backups')
RETAIN_DAYS = 7

logger = get_logger('run_database_backup')


def main():
    parser = argparse.ArgumentParser(description='Create a compressed daily PostgreSQL backup')
    parser.add_argument('--dry-run', action='store_true', help='Log what would happen without writing or deleting')
    args = parser.parse_args()

    with JobRunLogger('run_database_backup', CONFIG_NAME, args.dry_run) as job_log:

        # Step 1 — Database Dump
        step_id = job_log.begin_step('db_backup', 'Database Dump')
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            output_path = BACKUP_DIR / f"tangerine_{today}.sql.gz"

            db_url = os.environ['DB_URL']

            if args.dry_run:
                logger.info(f"[dry-run] Would write backup to {output_path}")
                job_log.complete_step(step_id, records_out=0, message=f"dry-run: would write {output_path}")
            else:
                logger.info(f"Starting pg_dump → {output_path}")
                result = subprocess.run(
                    ['pg_dump', db_url],
                    capture_output=True,
                )
                if result.returncode != 0:
                    err = result.stderr.decode(errors='replace').strip()
                    raise RuntimeError(f"pg_dump failed (exit {result.returncode}): {err}")

                with gzip.open(output_path, 'wb') as gz:
                    gz.write(result.stdout)

                size_kb = output_path.stat().st_size // 1024
                logger.info(f"Backup written: {output_path} ({size_kb} KB)")
                job_log.complete_step(step_id, records_out=size_kb, message=f"{size_kb} KB → {output_path.name}")

        except Exception as e:
            job_log.fail_step(step_id, str(e))
            logger.error(f"Backup failed: {e}")
            return 1

        # Step 2 — Retention Cleanup
        step_id = job_log.begin_step('retention_cleanup', 'Retention Cleanup')
        try:
            cutoff = datetime.utcnow().date() - timedelta(days=RETAIN_DAYS)
            all_files = sorted(BACKUP_DIR.glob('tangerine_*.sql.gz'))
            deleted = 0

            for f in all_files:
                try:
                    file_date = datetime.strptime(f.stem.replace('.sql', ''), 'tangerine_%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Skipping unrecognised filename: {f.name}")
                    continue

                if file_date < cutoff:
                    if args.dry_run:
                        logger.info(f"[dry-run] Would delete {f.name} (date={file_date})")
                    else:
                        f.unlink()
                        logger.info(f"Deleted old backup: {f.name}")
                    deleted += 1

            job_log.complete_step(step_id, records_in=len(all_files), records_out=deleted)

        except Exception as e:
            job_log.fail_step(step_id, str(e))
            logger.error(f"Retention cleanup failed: {e}")
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
