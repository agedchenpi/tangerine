"""
Bank of England Interactive Statistical Database (IADB) API Client.

Provides access to BoE statistical data via CSV endpoints:
- SONIA (Sterling Overnight Index Average) daily rates

API Documentation: https://www.bankofengland.co.uk/boeapps/database/
"""

import csv
import io
from datetime import date, timedelta
from typing import Dict, List

from etl.base.api_client import BaseAPIClient


class BankOfEnglandAPIClient(BaseAPIClient):
    """
    Client for Bank of England IADB CSV endpoints.

    The BoE IADB returns CSV data (not JSON), so this client uses
    _make_request() directly and parses CSV from response.text.

    Usage:
        client = BankOfEnglandAPIClient()
        rates = client.get_sonia_rates(days=60)
        client.close()
    """

    def __init__(self, base_url: str = 'https://www.bankofengland.co.uk'):
        super().__init__(base_url=base_url, rate_limit=30)

    def get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': 'Tangerine-ETL/1.0',
            'Accept': 'text/csv'
        }

    def get_sonia_rates(self, days: int = 60) -> List[Dict]:
        """
        Fetch SONIA daily rates from BoE IADB.

        Args:
            days: Number of days of history to fetch (default: 60)

        Returns:
            List of dicts with keys 'date' and 'rate'
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        params = {
            'Datefrom': start_date.strftime('%d/%b/%Y'),
            'Dateto': end_date.strftime('%d/%b/%Y'),
            'SeriesCodes': 'IUDSOIA',
            'CSVF': 'TN',
            'UsingCodes': 'Y',
            'VPD': 'Y',
            'VFD': 'N',
        }

        endpoint = '/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes'

        self.logger.info(
            f"Fetching SONIA rates from {start_date} to {end_date}",
            extra={'metadata': {'days': days, 'series': 'IUDSOIA'}}
        )

        response = self._make_request('GET', endpoint, params=params)

        records = []
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            date_val = row.get('DATE')
            rate_val = row.get('IUDSOIA')
            if date_val and rate_val:
                records.append({'date': date_val.strip(), 'rate': rate_val.strip()})

        self.logger.info(f"Fetched {len(records)} SONIA rate records")
        return records
