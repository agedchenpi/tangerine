"""
Backfill Far Side comics for a date range.

Iterates through each date, skipping dates already in the database,
with a configurable sleep between requests to avoid rate limiting.

Usage:
    python -m etl.jobs.run_farside_backfill --start-date 2025-01-01 --end-date 2025-03-31
    python -m etl.jobs.run_farside_backfill --start-date 2025-01-01 --sleep 3
    python -m etl.jobs.run_farside_backfill --start-date 2025-01-01 --dry-run
"""

import argparse
import sys
import time
from datetime import date, datetime, timedelta

from common.db_utils import fetch_dict
from common.logging_utils import get_logger
from etl.base.import_utils import JobRunLogger
from etl.jobs.run_farside_daily import scrape_and_store

CONFIG_NAME = "FarSide_Backfill"

logger = get_logger("run_farside_backfill")


def _existing_dates() -> set[str]:
    """Return set of date strings already in feeds.tfarside."""
    rows = fetch_dict("SELECT DISTINCT comic_date FROM feeds.tfarside")
    return {str(r["comic_date"]) for r in rows}


def main():
    parser = argparse.ArgumentParser(description="Backfill Far Side comics for a date range")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=date.today().isoformat(),
                        help="End date inclusive (YYYY-MM-DD, default: today)")
    parser.add_argument("--sleep", type=float, default=2.0,
                        help="Seconds to sleep between dates (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape and save JSON but skip DB insert and image download")
    args = parser.parse_args()

    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    if start > end:
        logger.error(f"start-date {start} is after end-date {end}")
        return 1

    total_days = (end - start).days + 1
    logger.info(f"Backfill: {start} → {end} ({total_days} days, sleep={args.sleep}s)")

    existing = set() if args.dry_run else _existing_dates()
    skipped = 0
    processed = 0
    failed = 0

    with JobRunLogger("run_farside_backfill", CONFIG_NAME, args.dry_run) as job_log:
        step_id = job_log.begin_step("backfill", "Backfill Date Range")

        current = start
        while current <= end:
            date_str = current.isoformat()

            if date_str in existing:
                skipped += 1
                current += timedelta(days=1)
                continue

            logger.info(f"[{processed + skipped + failed + 1}/{total_days}] Scraping {date_str}")

            rc = scrape_and_store(date_str, args.dry_run, job_log)
            if rc == 0:
                processed += 1
            else:
                failed += 1

            current += timedelta(days=1)

            # Sleep between dates (skip on last iteration)
            if current <= end and args.sleep > 0:
                time.sleep(args.sleep)

        msg = f"Done: {processed} scraped, {skipped} skipped, {failed} failed"
        logger.info(msg)
        job_log.complete_step(step_id, records_in=total_days, records_out=processed, message=msg)

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
