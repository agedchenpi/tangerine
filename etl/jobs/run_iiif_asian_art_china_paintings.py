"""
Fetch and import Smithsonian National Museum of Asian Art — Chinese Paintings.

Discovers manifest IDs dynamically via the Smithsonian Open Access API, then
fetches each IIIF manifest, downloads the full-resolution image, and imports
records into feeds.tiiif_artwork via generic_import.  Provenance rows are
inserted separately into feeds.tiiif_provenance after the main import.

Discovery query:
    unit_code:FSG AND object_type:Paintings AND place:China
    ~585 records expected (FSG = Freer|Sackler Galleries)

Usage:
    python etl/jobs/run_iiif_asian_art_china_paintings.py
    python etl/jobs/run_iiif_asian_art_china_paintings.py --dry-run
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import os

import requests

from common.db_utils import db_transaction, fetch_dict
from common.logging_utils import get_logger
from etl.base.import_utils import save_json, run_generic_import, JobRunLogger, audit_cols
from etl.clients.iiif_client import IIIFClient

CONFIG_NAME = 'IIIF_AsianArt_China_Paintings'
IMAGE_DIR   = Path('/app/data/images/iiif')

SI_API_BASE = 'https://api.si.edu/openaccess/api/v1.0'
SI_API_KEY  = os.environ.get('SI_API_KEY', 'DEMO_KEY')
SI_ROWS     = 1000          # max results per page

logger = get_logger('run_iiif_asian_art_china_paintings')


# ──────────────────────────────────────────────────────────────────────────── #
# Discovery                                                                    #
# ──────────────────────────────────────────────────────────────────────────── #

def discover_manifest_ids() -> list[str]:
    """
    Paginate the Smithsonian Open Access API to collect all IIIF manifest IDs
    for Chinese paintings from the Freer|Sackler Galleries (unit_code FSG).

    Each result item's online_media.media[0].idsId is the manifest ID used by
    IIIFClient.get_manifest().  Items without online_media are skipped.

    Returns:
        Sorted, deduplicated list of manifest ID strings.
    """
    manifest_ids: list[str] = []
    start = 0
    session = requests.Session()
    session.headers.update({'User-Agent': 'Tangerine-ETL/1.0'})

    while True:
        params = {
            'q':       'unit_code:FSG AND object_type:Paintings AND place:China',
            'rows':    SI_ROWS,
            'start':   start,
            'api_key': SI_API_KEY,
        }
        logger.info(f"SI API discovery: start={start}, rows={SI_ROWS}")
        resp = session.get(f'{SI_API_BASE}/search', params=params, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        rows = data.get('response', {}).get('rows', [])
        if not rows:
            break

        for item in rows:
            descriptive = item.get('content', {}).get('descriptiveNonRepeating', {})
            media = (descriptive.get('online_media') or {}).get('media', [])
            if not media:
                continue
            ids_id = media[0].get('idsId')
            if ids_id:
                manifest_ids.append(ids_id)

        total = data.get('response', {}).get('rowCount', 0)
        logger.info(f"  Page collected {len(rows)} items, total available: {total}")

        start += SI_ROWS
        if start >= total:
            break

        time.sleep(0.5)   # courtesy pause between discovery pages

    manifest_ids = sorted(set(manifest_ids))
    logger.info(f"Discovered {len(manifest_ids)} unique manifest IDs")
    return manifest_ids


# ──────────────────────────────────────────────────────────────────────────── #
# Collection                                                                   #
# ──────────────────────────────────────────────────────────────────────────── #

def collect_records(manifest_ids: list[str], dry_run: bool) -> list:
    """
    Fetch manifests, download images, and return list of artwork dicts.

    Skips image download if the destination file already exists.
    On dry-run, image download is skipped entirely.

    Args:
        manifest_ids: List of IIIF manifest IDs to process.
        dry_run:      If True, skip image downloads and DB writes.

    Returns:
        List of artwork record dicts (including 'provenance' key).
    """
    records = []
    with IIIFClient() as client:
        for manifest_id in manifest_ids:
            try:
                manifest = client.get_manifest(manifest_id)
                record = client.parse_manifest(manifest)

                if not dry_run:
                    dest = IMAGE_DIR / f"{manifest_id}.jpg"
                    if dest.exists():
                        logger.info(f"Image already exists, skipping download: {dest.name}")
                        record['local_filename'] = dest.name
                    else:
                        client.download_image(record['image_url'], dest)
                        record['local_filename'] = dest.name
                else:
                    logger.info(f"[dry-run] Skipping image download for {manifest_id}")

                records.append(record)
            except Exception as e:
                logger.error(f"Failed to process manifest {manifest_id}: {e}")

    logger.info(f"Collected {len(records)} artwork records from {len(manifest_ids)} manifest IDs")
    return records


# ──────────────────────────────────────────────────────────────────────────── #
# Transform                                                                    #
# ──────────────────────────────────────────────────────────────────────────── #

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
        if isinstance(row.get('raw_metadata'), list):
            row['raw_metadata'] = json.dumps(row['raw_metadata'])
        artwork_rows.append(row)
    return artwork_rows


# ──────────────────────────────────────────────────────────────────────────── #
# Provenance insert                                                             #
# ──────────────────────────────────────────────────────────────────────────── #

def insert_provenance(records: list, dry_run: bool) -> int:
    """
    Insert provenance rows into feeds.tiiif_provenance.

    Looks up each artwork's record_id by manifest_id, then inserts one row per
    provenance entry.  Skips silently if the artwork row is missing or has no
    provenance.

    Returns:
        Count of rows inserted.
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


# ──────────────────────────────────────────────────────────────────────────── #
# Entry point                                                                   #
# ──────────────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(
        description='Fetch and import Asian Art Museum Chinese paintings via IIIF'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch and save JSON but do not load to database or download images')
    args = parser.parse_args()

    with JobRunLogger('run_iiif_asian_art_china_paintings', CONFIG_NAME, args.dry_run) as job_log:

        # ── Step 1: manifest_discovery ─────────────────────────────────── #
        disc_step_id = job_log.begin_step('manifest_discovery', 'SI API Discovery')
        try:
            manifest_ids = discover_manifest_ids()
            if not manifest_ids:
                job_log.fail_step(disc_step_id, "Discovery returned 0 manifest IDs")
                return 1
            job_log.complete_step(disc_step_id, records_in=0, records_out=len(manifest_ids))
        except Exception as e:
            job_log.fail_step(disc_step_id, str(e))
            return 1

        # ── Step 2: data_collection ────────────────────────────────────── #
        step_id = job_log.begin_step('data_collection', 'Manifest Fetch')
        try:
            raw_records = collect_records(manifest_ids, args.dry_run)
            if not raw_records:
                job_log.complete_step(step_id, records_in=len(manifest_ids),
                                      records_out=0, message="No records returned")
                return 0

            artwork_rows = transform(raw_records)
            save_json(artwork_rows, CONFIG_NAME, source='iiif')
            job_log.complete_step(step_id, records_in=len(manifest_ids),
                                  records_out=len(artwork_rows))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        # ── Step 3: db_import (generic_import → tiiif_artwork) ──────────── #
        rc = run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)
        if rc != 0:
            return rc

        # ── Step 4: provenance_insert ──────────────────────────────────── #
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
