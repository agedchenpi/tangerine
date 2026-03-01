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

SI_API_BASE = 'https://api.si.edu/openaccess/api/v1.0'
SI_ROWS = 1000

GETTY_SPARQL_ENDPOINT = "https://data.getty.edu/museum/collection/sparql"

GETTY_OBJECT_TYPES = {
    "Paintings":       "300033618",
    "Drawings":        "300033973",
    "Prints":          "300041273",
    "Sculpture":       "300047090",
    "Ceramics":        "300151343",
    "Photographs":     "300046300",
    "Textiles":        "300231565",
    "Decorative Arts": "300054168",
}


# ── Getty ──────────────────────────────────────────────────────────────────── #

def _build_getty_sparql(
    object_type_aats: list[str],
    date_from: int | None,
    date_to: int | None,
    culture: str,
    medium: str,
) -> str:
    lines = [
        "PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>",
        "PREFIX aat: <http://vocab.getty.edu/aat/>",
        "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>",
        "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>",
        "",
        "SELECT DISTINCT ?manifest ?title WHERE {",
        "  ?obj a crm:E22_Human-Made_Object ;",
        "       crm:P67i_is_referred_to_by <http://creativecommons.org/publicdomain/zero/1.0/> ;",
        "       crm:P129i_is_subject_of ?manifest .",
        "  FILTER(CONTAINS(STR(?manifest), 'media.getty.edu/iiif/manifest'))",
        "",
    ]

    # Object type filter
    if len(object_type_aats) == 1:
        lines.append(f"  ?obj crm:P2_has_type <http://vocab.getty.edu/aat/{object_type_aats[0]}> .")
    else:
        values = " ".join(f"<http://vocab.getty.edu/aat/{a}>" for a in object_type_aats)
        lines += [
            f"  VALUES ?objType {{ {values} }}",
            "  ?obj crm:P2_has_type ?objType .",
        ]

    # Title (optional)
    lines += [
        "",
        "  OPTIONAL {",
        "    ?obj rdfs:label ?title .",
        "  }",
    ]

    # Date range (optional)
    if date_from or date_to:
        lines += [
            "",
            "  ?obj crm:P108i_was_produced_by ?prod .",
            "  ?prod crm:P4_has_time_span ?ts .",
        ]
        if date_from:
            lines.append(f"  ?ts crm:P82b_end_of_the_end ?endDate .")
            lines.append(f"  FILTER(?endDate >= '{date_from}-01-01'^^xsd:dateTime)")
        if date_to:
            lines.append(f"  ?ts crm:P82a_begin_of_the_begin ?startDate .")
            lines.append(f"  FILTER(?startDate <= '{date_to}-12-31'^^xsd:dateTime)")

    # Culture (optional text CONTAINS on referred_to_by linguistic statement)
    if culture:
        lines += [
            "",
            "  ?obj crm:P67i_is_referred_to_by ?cultureStmt .",
            "  ?cultureStmt crm:P2_has_type <http://vocab.getty.edu/aat/300055768> ;",
            "               crm:P190_has_symbolic_content ?cultureText .",
            f"  FILTER(CONTAINS(LCASE(STR(?cultureText)), '{culture.lower()}'))",
        ]

    # Medium (optional text CONTAINS on referred_to_by linguistic statement)
    if medium:
        lines += [
            "",
            "  ?obj crm:P67i_is_referred_to_by ?mediumStmt .",
            "  ?mediumStmt crm:P2_has_type <http://vocab.getty.edu/aat/300435429> ;",
            "              crm:P190_has_symbolic_content ?mediumText .",
            f"  FILTER(CONTAINS(LCASE(STR(?mediumText)), '{medium.lower()}'))",
        ]

    lines.append("}")
    return "\n".join(lines)


def discover_getty_manifests(
    object_type_aats: list[str] | None = None,
    date_from: int | None = None,
    date_to: int | None = None,
    culture: str = "",
    medium: str = "",
) -> list[dict]:
    """
    POST SPARQL query to Getty endpoint and return manifest UUIDs + URLs + titles.

    Args:
        object_type_aats: AAT codes for object types (defaults to ["300033618"] = paintings).
        date_from:        Earliest production year (inclusive).
        date_to:          Latest production year (inclusive).
        culture:          Text filter on production place label (case-insensitive CONTAINS).
        medium:           Text filter on material label (case-insensitive CONTAINS).

    Returns:
        List of {"uuid": "...", "manifest_url": "https://...", "title": "..."}.
    """
    if not object_type_aats:
        object_type_aats = ["300033618"]

    query = _build_getty_sparql(object_type_aats, date_from, date_to, culture, medium)

    response = requests.post(
        GETTY_SPARQL_ENDPOINT,
        data=query,
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
            title = row.get('title', {}).get('value', '')
            results.append({'uuid': uuid, 'manifest_url': url, 'title': title})

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
