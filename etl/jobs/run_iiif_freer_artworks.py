"""
Fetch and import Smithsonian Freer Gallery IIIF artwork records.

For each manifest ID, fetches the IIIF Presentation API manifest, extracts
structured artwork metadata, downloads the full-resolution image, and imports
the records into feeds.tiiif_artwork via generic_import.  Provenance rows are
inserted separately into feeds.tiiif_provenance after the main import.

Usage:
    python etl/jobs/run_iiif_freer_artworks.py
    python etl/jobs/run_iiif_freer_artworks.py --dry-run
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from common.db_utils import db_transaction, fetch_dict
from common.logging_utils import get_logger
from etl.base.import_utils import save_json, run_generic_import, JobRunLogger, audit_cols
from etl.clients.iiif_client import IIIFClient

CONFIG_NAME = 'IIIF_Freer_Artworks'
IMAGE_DIR   = Path('/app/data/images/iiif')

MANIFEST_IDS = [
    'FS-6542_02',   # Fishing by a mountain torrent   (F1909.174)
    'FS-7406_30',   # Riding a donkey on a mountain road (F1911.494)
    'FS-5908_09',   # Standing figure of Lü Dongbin   (F1916.580)
]

logger = get_logger('run_iiif_freer_artworks')


def collect_records(dry_run: bool) -> list:
    """
    Fetch manifests, download images, and return list of artwork dicts.

    On dry-run, image download is skipped and local_filename is left None.
    """
    records = []
    with IIIFClient() as client:
        for manifest_id in MANIFEST_IDS:
            try:
                manifest = client.get_manifest(manifest_id)
                record = client.parse_manifest(manifest)

                if not dry_run:
                    dest = IMAGE_DIR / f"{manifest_id}.jpg"
                    client.download_image(record['image_url'], dest)
                    record['local_filename'] = dest.name
                else:
                    logger.info(f"[dry-run] Skipping image download for {manifest_id}")

                records.append(record)
            except Exception as e:
                logger.error(f"Failed to process manifest {manifest_id}: {e}")

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
        # Serialise raw_metadata list → JSON string for the JSONB column
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
    parser = argparse.ArgumentParser(description='Fetch and import Freer Gallery IIIF artworks')
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch and save JSON but do not load to database or download images')
    args = parser.parse_args()

    with JobRunLogger('run_iiif_freer_artworks', CONFIG_NAME, args.dry_run) as job_log:
        # ── Step 1: data_collection ────────────────────────────────── #
        step_id = job_log.begin_step('data_collection', 'Manifest Fetch')
        try:
            raw_records = collect_records(args.dry_run)
            if not raw_records:
                job_log.complete_step(step_id, records_in=len(MANIFEST_IDS),
                                      records_out=0, message="No records returned")
                return 0

            artwork_rows = transform(raw_records)
            save_json(artwork_rows, CONFIG_NAME, source='iiif')
            job_log.complete_step(step_id, records_in=len(MANIFEST_IDS),
                                  records_out=len(artwork_rows))
        except Exception as e:
            job_log.fail_step(step_id, str(e))
            return 1

        # ── Step 2: db_import (generic_import → tiiif_artwork) ──────── #
        rc = run_generic_import(CONFIG_NAME, args.dry_run, job_run_logger=job_log)
        if rc != 0:
            return rc

        # ── Step 3: provenance insert ────────────────────────────────── #
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
