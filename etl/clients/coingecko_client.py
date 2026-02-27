"""
CoinGecko cryptocurrency OHLC API client.

Fetches daily OHLC price data for top 5 cryptocurrencies via the
CoinGecko free REST API (/api/v3/coins/{id}/ohlc endpoint).

The API returns 4-hour candles; this client aggregates to one daily record:
  open  = first candle open
  high  = max of all candle highs
  low   = min of all candle lows
  close = last candle close
  price_date = UTC date of the last candle
"""

import time
from datetime import datetime, timezone
from typing import Dict, List

from etl.base.api_client import BaseAPIClient


class CoinGeckoClient(BaseAPIClient):
    """
    Client for CoinGecko free-tier OHLC API.

    Rate limit: ~10-30 rpm on free tier. A 1-second sleep is added
    between coin fetches to stay within limits.

    Usage:
        client = CoinGeckoClient()
        ohlc = client.get_crypto_ohlc_daily()
        client.close()

    Or as a context manager:
        with CoinGeckoClient() as client:
            ohlc = client.get_crypto_ohlc_daily()
    """

    BASE_URL = 'https://api.coingecko.com'

    COINS = {
        'bitcoin':     'BTC',
        'ethereum':    'ETH',
        'binancecoin': 'BNB',
        'solana':      'SOL',
        'ripple':      'XRP',
    }

    def __init__(self):
        super().__init__(base_url=self.BASE_URL, rate_limit=10)

    def get_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': 'Tangerine-ETL/1.0',
            'Accept': 'application/json',
        }

    def get_crypto_ohlc_daily(self, days: int = 1) -> List[Dict]:
        """
        Fetch and aggregate OHLC data for each tracked cryptocurrency.

        For each coin, fetches /api/v3/coins/{id}/ohlc?vs_currency=usd&days=1,
        which returns 4-hour candles. Aggregates all candles to a single
        daily record using first open, max high, min low, last close.

        Args:
            days: CoinGecko days parameter (1 = last 24h candles)

        Returns:
            List of dicts with keys: symbol, coin_id, price_date (ISO str),
            open, high, low, close
        """
        records = []

        for coin_id, symbol in self.COINS.items():
            self.logger.info(f"Fetching OHLC for {coin_id} ({symbol})")
            try:
                response = self._make_request(
                    'GET',
                    f'/api/v3/coins/{coin_id}/ohlc',
                    params={'vs_currency': 'usd', 'days': days}
                )
                candles = response.json()

                if not candles:
                    self.logger.warning(f"No candles returned for {coin_id}")
                    time.sleep(1)
                    continue

                # Aggregate intraday candles to one daily record
                # Each candle: [timestamp_ms, open, high, low, close]
                last_ts_ms = candles[-1][0]
                price_date = datetime.fromtimestamp(
                    last_ts_ms / 1000, tz=timezone.utc
                ).date().isoformat()

                records.append({
                    'symbol': symbol,
                    'coin_id': coin_id,
                    'price_date': price_date,
                    'open': round(float(candles[0][1]), 6),
                    'high': round(max(c[2] for c in candles), 6),
                    'low': round(min(c[3] for c in candles), 6),
                    'close': round(float(candles[-1][4]), 6),
                })
                self.logger.info(
                    f"Fetched {len(candles)} candles for {coin_id}, "
                    f"aggregated to date {price_date}"
                )
            except Exception as e:
                self.logger.error(f"Error fetching OHLC for {coin_id}: {e}")

            # Respect free-tier rate limit between requests
            time.sleep(1)

        self.logger.info(f"Fetched {len(records)} crypto OHLC records")
        return records
