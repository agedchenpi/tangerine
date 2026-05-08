"""
Fetch and store today's Far Side daily comics.

Scrapes thefarside.com for a given date (default: today), downloads
comic images, and inserts metadata into feeds.tfarside.

Usage:
    python -m etl.jobs.run_farside_daily
    python -m etl.jobs.run_farside_daily --date 2026-05-06
    python -m etl.jobs.run_farside_daily --dry-run
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from common.db_utils import db_transaction
from common.logging_utils import get_logger
from etl.base.import_utils import save_json, audit_cols, JobRunLogger
from etl.clients.farside_client import FarSideClient

CONFIG_NAME = "FarSide_Daily"
IMAGE_DIR = Path("/app/data/images/farside")

logger = get_logger("run_farside_daily")


def scrape_and_store(target_date: str, dry_run: bool, job_log: JobRunLogger) -> int:
    """Scrape a single date, download images, insert to DB.

    Returns 0 on success, 1 on failure.
    """
    step_id = job_log.begin_step("data_collection", "Scrape & Download")
    try:
        client = FarSideClient()
        try:
            comics = client.scrape_date(target_date)
        finally:
            client.close()

        if not comics:
            job_log.complete_step(step_id, records_in=0, records_out=0,
                                  message=f"No comics found for {target_date}")
            return 0

        date_compact = target_date.replace("-", "")
        now = datetime.now().isoformat()

        for comic in comics:
            filename = f"farside_{date_compact}_{comic['position']}.jpg"
            comic["local_filename"] = filename
            comic["comic_date"] = target_date
            comic["created_date"] = now
            comic["created_by"] = "etl_user"

            if not dry_run:
                dest = IMAGE_DIR / filename
                if not dest.exists():
                    client2 = FarSideClient()
                    try:
                        client2.download_image(comic["image_url"], dest)
                    finally:
                        client2.close()
                    logger.info(f"Downloaded {filename}")

        save_json(comics, CONFIG_NAME, source="farside")
        job_log.complete_step(step_id, records_in=len(comics), records_out=len(comics))

    except Exception as e:
        job_log.fail_step(step_id, str(e))
        logger.error(f"Scrape failed for {target_date}: {e}")
        return 1

    if dry_run:
        logger.info(f"Dry run — skipping DB insert for {target_date}")
        return 0

    # DB insert
    step_id = job_log.begin_step("db_import", "Database Insert")
    try:
        inserted = 0
        with db_transaction(dict_cursor=False) as cursor:
            for comic in comics:
                cursor.execute(
                    """INSERT INTO feeds.tfarside
                       (comic_date, position, image_url, alt_text, caption,
                        local_filename, created_date, created_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (comic_date, position) DO NOTHING""",
                    (
                        comic["comic_date"],
                        comic["position"],
                        comic["image_url"],
                        comic.get("alt_text"),
                        comic.get("caption"),
                        comic["local_filename"],
                        comic["created_date"],
                        comic["created_by"],
                    ),
                )
                inserted += cursor.rowcount
        job_log.complete_step(step_id, records_in=len(comics), records_out=inserted)
        logger.info(f"Inserted {inserted} comics for {target_date}")
    except Exception as e:
        job_log.fail_step(step_id, str(e))
        logger.error(f"DB insert failed for {target_date}: {e}")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="Fetch Far Side daily comics")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Date to scrape (YYYY-MM-DD, default: today)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scrape and save JSON but skip DB insert and image download")
    args = parser.parse_args()

    with JobRunLogger("run_farside_daily", CONFIG_NAME, args.dry_run) as job_log:
        return scrape_and_store(args.date, args.dry_run, job_log)


if __name__ == "__main__":
    sys.exit(main())
