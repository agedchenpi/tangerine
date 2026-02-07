#!/usr/bin/env python3
"""
Fetch data from NewYorkFed Markets API and save as JSON files.

This script fetches data from all NewYorkFed API endpoints and saves
the responses as JSON files in the source directory for processing by
the generic import framework.

Usage:
    python scripts/fetch_newyorkfed_api_data.py [--endpoint ENDPOINT]

Examples:
    # Fetch all endpoints
    python scripts/fetch_newyorkfed_api_data.py

    # Fetch specific endpoint
    python scripts/fetch_newyorkfed_api_data.py --endpoint reference_rates
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from etl.clients.newyorkfed_client import NewYorkFedAPIClient
import logging

# Data directories
SOURCE_DIR = Path("/app/data/source/newyorkfed")
ARCHIVE_DIR = Path("/app/data/archive/newyorkfed")


def save_json_file(data: List[Dict], endpoint_name: str, logger) -> Path:
    """
    Save API response data to JSON file.

    Args:
        data: List of records from API
        endpoint_name: Name of endpoint (e.g., 'reference_rates')
        logger: Logger instance

    Returns:
        Path to saved file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"newyorkfed_{endpoint_name}_{timestamp}.json"
    filepath = SOURCE_DIR / filename

    # Ensure directory exists
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    # Save JSON file
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved {len(data)} records to {filepath}")
    return filepath


def fetch_and_save_all(logger) -> Dict[str, int]:
    """
    Fetch data from all NewYorkFed API endpoints and save as JSON files.

    Args:
        logger: Logger instance

    Returns:
        Dictionary mapping endpoint names to record counts
    """
    client = NewYorkFedAPIClient()
    results = {}

    # Define all endpoints to fetch
    endpoints = [
        ("reference_rates", client.get_reference_rates_latest),
        ("soma_holdings", client.get_soma_holdings),
        ("repo_operations", client.get_repo_operations),
        ("securities_lending", client.get_securities_lending),
        ("treasury_operations", client.get_treasury_operations),
        ("agency_mbs", client.get_agency_mbs),
        ("fx_swaps", client.get_fx_swaps),
        ("guide_sheets", client.get_guide_sheets),
    ]

    print("=" * 70)
    print("Fetching NewYorkFed API Data")
    print("=" * 70)
    print()

    for endpoint_name, fetch_func in endpoints:
        try:
            print(f"Fetching {endpoint_name}...", end=" ", flush=True)
            logger.info(f"Fetching data for {endpoint_name}")

            # Fetch data
            data = fetch_func()

            if data and len(data) > 0:
                # Save to JSON file
                filepath = save_json_file(data, endpoint_name, logger)
                results[endpoint_name] = len(data)
                print(f"✅ {len(data)} records saved to {filepath.name}")
            else:
                results[endpoint_name] = 0
                print(f"⚠️  No data available")

        except Exception as e:
            logger.error(f"Failed to fetch {endpoint_name}: {e}", exc_info=True)
            results[endpoint_name] = -1
            print(f"❌ ERROR: {str(e)}")

    # Close client
    client.close()

    # Print summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    total_records = sum(count for count in results.values() if count > 0)
    successful = sum(1 for count in results.values() if count > 0)
    empty = sum(1 for count in results.values() if count == 0)
    failed = sum(1 for count in results.values() if count < 0)

    for endpoint, count in results.items():
        status = "✅ SUCCESS" if count > 0 else ("⚠️  EMPTY" if count == 0 else "❌ FAILED")
        print(f"{endpoint:<25} {status:>15} {count:>8} records")

    print("-" * 70)
    print(f"Total: {total_records} records from {successful} endpoints")
    print(f"Empty: {empty}, Failed: {failed}")
    print("=" * 70)

    return results


def fetch_and_save_single(endpoint_name: str, logger) -> int:
    """
    Fetch data from a single endpoint and save as JSON file.

    Args:
        endpoint_name: Name of endpoint to fetch
        logger: Logger instance

    Returns:
        Number of records fetched
    """
    client = NewYorkFedAPIClient()

    # Map endpoint names to client methods
    endpoint_map = {
        "reference_rates": client.get_reference_rates_latest,
        "soma_holdings": client.get_soma_holdings,
        "repo_operations": client.get_repo_operations,
        "securities_lending": client.get_securities_lending,
        "treasury_operations": client.get_treasury_operations,
        "agency_mbs": client.get_agency_mbs,
        "fx_swaps": client.get_fx_swaps,
        "guide_sheets": client.get_guide_sheets,
    }

    if endpoint_name not in endpoint_map:
        logger.error(f"Unknown endpoint: {endpoint_name}")
        print(f"❌ Unknown endpoint: {endpoint_name}")
        print(f"Available endpoints: {', '.join(endpoint_map.keys())}")
        return -1

    try:
        fetch_func = endpoint_map[endpoint_name]
        logger.info(f"Fetching data for {endpoint_name}")

        # Fetch data
        data = fetch_func()

        if data and len(data) > 0:
            # Save to JSON file
            filepath = save_json_file(data, endpoint_name, logger)
            print(f"✅ Saved {len(data)} records to {filepath}")
            return len(data)
        else:
            print(f"⚠️  No data available for {endpoint_name}")
            return 0

    except Exception as e:
        logger.error(f"Failed to fetch {endpoint_name}: {e}", exc_info=True)
        print(f"❌ ERROR: {str(e)}")
        return -1
    finally:
        client.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch data from NewYorkFed Markets API and save as JSON files"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        help="Fetch specific endpoint only (default: fetch all)"
    )
    args = parser.parse_args()

    # Initialize logger
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("fetch_newyorkfed_api_data")

    if args.endpoint:
        # Fetch single endpoint
        count = fetch_and_save_single(args.endpoint, logger)
        return 0 if count >= 0 else 1
    else:
        # Fetch all endpoints
        results = fetch_and_save_all(logger)
        failed = sum(1 for count in results.values() if count < 0)
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
