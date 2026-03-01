"""Service layer for IIIF artwork and provenance data."""

from typing import List, Dict, Any, Optional
from common.db_utils import fetch_dict


def get_artworks(source: Optional[str] = None, rights: Optional[str] = None, topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return artwork records with optional filters.

    Args:
        source: 'Freer Gallery' or 'Getty Museum' or None for all
        rights: metadata_usage value to filter on (e.g. 'CC0') or None for all
        topic: substring to match against topics array, or None for all

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
