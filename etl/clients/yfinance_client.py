"""
Yahoo Finance market data client.

Provides OHLCV price data for commodity futures, US indexes, global indexes,
and sector ETFs using the yfinance Python library. Fetches 5 days of history
and takes the most recent non-null row per ticker to handle weekends and holidays.
"""

from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from common.logging_utils import get_logger


def _safe_float(val) -> Optional[float]:
    """Convert a pandas value to float, returning None for NaN/None."""
    try:
        if pd.isna(val):
            return None
        return round(float(val), 6)
    except (TypeError, ValueError):
        return None


def _safe_int(val) -> Optional[int]:
    """Convert a pandas value to int, returning None for NaN/None."""
    try:
        if pd.isna(val):
            return None
        return int(val)
    except (TypeError, ValueError):
        return None


class YFinanceClient:
    """
    Client for Yahoo Finance OHLCV market data.

    Supports commodity futures, US market indexes, global indexes,
    and US sector ETFs.

    Usage:
        client = YFinanceClient()
        prices = client.get_commodity_prices()
        us_indexes = client.get_us_index_prices()
        global_indexes = client.get_global_index_prices()
        sector_etfs = client.get_sector_etf_prices()
    """

    COMMODITIES = {
        'CL=F': ('CL', 'Energy'),       # WTI Crude Oil
        'BZ=F': ('BZ', 'Energy'),       # Brent Crude Oil
        'NG=F': ('NG', 'Energy'),       # Natural Gas
        'GC=F': ('GC', 'Metals'),       # Gold
        'SI=F': ('SI', 'Metals'),       # Silver
        'HG=F': ('HG', 'Metals'),       # Copper
        'ZW=F': ('ZW', 'Agriculture'),  # Wheat
        'ZC=F': ('ZC', 'Agriculture'),  # Corn
        'ZS=F': ('ZS', 'Agriculture'),  # Soybeans
        'LE=F': ('LE', 'Livestock'),    # Live Cattle
        'HE=F': ('HE', 'Livestock'),    # Lean Hogs
        'KC=F': ('KC', 'Softs'),        # Coffee
        'SB=F': ('SB', 'Softs'),        # Sugar
    }

    US_INDEXES = {
        '^GSPC': 'S&P 500',
        '^IXIC': 'NASDAQ Composite',
        '^NDX':  'NASDAQ-100',
        '^DJI':  'Dow Jones Industrial Average',
        '^RUT':  'Russell 2000',
        '^VIX':  'CBOE Volatility Index',
        '^TNX':  '10-Year Treasury Yield',
        '^TYX':  '30-Year Treasury Yield',
    }

    GLOBAL_INDEXES = {
        '^FTSE':     ('FTSE 100',      'Europe'),
        '^GDAXI':    ('DAX',           'Europe'),
        '^FCHI':     ('CAC 40',        'Europe'),
        '^STOXX50E': ('Euro Stoxx 50', 'Europe'),
        '^N225':     ('Nikkei 225',    'Asia'),
        '^HSI':      ('Hang Seng',     'Asia'),
        '^AXJO':     ('ASX 200',       'Asia'),
    }

    SECTOR_ETFS = {
        'XLF':  ('Financial Select Sector SPDR',                      'Financials'),
        'XLK':  ('Technology Select Sector SPDR',                     'Technology'),
        'XLE':  ('Energy Select Sector SPDR',                         'Energy'),
        'XLV':  ('Health Care Select Sector SPDR',                    'Health Care'),
        'XLI':  ('Industrial Select Sector SPDR',                     'Industrials'),
        'XLU':  ('Utilities Select Sector SPDR',                      'Utilities'),
        'XLB':  ('Materials Select Sector SPDR',                      'Materials'),
        'XLRE': ('Real Estate Select Sector SPDR',                    'Real Estate'),
        'XLY':  ('Consumer Discretionary Select Sector SPDR',         'Consumer Discretionary'),
        'XLP':  ('Consumer Staples Select Sector SPDR',               'Consumer Staples'),
        'XLC':  ('Communication Services Select Sector SPDR',         'Communication Services'),
    }

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def _download_ticker_prices(self, tickers: list, period: str = '5d') -> dict:
        """
        Download OHLCV for a list of tickers via yfinance.

        Returns a dict keyed by ticker symbol with price_date, open, high, low,
        close, volume — taking the most recent non-null Close row per ticker.
        """
        df = yf.download(tickers, period=period, progress=False, auto_adjust=False)

        if df is None or df.empty:
            return {}

        results = {}

        if isinstance(df.columns, pd.MultiIndex):
            # Multiple tickers: columns are (Price, Ticker) MultiIndex
            for ticker in tickers:
                try:
                    ticker_df = df.xs(ticker, axis=1, level=1).dropna(subset=['Close'])
                    if ticker_df.empty:
                        self.logger.warning(f"No data for {ticker}")
                        continue
                    row = ticker_df.iloc[-1]
                    results[ticker] = {
                        'price_date': ticker_df.index[-1].date().isoformat(),
                        'open': _safe_float(row.get('Open')),
                        'high': _safe_float(row.get('High')),
                        'low': _safe_float(row.get('Low')),
                        'close': _safe_float(row.get('Close')),
                        'volume': _safe_int(row.get('Volume')),
                    }
                except Exception as e:
                    self.logger.warning(f"Skipping {ticker}: {e}")
        else:
            # Single-ticker fallback
            ticker = tickers[0]
            df_clean = df.dropna(subset=['Close'])
            if not df_clean.empty:
                row = df_clean.iloc[-1]
                results[ticker] = {
                    'price_date': df_clean.index[-1].date().isoformat(),
                    'open': _safe_float(row.get('Open')),
                    'high': _safe_float(row.get('High')),
                    'low': _safe_float(row.get('Low')),
                    'close': _safe_float(row.get('Close')),
                    'volume': _safe_int(row.get('Volume')),
                }

        return results

    def get_commodity_prices(self, period: str = '5d') -> List[Dict]:
        """
        Fetch the most recent OHLCV price for each commodity future.

        Uses period='5d' to handle weekends and trading holidays —
        takes the most recent non-null row per ticker.

        Args:
            period: yfinance period string (default '5d')

        Returns:
            List of dicts with keys: symbol, ticker, category,
            price_date (ISO str), open, high, low, close, volume
        """
        tickers = list(self.COMMODITIES.keys())
        self.logger.info(f"Downloading {len(tickers)} commodity tickers from Yahoo Finance")

        df = yf.download(tickers, period=period, progress=False, auto_adjust=False)

        if df is None or df.empty:
            self.logger.warning("No data returned from yfinance")
            return []

        records = []

        if isinstance(df.columns, pd.MultiIndex):
            # Multiple tickers: columns are (Price, Ticker) MultiIndex
            for ticker, (symbol, category) in self.COMMODITIES.items():
                try:
                    ticker_df = df.xs(ticker, axis=1, level=1)
                    ticker_df = ticker_df.dropna(subset=['Close'])
                    if ticker_df.empty:
                        self.logger.warning(f"No data for {ticker} ({symbol})")
                        continue
                    row = ticker_df.iloc[-1]
                    price_date = ticker_df.index[-1].date().isoformat()
                    records.append({
                        'symbol': symbol,
                        'ticker': ticker,
                        'category': category,
                        'price_date': price_date,
                        'open': _safe_float(row.get('Open')),
                        'high': _safe_float(row.get('High')),
                        'low': _safe_float(row.get('Low')),
                        'close': _safe_float(row.get('Close')),
                        'volume': _safe_int(row.get('Volume')),
                    })
                except Exception as e:
                    self.logger.warning(f"Skipping {ticker} ({symbol}): {e}")
        else:
            # Single ticker fallback (unlikely with 13 tickers, but handled for robustness)
            ticker = tickers[0]
            symbol, category = self.COMMODITIES[ticker]
            df = df.dropna(subset=['Close'])
            if not df.empty:
                row = df.iloc[-1]
                price_date = df.index[-1].date().isoformat()
                records.append({
                    'symbol': symbol,
                    'ticker': ticker,
                    'category': category,
                    'price_date': price_date,
                    'open': _safe_float(row.get('Open')),
                    'high': _safe_float(row.get('High')),
                    'low': _safe_float(row.get('Low')),
                    'close': _safe_float(row.get('Close')),
                    'volume': _safe_int(row.get('Volume')),
                })

        self.logger.info(f"Fetched {len(records)} commodity price records")
        return records

    def get_us_index_prices(self, period: str = '5d') -> List[Dict]:
        """
        Fetch the most recent OHLCV price for each US market index.

        Args:
            period: yfinance period string (default '5d')

        Returns:
            List of dicts with keys: symbol, index_name,
            price_date (ISO str), open, high, low, close, volume
        """
        tickers = list(self.US_INDEXES.keys())
        self.logger.info(f"Downloading {len(tickers)} US index tickers from Yahoo Finance")

        prices = self._download_ticker_prices(tickers, period)
        if not prices:
            self.logger.warning("No US index data returned from yfinance")
            return []

        records = []
        for ticker, index_name in self.US_INDEXES.items():
            if ticker not in prices:
                self.logger.warning(f"No data for {ticker} ({index_name})")
                continue
            records.append({
                'symbol': ticker,
                'index_name': index_name,
                **prices[ticker],
            })

        self.logger.info(f"Fetched {len(records)} US index price records")
        return records

    def get_global_index_prices(self, period: str = '5d') -> List[Dict]:
        """
        Fetch the most recent OHLCV price for each global market index.

        Args:
            period: yfinance period string (default '5d')

        Returns:
            List of dicts with keys: symbol, index_name, region,
            price_date (ISO str), open, high, low, close, volume
        """
        tickers = list(self.GLOBAL_INDEXES.keys())
        self.logger.info(f"Downloading {len(tickers)} global index tickers from Yahoo Finance")

        prices = self._download_ticker_prices(tickers, period)
        if not prices:
            self.logger.warning("No global index data returned from yfinance")
            return []

        records = []
        for ticker, (index_name, region) in self.GLOBAL_INDEXES.items():
            if ticker not in prices:
                self.logger.warning(f"No data for {ticker} ({index_name})")
                continue
            records.append({
                'symbol': ticker,
                'index_name': index_name,
                'region': region,
                **prices[ticker],
            })

        self.logger.info(f"Fetched {len(records)} global index price records")
        return records

    def get_sector_etf_prices(self, period: str = '5d') -> List[Dict]:
        """
        Fetch the most recent OHLCV price for each US sector ETF.

        Args:
            period: yfinance period string (default '5d')

        Returns:
            List of dicts with keys: symbol, etf_name, sector,
            price_date (ISO str), open, high, low, close, volume
        """
        tickers = list(self.SECTOR_ETFS.keys())
        self.logger.info(f"Downloading {len(tickers)} sector ETF tickers from Yahoo Finance")

        prices = self._download_ticker_prices(tickers, period)
        if not prices:
            self.logger.warning("No sector ETF data returned from yfinance")
            return []

        records = []
        for ticker, (etf_name, sector) in self.SECTOR_ETFS.items():
            if ticker not in prices:
                self.logger.warning(f"No data for {ticker} ({etf_name})")
                continue
            records.append({
                'symbol': ticker,
                'etf_name': etf_name,
                'sector': sector,
                **prices[ticker],
            })

        self.logger.info(f"Fetched {len(records)} sector ETF price records")
        return records
