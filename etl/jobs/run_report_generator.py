"""
Report Generator - Generate and email reports based on report configs.

Executes SQL queries defined in report templates (using {{SQL:query}} syntax)
and renders results as HTML tables and/or file attachments (CSV/Excel).

Usage:
    python etl/jobs/run_report_generator.py [--report-id N] [--dry-run]

Examples:
    # Generate all active reports
    python etl/jobs/run_report_generator.py

    # Generate specific report with dry run (preview without sending)
    python etl/jobs/run_report_generator.py --report-id 1 --dry-run
"""

import argparse
import csv
import io
import re
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

from common.db_utils import fetch_dict, db_transaction
from common.gmail_client import GmailClient
from common.logging_utils import ETLLogger
from etl.base.etl_job import BaseETLJob

# Optional Excel support
try:
    import xlsxwriter
    HAS_XLSXWRITER = True
except ImportError:
    HAS_XLSXWRITER = False


class ReportGeneratorJob(BaseETLJob):
    """
    Generate and send reports based on configured templates.

    Template syntax:
        Use {{SQL:query}} blocks to embed SQL queries that will be
        executed and rendered as HTML tables.

        Example:
            <h1>Daily Summary</h1>
            <p>Log entries from today:</p>
            {{SQL:SELECT COUNT(*) as total_logs FROM dba.tlogentry WHERE DATE(timestamp) = CURRENT_DATE}}

    Output formats:
        - html: Inline HTML tables in email body
        - csv: CSV file attachment only
        - excel: Excel file attachment only
        - html_csv: Both inline tables and CSV attachment
        - html_excel: Both inline tables and Excel attachment
    """

    def __init__(
        self,
        report_id: Optional[int] = None,
        dry_run: bool = False,
        run_uuid: Optional[str] = None
    ):
        """
        Initialize report generator job.

        Args:
            report_id: Optional specific report ID to generate (None = all active)
            dry_run: If True, generate reports but don't send emails
            run_uuid: Optional run UUID for tracing
        """
        super().__init__(
            run_date=date.today(),
            dataset_type='ReportGenerator',
            data_source='Internal',
            dry_run=dry_run,
            run_uuid=run_uuid
        )
        self.report_id = report_id
        self.gmail: Optional[GmailClient] = None
        self.reports: List[Dict[str, Any]] = []
        self.generated_reports: List[Dict[str, Any]] = []
        self.temp_files: List[Path] = []

    def setup(self):
        """Load report configurations and initialize Gmail client."""
        self.logger.info("Initializing Gmail client", extra={'stepcounter': 'setup'})

        if not self.dry_run:
            self.gmail = GmailClient()

        self.reports = self._load_report_configs()
        self.logger.info(
            f"Loaded {len(self.reports)} report configuration(s)",
            extra={
                'stepcounter': 'setup',
                'metadata': {'report_count': len(self.reports)}
            }
        )

    def _load_report_configs(self) -> List[Dict[str, Any]]:
        """Load active report configurations from database."""
        query = """
            SELECT
                r.*,
                s.job_name as schedule_name,
                s.cron_minute,
                s.cron_hour
            FROM dba.treportmanager r
            LEFT JOIN dba.tscheduler s ON r.schedule_id = s.scheduler_id
            WHERE r.is_active = TRUE
        """
        params = ()

        if self.report_id:
            query = query.replace('WHERE r.is_active = TRUE', 'WHERE r.is_active = TRUE AND r.report_id = %s')
            params = (self.report_id,)

        query += " ORDER BY r.report_id"
        return fetch_dict(query, params) or []

    def extract(self) -> List[Dict[str, Any]]:
        """
        Extract SQL queries from report templates.

        Returns:
            List of report dictionaries with extracted SQL blocks
        """
        extracted = []

        for report in self.reports:
            sql_blocks = self._extract_sql_blocks(report['body_template'])

            extracted.append({
                'report': report,
                'sql_blocks': sql_blocks
            })

            self.logger.info(
                f"Extracted {len(sql_blocks)} SQL block(s) from report '{report['report_name']}'",
                extra={'metadata': {'report_id': report['report_id']}}
            )

        return extracted

    def _extract_sql_blocks(self, template: str) -> List[Dict[str, str]]:
        """
        Extract {{SQL:query}} blocks from template.

        Args:
            template: Report body template

        Returns:
            List of dicts with 'query' and 'placeholder' keys
        """
        pattern = r'\{\{SQL:(.*?)\}\}'
        matches = re.findall(pattern, template, re.DOTALL)

        return [
            {
                'query': m.strip(),
                'placeholder': f'{{{{SQL:{m}}}}}'
            }
            for m in matches
        ]

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute SQL queries and render results.

        Args:
            data: List of report dictionaries with SQL blocks

        Returns:
            List of transformed reports with HTML body and attachments
        """
        transformed = []

        for item in data:
            report = item['report']
            body_html = report['body_template']
            all_results = []

            # Execute each SQL block and replace with results
            for sql_block in item['sql_blocks']:
                try:
                    # Validate query is SELECT only
                    if not self._validate_sql_query(sql_block['query']):
                        error_html = f'<p style="color: red;">Query validation failed - only SELECT queries allowed</p>'
                        body_html = body_html.replace(sql_block['placeholder'], error_html)
                        continue

                    results = fetch_dict(sql_block['query'])
                    all_results.append({
                        'query': sql_block['query'],
                        'data': results or []
                    })

                    # Replace placeholder with HTML table
                    html_table = self._render_html_table(results)
                    body_html = body_html.replace(sql_block['placeholder'], html_table)

                    self.logger.debug(
                        f"Executed query with {len(results or [])} rows",
                        extra={'metadata': {'query_preview': sql_block['query'][:100]}}
                    )

                except Exception as e:
                    self.logger.error(f"Query execution failed: {e}")
                    error_html = f'<p style="color: red;">Query error: {str(e)}</p>'
                    body_html = body_html.replace(sql_block['placeholder'], error_html)
                    all_results.append({
                        'query': sql_block['query'],
                        'data': [],
                        'error': str(e)
                    })

            # Generate attachments if needed
            attachments = []
            output_format = report.get('output_format', 'html')

            if output_format in ('csv', 'html_csv') and all_results:
                for i, result in enumerate(all_results):
                    if result.get('data'):
                        csv_path = self._generate_csv(
                            result['data'],
                            report.get('attachment_filename') or report['report_name'],
                            suffix=f'_{i}' if len(all_results) > 1 else ''
                        )
                        attachments.append(csv_path)

            elif output_format in ('excel', 'html_excel') and all_results:
                # Combine all results into one Excel file
                excel_path = self._generate_excel(
                    all_results,
                    report.get('attachment_filename') or report['report_name']
                )
                if excel_path:
                    attachments.append(excel_path)

            transformed.append({
                'report': report,
                'body_html': body_html,
                'attachments': attachments,
                'results': all_results
            })

        return transformed

    def _validate_sql_query(self, query: str) -> bool:
        """
        Validate that a SQL query is safe (SELECT only).

        Args:
            query: SQL query string

        Returns:
            True if query is valid SELECT, False otherwise
        """
        # Normalize whitespace and case
        normalized = ' '.join(query.upper().split())

        # Must start with SELECT
        if not normalized.startswith('SELECT'):
            return False

        # Block dangerous keywords
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE',
                     'GRANT', 'REVOKE', 'CREATE', 'EXEC', 'EXECUTE']

        for keyword in dangerous:
            # Check for keyword as whole word
            if re.search(rf'\b{keyword}\b', normalized):
                return False

        return True

    def _render_html_table(self, data: Optional[List[Dict]]) -> str:
        """
        Render query results as HTML table.

        Args:
            data: List of row dictionaries

        Returns:
            HTML table string
        """
        if not data:
            return '<p><em>No data found</em></p>'

        html = '''<table style="border-collapse: collapse; width: 100%; margin: 10px 0; font-family: Arial, sans-serif;">'''
        html += '<thead><tr>'

        # Header row
        for col in data[0].keys():
            html += f'''<th style="padding: 12px 8px; background-color: #FF8C42; color: white; text-align: left; border: 1px solid #ddd; font-weight: bold;">{col}</th>'''
        html += '</tr></thead><tbody>'

        # Data rows
        for i, row in enumerate(data):
            bg_color = '#f9f9f9' if i % 2 == 0 else '#ffffff'
            html += f'<tr style="background-color: {bg_color};">'
            for val in row.values():
                # Format value for display
                display_val = self._format_value(val)
                html += f'''<td style="padding: 10px 8px; border: 1px solid #ddd; text-align: left;">{display_val}</td>'''
            html += '</tr>'

        html += '</tbody></table>'
        return html

    def _format_value(self, val: Any) -> str:
        """Format a value for HTML display."""
        if val is None:
            return '<em>null</em>'
        if isinstance(val, datetime):
            return val.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(val, date):
            return val.strftime('%Y-%m-%d')
        if isinstance(val, bool):
            return 'Yes' if val else 'No'
        if isinstance(val, float):
            return f'{val:,.2f}'
        if isinstance(val, int):
            return f'{val:,}'
        return str(val)

    def _generate_csv(
        self,
        data: List[Dict],
        base_filename: str,
        suffix: str = ''
    ) -> Path:
        """
        Generate CSV file from query results.

        Args:
            data: List of row dictionaries
            base_filename: Base name for the file
            suffix: Optional suffix for multiple files

        Returns:
            Path to the generated CSV file
        """
        # Clean filename
        safe_filename = re.sub(r'[^\w\-_]', '_', base_filename)
        filename = f"{safe_filename}{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        temp_path = Path(tempfile.gettempdir()) / filename

        with open(temp_path, 'w', newline='', encoding='utf-8') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        self.temp_files.append(temp_path)
        return temp_path

    def _generate_excel(
        self,
        all_results: List[Dict],
        base_filename: str
    ) -> Optional[Path]:
        """
        Generate Excel file from query results.

        Args:
            all_results: List of result dictionaries with 'query' and 'data'
            base_filename: Base name for the file

        Returns:
            Path to the generated Excel file, or None if xlsxwriter not available
        """
        if not HAS_XLSXWRITER:
            self.logger.warning("xlsxwriter not installed, skipping Excel generation")
            return None

        # Clean filename
        safe_filename = re.sub(r'[^\w\-_]', '_', base_filename)
        filename = f"{safe_filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        temp_path = Path(tempfile.gettempdir()) / filename

        workbook = xlsxwriter.Workbook(str(temp_path))

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FF8C42',
            'font_color': 'white',
            'border': 1
        })
        cell_format = workbook.add_format({'border': 1})

        for i, result in enumerate(all_results):
            sheet_name = f"Query_{i+1}" if len(all_results) > 1 else "Data"
            worksheet = workbook.add_worksheet(sheet_name[:31])  # Excel sheet name limit

            data = result.get('data', [])
            if not data:
                worksheet.write(0, 0, "No data")
                continue

            # Write headers
            for col_num, header in enumerate(data[0].keys()):
                worksheet.write(0, col_num, header, header_format)

            # Write data rows
            for row_num, row in enumerate(data, start=1):
                for col_num, val in enumerate(row.values()):
                    # Convert datetime objects to strings
                    if isinstance(val, (datetime, date)):
                        val = val.isoformat()
                    worksheet.write(row_num, col_num, val, cell_format)

            # Auto-fit columns (approximate)
            for col_num, header in enumerate(data[0].keys()):
                max_len = len(str(header))
                for row in data[:100]:  # Sample first 100 rows
                    val = list(row.values())[col_num]
                    max_len = max(max_len, len(str(val)) if val else 0)
                worksheet.set_column(col_num, col_num, min(max_len + 2, 50))

        workbook.close()
        self.temp_files.append(temp_path)
        return temp_path

    def load(self, data: List[Dict[str, Any]]):
        """
        Send reports via email.

        Args:
            data: List of transformed report dictionaries
        """
        for item in data:
            report = item['report']
            recipients = [r.strip() for r in report['recipients'].split(',')]
            cc = [c.strip() for c in report['cc_recipients'].split(',')] if report.get('cc_recipients') else None

            try:
                if self.dry_run:
                    self.logger.info(
                        f"[DRY RUN] Would send report '{report['report_name']}' to {', '.join(recipients)}",
                        extra={
                            'metadata': {
                                'report_id': report['report_id'],
                                'recipients': recipients,
                                'attachments': len(item['attachments'])
                            }
                        }
                    )
                    # Log preview of HTML body
                    preview = item['body_html'][:500] + '...' if len(item['body_html']) > 500 else item['body_html']
                    self.logger.debug(f"Email body preview:\n{preview}")

                else:
                    self.gmail.send_email(
                        to=recipients,
                        subject=report['subject_line'],
                        body_html=item['body_html'],
                        attachments=item['attachments'],
                        cc=cc
                    )

                    self.logger.info(
                        f"Sent report '{report['report_name']}' to {', '.join(recipients)}",
                        extra={
                            'metadata': {
                                'report_id': report['report_id'],
                                'recipients': recipients,
                                'attachments': len(item['attachments'])
                            }
                        }
                    )

                # Update last run status
                self._update_report_status(report['report_id'], 'Success')
                self.generated_reports.append(report)

            except Exception as e:
                self.logger.error(
                    f"Failed to send report '{report['report_name']}': {e}",
                    extra={'metadata': {'report_id': report['report_id']}}
                )
                self._update_report_status(report['report_id'], 'Failed')

        self.records_loaded = len(self.generated_reports)

    def _update_report_status(self, report_id: int, status: str):
        """Update report last run timestamp and status."""
        try:
            with db_transaction() as cursor:
                cursor.execute(
                    """UPDATE dba.treportmanager
                       SET last_run_at = %s, last_run_status = %s
                       WHERE report_id = %s""",
                    (datetime.now(), status, report_id)
                )
        except Exception as e:
            self.logger.error(f"Failed to update report status: {e}")

    def cleanup(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp file {temp_file}: {e}")

        self.logger.info(
            f"Report generation complete",
            extra={
                'metadata': {
                    'reports_sent': len(self.generated_reports),
                    'temp_files_cleaned': len(self.temp_files)
                }
            }
        )


def main():
    """CLI entry point for report generator."""
    parser = argparse.ArgumentParser(
        description='Generate and send reports based on configured templates'
    )
    parser.add_argument(
        '--report-id',
        type=int,
        help='Specific report ID to generate (default: all active)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Generate reports but do not send emails'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Run date in YYYY-MM-DD format (default: today)'
    )

    args = parser.parse_args()

    job = ReportGeneratorJob(
        report_id=args.report_id,
        dry_run=args.dry_run
    )

    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
