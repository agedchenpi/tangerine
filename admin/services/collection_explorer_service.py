"""
Collection Explorer service — lightweight discovery calls for museum APIs.

Fires single API calls to discover available artworks without fetching
individual manifests or downloading images.  Results are cross-referenced
against feeds.tiiif_artwork to flag already-imported records.
"""

import os
import time

import requests

from common.db_utils import fetch_dict
from etl.jobs.run_iiif_getty_artworks import SPARQL_ENDPOINT, SPARQL_QUERY

SI_API_BASE = 'https://api.si.edu/openaccess/api/v1.0'
SI_ROWS = 1000


# ── Getty ──────────────────────────────────────────────────────────────────── #

def discover_getty_manifests() -> list[dict]:
    """
    POST SPARQL query to Getty endpoint and return manifest UUIDs + URLs.

    Returns:
        List of {"uuid": "...", "manifest_url": "https://media.getty.edu/iiif/manifest/..."}.
    """
    response = requests.post(
        SPARQL_ENDPOINT,
        data=SPARQL_QUERY,
        headers={
            'Content-Type': 'application/sparql-query',
            'Accept': 'application/sparql-results+json',
        },
        timeout=60,
    )
    response.raise_for_status()

    bindings = response.json()['results']['bindings']
    results = []
    seen = set()
    for row in bindings:
        url = row.get('manifest', {}).get('value', '').rstrip('/')
        if not url:
            continue
        uuid = url.split('/')[-1]
        if uuid not in seen:
            seen.add(uuid)
            results.append({'uuid': uuid, 'manifest_url': url})

    return sorted(results, key=lambda r: r['uuid'])


# ── Smithsonian ────────────────────────────────────────────────────────────── #

def discover_smithsonian_artworks(
    query: str = 'unit_code:FSG AND object_type:Paintings AND place:China',
    max_rows: int = 500,
) -> list[dict]:
    """
    Paginate the Smithsonian Open Access API and return lightweight artwork metadata.

    Does NOT fetch individual IIIF manifests — only the search result fields.

    Args:
        query:    SI API freetext query string.
        max_rows: Cap on total records to retrieve (avoids runaway pagination).

    Returns:
        List of {"manifest_id", "title", "object_type", "date", "media_count"}.
    """
    api_key = os.getenv('SI_API_KEY', 'DEMO_KEY')
    session = requests.Session()
    session.headers.update({'User-Agent': 'Tangerine-ETL/1.0'})

    results: list[dict] = []
    start = 0

    while len(results) < max_rows:
        rows_to_fetch = min(SI_ROWS, max_rows - len(results))
        params = {
            'q':       query,
            'rows':    rows_to_fetch,
            'start':   start,
            'api_key': api_key,
        }
        resp = session.get(f'{SI_API_BASE}/search', params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        rows = data.get('response', {}).get('rows', [])
        if not rows:
            break

        for item in rows:
            descriptive = item.get('content', {}).get('descriptiveNonRepeating', {})
            media_list = (descriptive.get('online_media') or {}).get('media', [])
            ids_id = media_list[0].get('idsId') if media_list else None

            freetext = item.get('content', {}).get('freetext', {})
            date_val = None
            date_entries = freetext.get('date', [])
            if date_entries:
                date_val = date_entries[0].get('content')

            results.append({
                'manifest_id':  ids_id or '',
                'title':        item.get('title', ''),
                'object_type':  item.get('content', {}).get('indexedStructured', {}).get('object_type', [''])[0] if item.get('content', {}).get('indexedStructured', {}).get('object_type') else '',
                'date':         date_val or '',
                'media_count':  len(media_list),
            })

        total = data.get('response', {}).get('rowCount', 0)
        start += len(rows)
        if start >= total:
            break

        time.sleep(0.3)

    return results


# ── DB cross-reference ─────────────────────────────────────────────────────── #

def get_imported_manifest_ids() -> set[str]:
    """
    Return the set of manifest_ids already in feeds.tiiif_artwork.

    Used to flag discovered records as "Already Imported" vs "New".
    """
    rows = fetch_dict("SELECT DISTINCT manifest_id FROM feeds.tiiif_artwork")
    return {r['manifest_id'] for r in rows if r.get('manifest_id')}
