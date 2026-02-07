#!/usr/bin/env python3
"""
NewYorkFed API Status Report Generator

Generates comprehensive reports showing:
- API data availability status
- Database table record counts
- Job execution status
- Data freshness metrics
- Discrepancies between API and database

Usage:
    python scripts/newyorkfed_api_status_report.py
    python scripts/newyorkfed_api_status_report.py --format json
    python scripts/newyorkfed_api_status_report.py --output report.html
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_db_connection
from etl.clients.newyorkfed_client import NewYorkFedAPIClient


class StatusReportGenerator:
    """Generate comprehensive status reports for NewYorkFed data feeds."""

    FEEDS_CONFIG = [
        {
            'name': 'Reference Rates',
            'table': 'newyorkfed_reference_rates',
            'method': 'get_reference_rates_latest',
            'status': 'active'
        },
        {
            'name': 'SOMA Holdings',
            'table': 'newyorkfed_soma_holdings',
            'method': 'get_soma_holdings',
            'status': 'active'
        },
        {
            'name': 'Repo Operations',
            'table': 'newyorkfed_repo_operations',
            'method': 'get_repo_operations',
            'status': 'active'
        },
        {
            'name': 'Securities Lending',
            'table': 'newyorkfed_securities_lending',
            'method': 'get_securities_lending',
            'status': 'active'
        },
        {
            'name': 'Guide Sheets',
            'table': 'newyorkfed_guide_sheets',
            'method': 'get_guide_sheets',
            'status': 'active'
        },
        {
            'name': 'Agency MBS',
            'table': 'newyorkfed_agency_mbs',
            'method': 'get_agency_mbs',
            'status': 'waiting'
        },
        {
            'name': 'FX Swaps',
            'table': 'newyorkfed_fx_swaps',
            'method': 'get_fx_swaps',
            'status': 'waiting'
        },
        {
            'name': 'Treasury Operations',
            'table': 'newyorkfed_treasury_operations',
            'method': 'get_treasury_operations',
            'status': 'waiting'
        },
        {
            'name': 'PD Statistics',
            'table': 'newyorkfed_pd_statistics',
            'method': None,
            'status': 'stub'
        },
        {
            'name': 'Market Share',
            'table': 'newyorkfed_market_share',
            'method': None,
            'status': 'stub'
        }
    ]

    def __init__(self):
        """Initialize status report generator."""
        self.client = NewYorkFedAPIClient()
        self.report_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'feeds': []
        }

    def get_table_stats(self, conn, table_name: str) -> Dict[str, Any]:
        """
        Get statistics for a database table.

        Args:
            conn: Database connection
            table_name: Name of the table (without schema)

        Returns:
            Dictionary with table statistics
        """
        stats = {
            'record_count': 0,
            'latest_date': None,
            'earliest_date': None,
            'last_created': None,
            'size_bytes': 0
        }

        try:
            with conn.cursor() as cur:
                # Get record count
                cur.execute(f"SELECT COUNT(*) FROM feeds.{table_name}")
                stats['record_count'] = cur.fetchone()[0]

                # Try to get date range (different tables have different date columns)
                date_columns = [
                    'rate_date', 'as_of_date', 'operation_date', 'guide_date',
                    'swap_date', 'report_date'
                ]

                for date_col in date_columns:
                    try:
                        cur.execute(f"""
                            SELECT MIN({date_col}), MAX({date_col})
                            FROM feeds.{table_name}
                        """)
                        row = cur.fetchone()
                        if row and row[0]:
                            stats['earliest_date'] = row[0].isoformat() if row[0] else None
                            stats['latest_date'] = row[1].isoformat() if row[1] else None
                            break
                    except:
                        continue

                # Get last created timestamp
                try:
                    cur.execute(f"""
                        SELECT MAX(created_date)
                        FROM feeds.{table_name}
                    """)
                    row = cur.fetchone()
                    if row and row[0]:
                        stats['last_created'] = row[0].isoformat()
                except:
                    pass

                # Get table size
                cur.execute(f"""
                    SELECT pg_total_relation_size('feeds.{table_name}')
                """)
                stats['size_bytes'] = cur.fetchone()[0]

        except Exception as e:
            stats['error'] = str(e)

        return stats

    def check_api_availability(self, method_name: str) -> Dict[str, Any]:
        """
        Check if API endpoint has data available.

        Args:
            method_name: Name of client method to call

        Returns:
            Dictionary with API availability info
        """
        result = {
            'has_data': False,
            'record_count': 0,
            'error': None
        }

        if method_name is None:
            result['error'] = 'Not implemented'
            return result

        try:
            method = getattr(self.client, method_name)
            data = method()
            result['record_count'] = len(data) if data else 0
            result['has_data'] = result['record_count'] > 0
        except Exception as e:
            result['error'] = str(e)

        return result

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive status report.

        Returns:
            Dictionary with full report data
        """
        conn = get_db_connection()

        try:
            for feed_config in self.FEEDS_CONFIG:
                feed_report = {
                    'name': feed_config['name'],
                    'table': feed_config['table'],
                    'status': feed_config['status'],
                    'database': {},
                    'api': {},
                    'health': 'unknown'
                }

                # Get database stats
                feed_report['database'] = self.get_table_stats(conn, feed_config['table'])

                # Check API availability
                if feed_config['method']:
                    feed_report['api'] = self.check_api_availability(feed_config['method'])
                else:
                    feed_report['api'] = {'has_data': False, 'record_count': 0, 'error': 'Not implemented'}

                # Determine health status
                db_has_data = feed_report['database']['record_count'] > 0
                api_has_data = feed_report['api']['has_data']

                if feed_config['status'] == 'stub':
                    feed_report['health'] = 'not_implemented'
                elif feed_config['status'] == 'waiting':
                    feed_report['health'] = 'waiting_for_data'
                elif db_has_data and api_has_data:
                    feed_report['health'] = 'healthy'
                elif db_has_data and not api_has_data:
                    feed_report['health'] = 'stale_data'
                elif not db_has_data and api_has_data:
                    feed_report['health'] = 'needs_sync'
                else:
                    feed_report['health'] = 'no_data'

                self.report_data['feeds'].append(feed_report)

        finally:
            conn.close()

        return self.report_data

    def print_text_report(self):
        """Print human-readable text report."""
        print("=" * 80)
        print("NewYorkFed Feeds Status Report")
        print("=" * 80)
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")

        # Summary
        health_counts = {}
        for feed in self.report_data['feeds']:
            health = feed['health']
            health_counts[health] = health_counts.get(health, 0) + 1

        print("Summary:")
        print(f"  ✅ Healthy (data in DB + API):      {health_counts.get('healthy', 0)}")
        print(f"  ⏳ Waiting for data:                {health_counts.get('waiting_for_data', 0)}")
        print(f"  📦 Stale (data in DB, not API):     {health_counts.get('stale_data', 0)}")
        print(f"  🔄 Needs sync (data in API not DB): {health_counts.get('needs_sync', 0)}")
        print(f"  ⚫ No data anywhere:                {health_counts.get('no_data', 0)}")
        print(f"  🚧 Not implemented:                 {health_counts.get('not_implemented', 0)}")
        print()

        # Detailed feed status
        print("Detailed Status:")
        print("-" * 80)

        for feed in self.report_data['feeds']:
            health_icon = {
                'healthy': '✅',
                'waiting_for_data': '⏳',
                'stale_data': '📦',
                'needs_sync': '🔄',
                'no_data': '⚫',
                'not_implemented': '🚧'
            }.get(feed['health'], '❓')

            print(f"\n{health_icon} {feed['name']}")
            print(f"   Table: feeds.{feed['table']}")
            print(f"   Status: {feed['status']}")

            # Database info
            db = feed['database']
            print(f"   Database:")
            print(f"     Records: {db['record_count']:,}")
            if db.get('latest_date'):
                print(f"     Date range: {db['earliest_date']} to {db['latest_date']}")
            if db.get('last_created'):
                print(f"     Last updated: {db['last_created']}")
            if db.get('size_bytes', 0) > 0:
                size_mb = db['size_bytes'] / (1024 * 1024)
                print(f"     Size: {size_mb:.2f} MB")

            # API info
            api = feed['api']
            print(f"   API:")
            if api.get('error'):
                print(f"     Error: {api['error']}")
            else:
                print(f"     Records available: {api['record_count']}")
                status_text = "✅ Has data" if api['has_data'] else "⚫ No data"
                print(f"     Status: {status_text}")

        print("\n" + "=" * 80)

    def export_json(self) -> str:
        """Export report as JSON."""
        return json.dumps(self.report_data, indent=2)

    def export_html(self) -> str:
        """Export report as HTML."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NewYorkFed Feeds Status Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .summary-card {{ padding: 15px; border-radius: 5px; background: #f9f9f9; border-left: 4px solid #0066cc; }}
        .summary-card .number {{ font-size: 2em; font-weight: bold; color: #0066cc; }}
        .summary-card .label {{ color: #666; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #0066cc; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .health-icon {{ font-size: 1.2em; margin-right: 5px; }}
        .status-healthy {{ color: #28a745; }}
        .status-waiting {{ color: #ffc107; }}
        .status-stub {{ color: #6c757d; }}
        .timestamp {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NewYorkFed Feeds Status Report</h1>
        <div class="timestamp">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>

        <div class="summary">
"""

        # Add summary cards
        health_counts = {}
        total_records = 0
        for feed in self.report_data['feeds']:
            health = feed['health']
            health_counts[health] = health_counts.get(health, 0) + 1
            total_records += feed['database']['record_count']

        html += f"""
            <div class="summary-card">
                <div class="number">{len(self.report_data['feeds'])}</div>
                <div class="label">Total Feeds</div>
            </div>
            <div class="summary-card">
                <div class="number">{health_counts.get('healthy', 0)}</div>
                <div class="label">Healthy Feeds</div>
            </div>
            <div class="summary-card">
                <div class="number">{total_records:,}</div>
                <div class="label">Total Records</div>
            </div>
            <div class="summary-card">
                <div class="number">{health_counts.get('waiting_for_data', 0)}</div>
                <div class="label">Waiting for Data</div>
            </div>
        </div>

        <h2>Feed Details</h2>
        <table>
            <tr>
                <th>Feed Name</th>
                <th>Status</th>
                <th>DB Records</th>
                <th>API Records</th>
                <th>Latest Date</th>
                <th>Health</th>
            </tr>
"""

        # Add table rows
        for feed in self.report_data['feeds']:
            health_class = f"status-{feed['health'].replace('_', '-')}"
            health_icon = {
                'healthy': '✅',
                'waiting_for_data': '⏳',
                'stale_data': '📦',
                'needs_sync': '🔄',
                'no_data': '⚫',
                'not_implemented': '🚧'
            }.get(feed['health'], '❓')

            latest_date = feed['database'].get('latest_date', 'N/A')
            api_count = feed['api'].get('record_count', 0)
            db_count = feed['database']['record_count']

            html += f"""
            <tr>
                <td><strong>{feed['name']}</strong><br><small>feeds.{feed['table']}</small></td>
                <td>{feed['status']}</td>
                <td>{db_count:,}</td>
                <td>{api_count}</td>
                <td>{latest_date}</td>
                <td class="{health_class}"><span class="health-icon">{health_icon}</span>{feed['health'].replace('_', ' ').title()}</td>
            </tr>
"""

        html += """
        </table>
    </div>
</body>
</html>
"""
        return html


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate NewYorkFed API status report'
    )
    parser.add_argument(
        '--format',
        choices=['text', 'json', 'html'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Write output to file'
    )

    args = parser.parse_args()

    # Generate report
    generator = StatusReportGenerator()
    generator.generate_report()

    # Output in requested format
    if args.format == 'json':
        output = generator.export_json()
    elif args.format == 'html':
        output = generator.export_html()
    else:
        generator.print_text_report()
        return

    # Write to file or stdout
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Report written to: {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
