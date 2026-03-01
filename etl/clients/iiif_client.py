"""
Smithsonian IIIF Presentation API client.

Fetches IIIF manifests from ids.si.edu and downloads full-resolution images.
No authentication required — Smithsonian public API.

IIIF Presentation API 2.x:
  Manifest URL:  https://ids.si.edu/ids/manifest/{manifest_id}
  Image URL:     https://ids.si.edu/ids/iiif/{manifest_id}/full/full/0/default.jpg

Usage:
    client = IIIFClient()
    manifest = client.get_manifest('FS-6542_02')
    record = client.parse_manifest(manifest)
    client.download_image(record['image_url'], Path('/app/data/images/iiif/FS-6542_02.jpg'))
    client.close()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from etl.base.api_client import BaseAPIClient


class IIIFClient(BaseAPIClient):
    """
    Client for Smithsonian IIIF Presentation API (ids.si.edu).

    No API key required. Rate limit is generous for public use;
    a small sleep between requests is added as courtesy.

    Usage:
        with IIIFClient() as client:
            manifest = client.get_manifest('FS-6542_02')
            record = client.parse_manifest(manifest)
    """

    BASE_URL = 'https://ids.si.edu'

    # Metadata label synonyms → canonical column names
    _LABEL_MAP = {
        # title
        'title': 'title',
        # artist
        'artist': 'artist',
        'maker': 'artist',
        'creator': 'artist',
        # medium
        'medium': 'medium',
        'technique': 'medium',
        'material and technique': 'medium',
        # dimensions
        'dimensions': 'dimensions_text',
        'measurements': 'dimensions_text',
        # date
        'date': 'date_text',
        'date created': 'date_text',
        # period
        'period': 'period',
        'dynasty': 'period',
        # origin
        'place of origin': 'origin',
        'origin': 'origin',
        'geography': 'origin',
        # artwork type
        'object type': 'artwork_type',
        'type': 'artwork_type',
        'classification': 'artwork_type',
        # description
        'description': 'description',
        'summary': 'description',
        # collection
        'collection': 'collection',
        # data source / museum
        'data source': 'data_source',
        'museum': 'data_source',
        'repository': 'data_source',
        # credit line
        'credit line': 'credit_line',
        'credit': 'credit_line',
        # accession number
        'accession number': 'accession_number',
        'id number': 'accession_number',
        # Getty synonyms
        'artist/maker': 'artist',
        'material': 'medium',
        'rights statement': 'metadata_usage',
        # Smithsonian rights field
        'metadata usage': 'metadata_usage',
    }

    def __init__(self):
        super().__init__(base_url=self.BASE_URL, rate_limit=30)

    def get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': 'Tangerine-ETL/1.0',
            'Accept': 'application/json, application/ld+json',
        }

    # ------------------------------------------------------------------ #
    # Public methods                                                       #
    # ------------------------------------------------------------------ #

    def get_manifest(self, manifest_id: str) -> dict:
        """
        Fetch IIIF Presentation API manifest for a given manifest ID.

        Args:
            manifest_id: e.g. 'FS-6542_02'

        Returns:
            Raw manifest dict (IIIF Presentation API 2.x JSON-LD)
        """
        self.logger.info(f"Fetching IIIF manifest: {manifest_id}")
        return self.get(f'/ids/manifest/{manifest_id}')

    def parse_manifest(self, manifest: dict) -> dict:
        """
        Extract structured fields from a raw IIIF manifest.

        Parses the manifest metadata[] array, canvas dimensions, image
        resource URL, and service URL. Returns a flat dict whose keys
        match tiiif_artwork columns plus a 'provenance' list of dicts.

        Args:
            manifest: Raw IIIF manifest dict

        Returns:
            Dict with artwork fields + 'provenance' list + 'raw_metadata' JSONB
        """
        manifest_id = manifest.get('@id', '').rstrip('/').split('/')[-1]

        # ── metadata[] → flat dict + multi-value fields ─────────────── #
        metadata_list: List[dict] = manifest.get('metadata', [])
        mapped: Dict[str, str] = {}
        topics: List[str] = []
        exhibitions_raw: List[str] = []
        ark_guid = None

        for item in metadata_list:
            raw_label = str(item.get('label', '')).strip()
            label_lower = raw_label.lower()
            value = self._extract_value(item.get('value'))
            if not value:
                continue

            # Multi-value fields: collect all occurrences
            if label_lower == 'topic':
                topics.append(value)
                continue
            if label_lower == 'exhibition history':
                exhibitions_raw.append(value)
                continue
            if label_lower == 'guid':
                ark_guid = value
                continue

            col = self._LABEL_MAP.get(label_lower)
            if col and col not in mapped:
                mapped[col] = value

        # metadata_usage may arrive via _LABEL_MAP ('metadata usage' or 'rights statement')
        # ark_guid extracted directly above

        # ── canvas / image resource ──────────────────────────────────── #
        canvas = self._first_canvas(manifest)
        image_width, image_height, image_url, service_url, iiif_profile = (
            None, None, None, None, None
        )

        if canvas:
            image_width = canvas.get('width')
            image_height = canvas.get('height')

            resource = self._first_resource(canvas)
            if resource:
                image_url = resource.get('@id')
                svc = resource.get('service', {})
                service_url = svc.get('@id')
                iiif_profile = self._extract_profile(svc.get('profile'))

        # ── build image download URL ─────────────────────────────────── #
        if service_url:
            image_url = f"{service_url}/full/full/0/default.jpg"
        elif manifest_id:
            image_url = f"{self.BASE_URL}/ids/iiif/{manifest_id}/full/full/0/default.jpg"
            service_url = f"{self.BASE_URL}/ids/iiif/{manifest_id}"

        # ── manifest-level fields ────────────────────────────────────── #
        attribution = self._extract_value(manifest.get('attribution'))
        license_url = manifest.get('license')

        # ── seeAlso → api_url (Getty Linked Art pattern) ─────────────── #
        # seeAlso may be a list, a single dict, or a plain string
        see_also = manifest.get('seeAlso', [])
        if isinstance(see_also, list) and see_also:
            first = see_also[0]
            api_url = first.get('@id') if isinstance(first, dict) else str(first)
        elif isinstance(see_also, dict):
            api_url = see_also.get('@id')
        elif isinstance(see_also, str):
            api_url = see_also
        else:
            api_url = None

        # ── exhibition_history → JSONB string ────────────────────────── #
        exhibitions_list = self._parse_exhibitions(exhibitions_raw)
        exhibition_history = json.dumps(exhibitions_list) if exhibitions_list else None

        record = {
            'manifest_id':        manifest_id,
            'manifest_url':       manifest.get('@id', f"{self.BASE_URL}/ids/manifest/{manifest_id}"),
            'iiif_service_url':   service_url,
            'iiif_profile':       iiif_profile,
            'accession_number':   mapped.get('accession_number'),
            'title':              mapped.get('title') or self._extract_value(manifest.get('label')) or '',
            'artist':             mapped.get('artist'),
            'medium':             mapped.get('medium'),
            'dimensions_text':    mapped.get('dimensions_text'),
            'date_text':          mapped.get('date_text'),
            'period':             mapped.get('period'),
            'origin':             mapped.get('origin'),
            'artwork_type':       mapped.get('artwork_type'),
            'description':        mapped.get('description') or self._extract_value(manifest.get('description')),
            'collection':         mapped.get('collection'),
            'data_source':        mapped.get('data_source'),
            'credit_line':        mapped.get('credit_line'),
            'ark_guid':           ark_guid,
            'metadata_usage':     mapped.get('metadata_usage'),
            'topics':             self._to_pg_array(topics),
            'exhibition_history': exhibition_history,
            'api_url':            api_url,
            'image_url':          image_url,
            'image_width':        image_width,
            'image_height':       image_height,
            'image_format':       'image/jpeg',
            'attribution':        attribution,
            'license_url':        license_url,
            'local_directory':    '/app/data/images/iiif/',
            'local_filename':     None,
            'raw_metadata':       metadata_list,
            'provenance':         self._parse_provenance(metadata_list),
        }

        self.logger.info(
            f"Parsed manifest {manifest_id}: "
            f"title='{record['title'][:60]}', "
            f"image={image_width}x{image_height}"
        )
        return record

    def download_image(self, image_url: str, dest_path: Path) -> int:
        """
        Stream full-resolution IIIF image to dest_path.

        Uses a .tmp suffix during download and renames on success to
        avoid leaving partial files on disk.

        Args:
            image_url: Full image URL (e.g. .../full/full/0/default.jpg)
            dest_path: Target Path for the downloaded file

        Returns:
            File size in bytes
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dest_path.with_suffix('.tmp')

        self.logger.info(f"Downloading image: {image_url} → {dest_path}")

        response = self.session.get(
            image_url,
            headers=self.get_headers(),
            stream=True,
            timeout=self.timeout
        )
        response.raise_for_status()

        bytes_written = 0
        try:
            with open(tmp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=65536):
                    f.write(chunk)
                    bytes_written += len(chunk)
            tmp_path.rename(dest_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        self.logger.info(f"Downloaded {bytes_written:,} bytes → {dest_path.name}")
        return bytes_written

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _extract_value(self, value) -> Optional[str]:
        """Normalise IIIF string-or-list value to a plain string."""
        if value is None:
            return None
        if isinstance(value, list):
            # May be a list of language-tagged strings or plain strings
            parts = []
            for item in value:
                if isinstance(item, dict):
                    parts.append(str(item.get('@value', '')))
                else:
                    parts.append(str(item))
            return '; '.join(p for p in parts if p).strip() or None
        if isinstance(value, dict):
            return str(value.get('@value', '')).strip() or None
        return str(value).strip() or None

    def _extract_profile(self, profile) -> Optional[str]:
        """Extract profile URI string from profile field (may be list or str)."""
        if not profile:
            return None
        if isinstance(profile, list):
            for item in profile:
                if isinstance(item, str):
                    return item
                if isinstance(item, dict):
                    return item.get('@id')
        if isinstance(profile, str):
            return profile
        return None

    def _first_canvas(self, manifest: dict) -> Optional[dict]:
        """Return the first canvas from the first sequence."""
        sequences = manifest.get('sequences', [])
        if not sequences:
            return None
        canvases = sequences[0].get('canvases', [])
        return canvases[0] if canvases else None

    def _first_resource(self, canvas: dict) -> Optional[dict]:
        """Return the first image resource from a canvas."""
        images = canvas.get('images', [])
        if not images:
            return None
        return images[0].get('resource')

    def get_manifest_url(self, manifest_url: str) -> dict:
        """
        Fetch a IIIF manifest from a full URL (e.g. Getty manifest URL).

        Use this when the manifest URL differs from the Smithsonian BASE_URL pattern.

        Args:
            manifest_url: Full manifest URL, e.g. https://media.getty.edu/iiif/manifest/{uuid}

        Returns:
            Raw manifest dict (IIIF Presentation API 2.x JSON-LD)
        """
        self.logger.info(f"Fetching IIIF manifest from URL: {manifest_url}")
        response = self.session.get(manifest_url, headers=self.get_headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_linked_art(self, api_url: str) -> dict:
        """
        Fetch a Linked Art JSON-LD record (e.g. Getty data.getty.edu API).

        Args:
            api_url: Full URL to the Linked Art record

        Returns:
            Linked Art JSON-LD dict
        """
        self.logger.info(f"Fetching Linked Art: {api_url}")
        response = self.session.get(api_url, headers=self.get_headers(), timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def parse_linked_art_provenance(self, linked_art: dict) -> List[dict]:
        """
        Parse provenance from Getty Linked Art API `changed_ownership_through[]`.

        Each acquisition entry maps to one provenance row:
          holder_name   ← transferred_title_to[0]._label
          holder_dates  ← timespan.identified_by[0].content
          location      ← referred_to_by[classified=Provenance Location Statement].content
          acquisition_notes ← referred_to_by[classified=Provenance Biography].content

        Args:
            linked_art: Linked Art JSON-LD dict from data.getty.edu

        Returns:
            List of provenance dicts (sequence_order, holder_name, holder_dates,
            location, acquisition_notes)
        """
        rows = []
        for acq in linked_art.get('changed_ownership_through', []):
            holders = acq.get('transferred_title_to', [])
            holder_name = holders[0].get('_label', '') if holders else ''

            activity = (acq.get('part_of') or [{}])[0]
            timespan = activity.get('timespan', {})
            holder_dates = next(
                (n.get('content') for n in timespan.get('identified_by', [])), None
            )

            notes_by_class = {}
            for note in activity.get('referred_to_by', []):
                label = (note.get('classified_as') or [{}])[0].get('_label', '')
                notes_by_class[label] = note.get('content', '')

            rows.append({
                'sequence_order':    len(rows) + 1,
                'holder_name':       holder_name,
                'holder_dates':      holder_dates,
                'location':          notes_by_class.get('Provenance Location Statement'),
                'acquisition_notes': notes_by_class.get('Provenance Biography'),
            })
        return rows

    def _parse_provenance(self, metadata_list: list) -> List[dict]:
        """
        Parse Smithsonian manifest provenance: alternating date-header/detail pairs.

        The metadata[] array contains interleaved 'Provenance' entries:
          odd items  → date range headers  ("To 1909", "From 1909 to 1919")
          even items → holder detail lines ("Charles Lang Freer ..., purchased in 1909 [1]")
        followed by 'Notes:' and footnote entries ("[1] See Original Panel List...").

        Returns a list of provenance dicts ordered by sequence_order.
        Returns an empty list if no 'Provenance' entries are found.
        """
        import re
        prov_entries = [
            self._extract_value(m.get('value'))
            for m in metadata_list
            if str(m.get('label', '')).strip() == 'Provenance'
        ]
        prov_entries = [e for e in prov_entries if e]

        chain: List[str] = []
        footnotes: Dict[int, str] = {}
        notes_section = False

        for entry in prov_entries:
            if entry.strip() == 'Notes:':
                notes_section = True
                continue
            if notes_section:
                match = re.match(r'^\[(\d+)\]\s*(.*)', entry)
                if match:
                    footnotes[int(match.group(1))] = match.group(2).strip()
            else:
                chain.append(entry)

        rows = []
        for i in range(0, len(chain) - 1, 2):
            date_header = chain[i]
            detail = chain[i + 1]
            refs = [int(r) for r in re.findall(r'\[(\d+)\]', detail)]
            detail_clean = re.sub(r'\s*\[\d+\]', '', detail).strip()
            footnote_text = '; '.join(footnotes[r] for r in refs if r in footnotes) or None
            rows.append({
                'sequence_order':    len(rows) + 1,
                'holder_name':       detail_clean,
                'holder_dates':      date_header,
                'location':          None,
                'acquisition_notes': footnote_text,
            })
        return rows

    def _to_pg_array(self, items: List[str]) -> Optional[str]:
        """Convert a Python list to a PostgreSQL TEXT[] literal string.

        e.g. ['landscape', 'pine tree'] → '{"landscape","pine tree"}'

        Used so generic_import (which reads from JSON and stringifies values)
        passes the correct literal format for TEXT[] columns.
        """
        if not items:
            return None
        escaped = ['"' + s.replace('"', '""') + '"' for s in items]
        return '{' + ','.join(escaped) + '}'

    def _parse_exhibitions(self, raw: List[str]) -> List[dict]:
        """
        Convert 'Name (dates)' strings to [{'name': ..., 'dates': ...}] dicts.

        Args:
            raw: List of exhibition strings from manifest metadata[]

        Returns:
            List of dicts with 'name' and 'dates' keys
        """
        import re
        result = []
        for entry in raw:
            m = re.match(r'^(.*?)\s*\(([^)]+)\)\s*$', entry)
            if m:
                result.append({'name': m.group(1).strip(), 'dates': m.group(2).strip()})
            else:
                result.append({'name': entry.strip(), 'dates': None})
        return result
