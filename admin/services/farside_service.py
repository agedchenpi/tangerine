"""Service layer for Far Side gallery — database queries, no UI imports."""

from typing import Optional

from common.db_utils import fetch_dict


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
