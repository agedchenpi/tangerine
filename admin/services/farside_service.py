"""Service layer for Far Side gallery — database queries and scrape triggers."""

import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from common.db_utils import db_transaction, fetch_dict
from common.logging_utils import get_logger

logger = get_logger("farside_service")

IMAGE_DIR = Path("/app/data/images/farside")


def get_comics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return comics matching filters, newest first."""
    conditions = []
    params = []

    if date_from:
        conditions.append("comic_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("comic_date <= %s")
        params.append(date_to)
    if search:
        conditions.append("(alt_text ILIKE %s OR caption ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT farside_id, comic_date, position, image_url,
               alt_text, caption, local_filename
        FROM feeds.tfarside
        {where}
        ORDER BY comic_date DESC, position ASC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    return fetch_dict(query, tuple(params))


def get_comic_count(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
) -> int:
    """Return total count of comics matching filters."""
    conditions = []
    params = []

    if date_from:
        conditions.append("comic_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("comic_date <= %s")
        params.append(date_to)
    if search:
        conditions.append("(alt_text ILIKE %s OR caption ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"SELECT COUNT(*) AS cnt FROM feeds.tfarside {where}"
    rows = fetch_dict(query, tuple(params))
    return rows[0]["cnt"] if rows else 0


def get_date_range() -> dict:
    """Return min and max comic_date in the collection."""
    rows = fetch_dict(
        "SELECT MIN(comic_date) AS min_date, MAX(comic_date) AS max_date FROM feeds.tfarside"
    )
    if rows and rows[0]["min_date"]:
        return {"min_date": rows[0]["min_date"], "max_date": rows[0]["max_date"]}
    return {"min_date": None, "max_date": None}


def _existing_dates() -> set[str]:
    """Return set of date strings already in feeds.tfarside."""
    rows = fetch_dict("SELECT DISTINCT comic_date FROM feeds.tfarside")
    return {str(r["comic_date"]) for r in rows}


def scrape_date(target_date: str) -> dict:
    """Scrape a single date, download images, insert to DB.

    Returns dict with keys: success, comics_added, message.
    """
    from etl.clients.farside_client import FarSideClient

    try:
        client = FarSideClient()
        try:
            comics = client.scrape_date(target_date)
        finally:
            client.close()

        if not comics:
            return {"success": True, "comics_added": 0,
                    "message": f"No comics found for {target_date}"}

        date_compact = target_date.replace("-", "")
        now = datetime.now().isoformat()

        # Download images
        for comic in comics:
            filename = f"farside_{date_compact}_{comic['position']}.jpg"
            comic["local_filename"] = filename
            dest = IMAGE_DIR / filename
            if not dest.exists():
                dl_client = FarSideClient()
                try:
                    dl_client.download_image(comic["image_url"], dest)
                finally:
                    dl_client.close()

        # DB insert
        inserted = 0
        with db_transaction(dict_cursor=False) as cursor:
            for comic in comics:
                cursor.execute(
                    """INSERT INTO feeds.tfarside
                       (comic_date, position, image_url, alt_text, caption,
                        local_filename, created_date, created_by)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (comic_date, position) DO UPDATE SET
                           image_url = EXCLUDED.image_url,
                           alt_text = EXCLUDED.alt_text,
                           caption = EXCLUDED.caption,
                           local_filename = EXCLUDED.local_filename""",
                    (
                        target_date, comic["position"], comic["image_url"],
                        comic.get("alt_text"), comic.get("caption"),
                        comic["local_filename"], now, "etl_user",
                    ),
                )
                inserted += cursor.rowcount

        return {"success": True, "comics_added": inserted,
                "message": f"{inserted} comics for {target_date}"}

    except Exception as e:
        logger.error(f"Scrape failed for {target_date}: {e}")
        return {"success": False, "comics_added": 0, "message": str(e)}


def scrape_range(start_date: str, end_date: str, sleep_secs: float = 2.0,
                 progress_callback=None) -> dict:
    """Scrape a range of dates, skipping existing ones.

    Args:
        progress_callback: Optional callable(current_idx, total, date_str, result)

    Returns dict with keys: success, total, scraped, skipped, failed.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    existing = _existing_dates()

    total = (end - start).days + 1
    scraped = 0
    skipped = 0
    failed = 0

    current = start
    idx = 0
    while current <= end:
        ds = current.isoformat()
        idx += 1

        if ds in existing:
            skipped += 1
            current += timedelta(days=1)
            if progress_callback:
                progress_callback(idx, total, ds, {"skipped": True})
            continue

        result = scrape_date(ds)
        if result["success"]:
            scraped += 1
        else:
            failed += 1

        if progress_callback:
            progress_callback(idx, total, ds, result)

        current += timedelta(days=1)
        if current <= end and sleep_secs > 0:
            time.sleep(sleep_secs)

    return {"success": failed == 0, "total": total,
            "scraped": scraped, "skipped": skipped, "failed": failed}
