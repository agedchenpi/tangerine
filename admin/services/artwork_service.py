"""Service layer for IIIF artwork and provenance data."""

from typing import List, Dict, Any, Optional
from common.db_utils import fetch_dict


def get_artworks(
    source: Optional[str] = None,
    rights: Optional[str] = None,
    topic: Optional[str] = None,
    search: Optional[str] = None,
    date_text: Optional[str] = None,
    period: Optional[str] = None,
    origin: Optional[str] = None,
    artwork_type: Optional[str] = None,
    medium: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Return artwork records with optional filters.

    Args:
        source: 'Freer Gallery' or 'Getty Museum' or None for all
        rights: metadata_usage value to filter on (e.g. 'CC0') or None for all
        topic: substring to match against topics array, or None for all
        search: free-text ILIKE match across all text fields
        date_text: exact match on date_text column
        period: exact match on period column
        origin: exact match on origin column
        artwork_type: exact match on artwork_type column
        medium: exact match on medium column

    Returns:
        List of artwork dicts with all columns needed for gallery + detail view
    """
    conditions = []
    params = []

    if source == "Freer Gallery":
        conditions.append("manifest_id LIKE 'FS-%'")
    elif source == "Getty Museum":
        conditions.append("manifest_id NOT LIKE 'FS-%'")

    if rights:
        conditions.append("metadata_usage = %s")
        params.append(rights)

    if topic:
        conditions.append("%s = ANY(topics)")
        params.append(topic)

    if search:
        pattern = f"%{search}%"
        conditions.append("""(
            title             ILIKE %s
            OR artist         ILIKE %s
            OR manifest_id    ILIKE %s
            OR accession_number ILIKE %s
            OR medium         ILIKE %s
            OR period         ILIKE %s
            OR origin         ILIKE %s
            OR artwork_type   ILIKE %s
            OR date_text      ILIKE %s
        )""")
        params.extend([pattern] * 9)

    if date_text:
        conditions.append("date_text = %s")
        params.append(date_text)

    if period:
        conditions.append("period = %s")
        params.append(period)

    if origin:
        conditions.append("origin = %s")
        params.append(origin)

    if artwork_type:
        conditions.append("artwork_type = %s")
        params.append(artwork_type)

    if medium:
        conditions.append("medium = %s")
        params.append(medium)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    query = f"""
        SELECT
            record_id,
            manifest_id,
            manifest_url,
            accession_number,
            title,
            artist,
            medium,
            dimensions_text,
            date_text,
            period,
            origin,
            artwork_type,
            description,
            collection,
            data_source,
            credit_line,
            metadata_usage,
            topics,
            image_url,
            image_width,
            image_height,
            local_directory,
            local_filename,
            attribution,
            license_url
        FROM feeds.tiiif_artwork
        {where_clause}
        ORDER BY title
    """
    return fetch_dict(query, tuple(params) if params else None) or []


def get_provenance(artwork_id: int) -> List[Dict[str, Any]]:
    """
    Return ordered provenance chain for one artwork.

    Args:
        artwork_id: tiiif_artwork.record_id

    Returns:
        List of provenance dicts ordered by sequence_order
    """
    query = """
        SELECT
            provenance_id,
            sequence_order,
            holder_name,
            holder_dates,
            location,
            acquisition_notes
        FROM feeds.tiiif_provenance
        WHERE artwork_id = %s
        ORDER BY sequence_order
    """
    return fetch_dict(query, (artwork_id,)) or []


def get_distinct_periods() -> List[str]:
    """Return sorted list of distinct non-null period values."""
    query = "SELECT DISTINCT period FROM feeds.tiiif_artwork WHERE period IS NOT NULL ORDER BY period"
    result = fetch_dict(query) or []
    return [r['period'] for r in result]


def get_distinct_origins() -> List[str]:
    """Return sorted list of distinct non-null origin values."""
    query = "SELECT DISTINCT origin FROM feeds.tiiif_artwork WHERE origin IS NOT NULL ORDER BY origin"
    result = fetch_dict(query) or []
    return [r['origin'] for r in result]


def get_distinct_artwork_types() -> List[str]:
    """Return sorted list of distinct non-null artwork_type values."""
    query = "SELECT DISTINCT artwork_type FROM feeds.tiiif_artwork WHERE artwork_type IS NOT NULL ORDER BY artwork_type"
    result = fetch_dict(query) or []
    return [r['artwork_type'] for r in result]


def get_distinct_mediums() -> List[str]:
    """Return sorted list of distinct non-null medium values."""
    query = "SELECT DISTINCT medium FROM feeds.tiiif_artwork WHERE medium IS NOT NULL ORDER BY medium"
    result = fetch_dict(query) or []
    return [r['medium'] for r in result]


def get_distinct_date_texts() -> List[str]:
    """Return sorted list of distinct non-null date_text values."""
    query = "SELECT DISTINCT date_text FROM feeds.tiiif_artwork WHERE date_text IS NOT NULL ORDER BY date_text"
    result = fetch_dict(query) or []
    return [r['date_text'] for r in result]


def get_search_suggestions() -> List[Dict[str, str]]:
    """
    Return [{field, value}] rows for all searchable text values across all artworks.
    Used to populate the smart search selectbox with labelled suggestions.
    """
    query = """
        SELECT 'Title'     AS field, title           AS value FROM feeds.tiiif_artwork WHERE title IS NOT NULL
        UNION
        SELECT 'Artist'    AS field, artist           AS value FROM feeds.tiiif_artwork WHERE artist IS NOT NULL
        UNION
        SELECT 'Manifest'  AS field, manifest_id      AS value FROM feeds.tiiif_artwork WHERE manifest_id IS NOT NULL
        UNION
        SELECT 'Accession' AS field, accession_number AS value FROM feeds.tiiif_artwork WHERE accession_number IS NOT NULL
        UNION
        SELECT 'Medium'    AS field, medium            AS value FROM feeds.tiiif_artwork WHERE medium IS NOT NULL
        UNION
        SELECT 'Period'    AS field, period            AS value FROM feeds.tiiif_artwork WHERE period IS NOT NULL
        UNION
        SELECT 'Origin'    AS field, origin            AS value FROM feeds.tiiif_artwork WHERE origin IS NOT NULL
        UNION
        SELECT 'Type'      AS field, artwork_type      AS value FROM feeds.tiiif_artwork WHERE artwork_type IS NOT NULL
        UNION
        SELECT 'Date'      AS field, date_text         AS value FROM feeds.tiiif_artwork WHERE date_text IS NOT NULL
        ORDER BY field, value
    """
    return fetch_dict(query) or []


def get_artwork_topics() -> List[str]:
    """
    Return sorted list of all distinct topics across all artworks.
    """
    query = """
        SELECT DISTINCT unnest(topics) AS topic
        FROM feeds.tiiif_artwork
        WHERE topics IS NOT NULL
        ORDER BY topic
    """
    result = fetch_dict(query) or []
    return [r['topic'] for r in result]


def get_rights_values() -> List[str]:
    """
    Return sorted list of distinct metadata_usage values.
    """
    query = """
        SELECT DISTINCT metadata_usage
        FROM feeds.tiiif_artwork
        WHERE metadata_usage IS NOT NULL
        ORDER BY metadata_usage
    """
    result = fetch_dict(query) or []
    return [r['metadata_usage'] for r in result]
