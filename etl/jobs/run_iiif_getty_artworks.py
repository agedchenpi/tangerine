"""
Fetch and import Getty Museum IIIF artwork records.

Discovers all open-content paintings via the Getty SPARQL endpoint at
data.getty.edu, then for each manifest UUID fetches the IIIF Presentation
API manifest from media.getty.edu, extracts structured artwork metadata,
downloads the full-resolution image, and imports the records into
feeds.tiiif_artwork via generic_import.

Getty provenance is NOT in the manifest — it lives in the Linked Art API
(data.getty.edu). After parsing the manifest, the job checks for a seeAlso
api_url and calls the Linked Art API to retrieve structured provenance via
`changed_ownership_through[]`.

Usage:
    python etl/jobs/run_iiif_getty_artworks.py
    python etl/jobs/run_iiif_getty_artworks.py --dry-run
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import requests

from common.db_utils import db_transaction, fetch_dict
from common.logging_utils import get_logger
from etl.base.import_utils import save_json, run_generic_import, JobRunLogger
from etl.clients.iiif_client import IIIFClient

CONFIG_NAME    = 'IIIF_Getty_Artworks'
IMAGE_DIR      = Path('/app/data/images/iiif')
MANIFEST_BASE  = 'https://media.getty.edu/iiif/manifest'
SPARQL_ENDPOINT = 'https://data.getty.edu/museum/collection/sparql'

SPARQL_QUERY = """
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>

SELECT DISTINCT ?manifest WHERE {
  ?obj a crm:E22_Human-Made_Object ;
       crm:P2_has_type <http://vocab.getty.edu/aat/300033618> ;
       crm:P67i_is_referred_to_by <http://creativecommons.org/publicdomain/zero/1.0/> ;
       crm:P129i_is_subject_of ?manifest .
  FILTER(CONTAINS(STR(?manifest), "media.getty.edu/iiif/manifest"))
}
"""

logger = get_logger('run_iiif_getty_artworks')


def discover_manifest_uuids() -> list:
    """
    Query the Getty SPARQL endpoint for all open-content painting manifests.

    POSTs a SPARQL SELECT query to data.getty.edu and extracts the UUID
    suffix from each returned manifest URL.

    Returns:
        Sorted, deduplicated list of manifest UUID strings (~768 expected).
    """
    logger.info(f"Querying SPARQL endpoint: {SPARQL_ENDPOINT}")
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
    uuids = sorted({
        row['manifest']['value'].rstrip('/').split('/')[-1]
        for row in bindings
        if row.get('manifest', {}).get('value')
    })
    logger.info(f"Discovered {len(uuids)} unique manifest UUIDs")
    return uuids


def collect_records(manifest_uuids: list, dry_run: bool) -> list:
    """
    Fetch manifests + Linked Art provenance, download images, return artwork dicts.

    Skips image download if the file already exists on disk.
    On dry-run, all image downloads are skipped and local_filename is left None.

    Args:
        manifest_uuids: List of Getty IIIF manifest UUID strings.
        dry_run: If True, skip image downloads.
    """
    records = []
    with IIIFClient() as client:
        for manifest_uuid in manifest_uuids:
            manifest_url = f"{MANIFEST_BASE}/{manifest_uuid}"
            try:
                manifest = client.get_manifest_url(manifest_url)
                record = client.parse_manifest(manifest)

                # Getty provenance lives in Linked Art API (seeAlso in manifest)
                api_url = record.get('api_url')
                if api_url:
                    linked_art = client.get_linked_art(api_url)
                    record['provenance'] = client.parse_linked_art_provenance(linked_art)
                else:
                    logger.warning(f"No seeAlso/api_url found for {manifest_uuid}; provenance will be empty")
                    record['provenance'] = []

                dest = IMAGE_DIR / f"{manifest_uuid}.jpg"
                if dry_run:
                    logger.info(f"[dry-run] Skipping image download for {manifest_uuid}")
                elif dest.exists():
                    logger.info(f"Image already exists, skipping download: {dest.name}")
                    record['local_filename'] = dest.name
                else:
                    client.download_image(record['image_url'], dest)
                    record['local_filename'] = dest.name

                records.append(record)
            except Exception as e:
                logger.error(f"Failed to process manifest {manifest_uuid}: {e}")

    logger.info(f"Collected {len(records)} artwork records")
    return records


def transform(records: list) -> list:
    """
    Strip provenance (stored separately) and add audit columns.
    Returns artwork-only dicts ready for generic_import.
    """
    now = datetime.now().isoformat()
    artwork_rows = []
    for rec in records:
        row = {k: v for k, v in rec.items() if k != 'provenance'}
        row['created_date'] = now
        row['created_by'] = 'etl_user'
        # Serialise JSONB list → JSON string for the database
        if isinstance(row.get('raw_metadata'), list):
            row['raw_metadata'] = json.dumps(row['raw_metadata'])
        artwork_rows.append(row)
    return artwork_rows


def insert_provenance(records: list, dry_run: bool) -> int:
    """
    Insert provenance rows into feeds.tiiif_provenance.

    Looks up each artwork's record_id by manifest_id, then inserts
    one row per provenance entry.  Skips silently if the artwork row
    is missing or has no provenance.

    Returns count of rows inserted.
    """
    if dry_run:
        total = sum(len(r.get('provenance', [])) for r in records)
        logger.info(f"[dry-run] Would insert {total} provenance row(s)")
        return 0

    now = datetime.now().isoformat()
    inserted = 0

    for rec in records:
        provenance = rec.get('provenance', [])
        if not provenance:
            continue

        manifest_id = rec['manifest_id']
        rows = fetch_dict(
            "SELECT record_id FROM feeds.tiiif_artwork WHERE manifest_id = %s",
            (manifest_id,)
        )
        if not rows:
            logger.warning(f"No artwork record found for manifest_id={manifest_id}; skipping provenance")
            continue

        artwork_id = rows[0]['record_id']

        for entry in provenance:
            try:
                with db_transaction(dict_cursor=False) as cur:
                    cur.execute("""
                        INSERT INTO feeds.tiiif_provenance
                            (artwork_id, sequence_order, holder_name,
                             holder_dates, location, acquisition_notes,
                             created_date, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (artwork_id, sequence_order) DO NOTHING
                    """, (
                        artwork_id,
                        entry['sequence_order'],
                        entry['holder_name'],
                        entry.get('holder_dates'),
                        entry.get('location'),
                        entry.get('acquisition_notes'),
                        now,
                        'etl_user',
                    ))
                inserted += 1
            except Exception as e:
                logger.error(f"Failed to insert provenance for {manifest_id} seq {entry['sequence_order']}: {e}")

    logger.info(f"Inserted {inserted} provenance row(s)")
    return inserted


def main():
    parser = argparse.ArgumentParser(description='Fetch and import Getty Museum IIIF artworks')
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch and save JSON but do not load to database or download images')
    args = parser.parse_args()

    with JobRunLogger('run_iiif_getty_artworks', CONFIG_NAME, args.dry_run) as job_log:
        # ── Step 1: manifest_discovery ────────────────────────────────── #
        disc_step_id = job_log.begin_step('manifest_discovery', 'SPARQL Discovery')
        try:
            manifest_uuids = discover_manifest_uuids()
            job_log.complete_step(disc_step_id, records_in=0,
                                  records_out=len(manifest_uuids))
        except Exception as e:
            job_log.fail_step(disc_step_id, str(e))
            return 1

        # ── Step 2: data_collection ───────────────────────────────────── #
        step_id = job_log.begin_step('data_collection', 'Manifest Fetch')
        try:
            raw_records = collect_records(manifest_uuids, args.dry_run)
            if not raw_records:
                job_log.complete_step(step_id, records_in=len(manifest_uuids),
                                      records_out=0, message="No records returned")
                return 0

            artwork_rows = transform(raw_records)
            save_json(artwork_rows, CONFIG_NAME, source='iiif')
            job_log.complete_step(step_id, records_in=len(manifest_uuids),
                                  records_out=len(artwork_rows))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        # ── Step 3: db_import (generic_import → tiiif_artwork) ──────── #
        rc = run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)
        if rc != 0:
            return rc

        # ── Step 4: provenance insert ────────────────────────────────── #
        prov_step_id = job_log.begin_step('provenance_insert', 'Provenance Insert')
        try:
            n_prov = insert_provenance(raw_records, args.dry_run)
            job_log.complete_step(prov_step_id, records_in=len(raw_records),
                                  records_out=n_prov)
        except Exception as e:
            job_log.fail_step(prov_step_id, str(e))
            return 1

        return 0


if __name__ == '__main__':
    sys.exit(main())
