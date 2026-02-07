#!/usr/bin/env python3
"""
NewYorkFed Markets API Availability Monitor

Checks all 10 API endpoints to determine:
- Which endpoints have data available
- Which endpoints return empty arrays
- API response times
- Any errors or connectivity issues

Run this script to monitor when previously empty APIs start providing data.

Usage:
    python scripts/monitor_newyorkfed_apis.py
    python scripts/monitor_newyorkfed_apis.py --json  # Output as JSON
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.clients.newyorkfed_client import NewYorkFedAPIClient


class APIEndpointMonitor:
    """Monitor for NewYorkFed API endpoint availability and data status."""

    # Define all 10 API endpoints with their metadata
    ENDPOINTS = [
        {
            'name': 'Reference Rates',
            'table': 'newyorkfed_reference_rates',
            'method': 'get_reference_rates_latest',
            'endpoint': '/api/rates/all/latest.json',
            'response_path': 'refRates',
            'description': 'SOFR, EFFR, OBFR, TGCR, BGCR rates'
        },
        {
            'name': 'SOMA Holdings',
            'table': 'newyorkfed_soma_holdings',
            'method': 'get_soma_holdings',
            'endpoint': '/api/soma/tsy/get/monthly.json',
            'response_path': 'soma.holdings',
            'description': 'Treasury securities held by Federal Reserve'
        },
        {
            'name': 'Repo Operations',
            'table': 'newyorkfed_repo_operations',
            'method': 'get_repo_operations',
            'endpoint': '/api/rp/all/all/results/lastTwoWeeks.json',
            'response_path': 'repo.operations',
            'description': 'Repo and reverse repo operations (last 2 weeks)'
        },
        {
            'name': 'Securities Lending',
            'table': 'newyorkfed_securities_lending',
            'method': 'get_securities_lending',
            'endpoint': '/api/seclending/all/results/summary/latest.json',
            'response_path': 'seclending.operations',
            'description': 'Securities lending operations summary'
        },
        {
            'name': 'Guide Sheets',
            'table': 'newyorkfed_guide_sheets',
            'method': 'get_guide_sheets',
            'endpoint': '/api/guidesheets/si/latest.json',
            'response_path': 'guidesheet.si',
            'description': 'SI guide sheet details'
        },
        {
            'name': 'Agency MBS',
            'table': 'newyorkfed_agency_mbs',
            'method': 'get_agency_mbs',
            'endpoint': '/api/ambs/all/announcements/summary/latest.json',
            'response_path': 'ambs.auctions',
            'description': 'Agency MBS operation announcements'
        },
        {
            'name': 'FX Swaps',
            'table': 'newyorkfed_fx_swaps',
            'method': 'get_fx_swaps',
            'endpoint': '/api/fxs/all/latest.json',
            'response_path': 'fxSwaps.operations',
            'description': 'Foreign exchange swap operations'
        },
        {
            'name': 'Treasury Operations',
            'table': 'newyorkfed_treasury_operations',
            'method': 'get_treasury_operations',
            'endpoint': '/api/tsy/all/announcements/summary/latest.json',
            'response_path': 'treasury.auctions',
            'description': 'Treasury operation announcements'
        },
        {
            'name': 'PD Statistics',
            'table': 'newyorkfed_pd_statistics',
            'method': None,  # No implementation yet
            'endpoint': 'NOT_IMPLEMENTED',
            'response_path': None,
            'description': 'Primary Dealer statistics (API endpoint not found)'
        },
        {
            'name': 'Market Share',
            'table': 'newyorkfed_market_share',
            'method': None,  # No implementation yet
            'endpoint': 'NOT_IMPLEMENTED',
            'response_path': None,
            'description': 'Market share data (API endpoint not found)'
        }
    ]

    def __init__(self):
        """Initialize the monitor with NewYorkFed API client."""
        self.client = NewYorkFedAPIClient()
        self.results: List[Dict[str, Any]] = []

    def check_endpoint(self, endpoint_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check a single API endpoint for data availability.

        Args:
            endpoint_config: Endpoint configuration dictionary

        Returns:
            Dictionary with check results
        """
        result = {
            'name': endpoint_config['name'],
            'table': endpoint_config['table'],
            'endpoint': endpoint_config['endpoint'],
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'unknown',
            'record_count': 0,
            'response_time_ms': None,
            'error': None,
            'has_data': False
        }

        # Skip stub implementations
        if endpoint_config['method'] is None:
            result['status'] = 'not_implemented'
            result['error'] = 'No API endpoint implementation available'
            return result

        try:
            # Time the API call
            start_time = time.time()

            # Call the client method
            method = getattr(self.client, endpoint_config['method'])
            data = method()

            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)

            # Analyze results
            result['response_time_ms'] = response_time_ms
            result['record_count'] = len(data) if data else 0
            result['has_data'] = result['record_count'] > 0

            if result['has_data']:
                result['status'] = 'success'
            else:
                result['status'] = 'empty'
                result['error'] = 'API returned empty array (no data available)'

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def check_all_endpoints(self) -> List[Dict[str, Any]]:
        """
        Check all 10 API endpoints.

        Returns:
            List of check results for all endpoints
        """
        print("Checking NewYorkFed API endpoints...")
        print("=" * 80)

        self.results = []
        for endpoint_config in self.ENDPOINTS:
            result = self.check_endpoint(endpoint_config)
            self.results.append(result)

        return self.results

    def print_summary(self):
        """Print human-readable summary of check results."""
        print("\n" + "=" * 80)
        print("NewYorkFed API Availability Report")
        print("=" * 80)
        print(f"Checked at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # Count statuses
        status_counts = {
            'success': 0,
            'empty': 0,
            'error': 0,
            'not_implemented': 0
        }

        for result in self.results:
            status_counts[result['status']] += 1

        # Print summary stats
        print("Summary:")
        print(f"  ✅ APIs with data:        {status_counts['success']}")
        print(f"  ⏳ APIs without data:     {status_counts['empty']}")
        print(f"  ❌ APIs with errors:      {status_counts['error']}")
        print(f"  🚧 Not implemented:       {status_counts['not_implemented']}")
        print(f"  📊 Total endpoints:       {len(self.results)}")
        print()

        # Print detailed results
        print("Detailed Results:")
        print("-" * 80)

        for result in self.results:
            status_icon = {
                'success': '✅',
                'empty': '⏳',
                'error': '❌',
                'not_implemented': '🚧'
            }.get(result['status'], '❓')

            print(f"\n{status_icon} {result['name']}")
            print(f"   Table: {result['table']}")
            print(f"   Endpoint: {result['endpoint']}")

            if result['status'] == 'not_implemented':
                print(f"   Status: Not implemented (stub)")
            elif result['status'] == 'error':
                print(f"   Status: Error")
                print(f"   Error: {result['error']}")
            elif result['status'] == 'empty':
                print(f"   Status: No data available")
                print(f"   Records: 0 (API returned empty array)")
                print(f"   Response time: {result['response_time_ms']}ms")
            else:  # success
                print(f"   Status: Data available")
                print(f"   Records: {result['record_count']}")
                print(f"   Response time: {result['response_time_ms']}ms")

        print("\n" + "=" * 80)

    def export_json(self) -> str:
        """
        Export results as JSON.

        Returns:
            JSON string of results
        """
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'total_endpoints': len(self.results),
            'summary': {
                'with_data': sum(1 for r in self.results if r['has_data']),
                'without_data': sum(1 for r in self.results if r['status'] == 'empty'),
                'errors': sum(1 for r in self.results if r['status'] == 'error'),
                'not_implemented': sum(1 for r in self.results if r['status'] == 'not_implemented')
            },
            'endpoints': self.results
        }
        return json.dumps(report, indent=2)


def main():
    """Main entry point for monitor script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Monitor NewYorkFed API endpoint availability'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON instead of human-readable format'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Write JSON output to file'
    )

    args = parser.parse_args()

    # Create monitor and check all endpoints
    monitor = APIEndpointMonitor()
    monitor.check_all_endpoints()

    if args.json or args.output:
        # JSON output
        json_output = monitor.export_json()

        if args.output:
            # Write to file
            with open(args.output, 'w') as f:
                f.write(json_output)
            print(f"Report written to: {args.output}")
        else:
            # Print to stdout
            print(json_output)
    else:
        # Human-readable output
        monitor.print_summary()


if __name__ == '__main__':
    main()
