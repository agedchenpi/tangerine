"""
Far Side web scraper client.

Scrapes daily comic pages from thefarside.com and downloads images
from the Andrews McMeel CDN (featureassets.amuniversal.com).

Page structure (per date):
  - 5 comic cards in <div class="card tfs-comic js-comic">
  - Image URL in <img data-src="..." class="img-fluid js-lazy-load">
  - Caption in <figcaption class="figure-caption">

Usage:
    client = FarSideClient()
    comics = client.scrape_date('2026-05-06')
    for comic in comics:
        client.download_image(comic['image_url'], Path('farside_20260506_1.jpg'))
    client.close()
"""

from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup

from etl.base.api_client import BaseAPIClient


class FarSideClient(BaseAPIClient):
    """Client for scraping thefarside.com daily comics."""

    BASE_URL = "https://www.thefarside.com"

    _USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    def __init__(self):
        super().__init__(
            base_url=self.BASE_URL,
            timeout=30,
            rate_limit=20,
            retry_attempts=3,
        )

    def get_headers(self) -> Dict[str, str]:
        return {"User-Agent": self._USER_AGENT}

    def scrape_date(self, date_str: str) -> List[dict]:
        """Scrape comics for a given date.

        Args:
            date_str: Date in YYYY-MM-DD format.

        Returns:
            List of dicts with keys: position, image_url, alt_text, caption.
        """
        year, month, day = date_str.split("-")
        endpoint = f"/{year}/{month}/{day}"

        response = self._make_request("GET", endpoint)
        soup = BeautifulSoup(response.text, "html.parser")

        comics = []
        cards = soup.select("div.tfs-comic.js-comic")

        for idx, card in enumerate(cards, start=1):
            img = card.select_one("img.js-lazy-load")
            if not img:
                continue

            image_url = img.get("data-src", "")
            if not image_url:
                continue

            alt_text = img.get("alt", "").strip() or None

            figcaption = card.select_one("figcaption.figure-caption")
            caption = figcaption.get_text(strip=True) if figcaption else None
            caption = caption or None  # empty string → None

            comics.append({
                "position": idx,
                "image_url": image_url,
                "alt_text": alt_text,
                "caption": caption,
            })

        self.logger.info(f"Scraped {len(comics)} comics for {date_str}")
        return comics

    def download_image(self, image_url: str, dest_path: Path) -> int:
        """Download a comic image with atomic write.

        Args:
            image_url: Full CDN URL.
            dest_path: Local file path to save to.

        Returns:
            Bytes written.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dest_path.with_suffix(".tmp")

        response = self.session.get(
            image_url,
            headers=self.get_headers(),
            stream=True,
            timeout=self.timeout,
        )
        response.raise_for_status()

        bytes_written = 0
        try:
            with open(tmp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    f.write(chunk)
                    bytes_written += len(chunk)
            tmp_path.rename(dest_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        return bytes_written
