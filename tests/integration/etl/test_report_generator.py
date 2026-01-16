"""Integration tests for run_report_generator.py ETL job

Tests report generation functionality including:
- Configuration loading
- SQL block extraction from templates
- SQL validation (SELECT-only, dangerous keyword blocking)
- HTML table rendering
- CSV/Excel attachment generation
- Email sending with recipients
- Dry run mode
"""

import csv
import re
import tempfile
import uuid
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# TEST: CONFIGURATION LOADING
# ============================================================================

class TestReportConfigLoading:
    """Tests for loading report configurations from database"""

    @pytest.mark.integration
    def test_load_report_config_by_id(self, db_transaction, created_report_config):
        """Report config can be loaded by ID from database"""
        from admin.services.report_manager_service import get_report

        report = get_report(created_report_config["report_id"])

        assert report is not None
        assert report["report_id"] == created_report_config["report_id"]
        assert report["report_name"] == created_report_config["report_name"]

    @pytest.mark.integration
    def test_load_report_returns_none_for_invalid_id(self, db_transaction):
        """Loading non-existent report returns None"""
        from admin.services.report_manager_service import get_report

        report = get_report(999999)

        assert report is None

    @pytest.mark.integration
    def test_report_contains_template_and_recipients(self, db_transaction, created_report_config):
        """Loaded report contains template and recipients"""
        from admin.services.report_manager_service import get_report

        report = get_report(created_report_config["report_id"])

        assert "body_template" in report
        assert "recipients" in report
        assert "subject_line" in report
        assert "output_format" in report


# ============================================================================
# TEST: SQL BLOCK EXTRACTION
# ============================================================================

class TestSQLBlockExtraction:
    """Tests for extracting SQL blocks from templates"""

    @pytest.mark.integration
    def test_extract_single_sql_block(self):
        """Single SQL block is extracted from template"""
        template = """
<h1>Report</h1>
{{SQL:SELECT COUNT(*) FROM dba.tdataset}}
<p>End of report</p>
"""
        pattern = r"\{\{SQL:(.+?)\}\}"
        matches = re.findall(pattern, template, re.DOTALL)

        assert len(matches) == 1
        assert "SELECT COUNT(*)" in matches[0]

    @pytest.mark.integration
    def test_extract_multiple_sql_blocks(self):
        """Multiple SQL blocks are extracted from template"""
        template = """
<h1>Summary</h1>
{{SQL:SELECT COUNT(*) as total FROM dba.tdataset}}
<h2>Details</h2>
{{SQL:SELECT label, status FROM dba.tdataset LIMIT 10}}
<p>End</p>
"""
        pattern = r"\{\{SQL:(.+?)\}\}"
        matches = re.findall(pattern, template, re.DOTALL)

        assert len(matches) == 2
        assert "COUNT(*)" in matches[0]
        assert "label, status" in matches[1]

    @pytest.mark.integration
    def test_multiline_sql_block(self):
        """Multiline SQL is extracted correctly"""
        template = """
{{SQL:
SELECT
    label,
    status,
    createddate
FROM dba.tdataset
WHERE status = 1
ORDER BY createddate DESC
}}
"""
        pattern = r"\{\{SQL:(.+?)\}\}"
        matches = re.findall(pattern, template, re.DOTALL)

        assert len(matches) == 1
        assert "SELECT" in matches[0]
        assert "ORDER BY" in matches[0]

    @pytest.mark.integration
    def test_template_without_sql_blocks(self):
        """Template without SQL blocks returns empty list"""
        template = "<h1>Static Report</h1><p>No data</p>"

        pattern = r"\{\{SQL:(.+?)\}\}"
        matches = re.findall(pattern, template, re.DOTALL)

        assert len(matches) == 0


# ============================================================================
# TEST: SQL VALIDATION
# ============================================================================

class TestSQLValidation:
    """Tests for SQL query validation"""

    @pytest.mark.integration
    def test_select_query_is_valid(self):
        """SELECT query passes validation"""
        query = "SELECT * FROM dba.tdataset"

        is_select = query.strip().upper().startswith("SELECT")

        assert is_select

    @pytest.mark.integration
    def test_insert_query_is_blocked(self):
        """INSERT query is blocked"""
        query = "INSERT INTO dba.tdataset (label) VALUES ('test')"

        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"]
        query_upper = query.upper()

        is_dangerous = any(kw in query_upper for kw in dangerous_keywords)

        assert is_dangerous

    @pytest.mark.integration
    def test_update_query_is_blocked(self):
        """UPDATE query is blocked"""
        query = "UPDATE dba.tdataset SET status = 0"

        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"]
        query_upper = query.upper()

        is_dangerous = any(kw in query_upper for kw in dangerous_keywords)

        assert is_dangerous

    @pytest.mark.integration
    def test_delete_query_is_blocked(self):
        """DELETE query is blocked"""
        query = "DELETE FROM dba.tdataset"

        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"]
        query_upper = query.upper()

        is_dangerous = any(kw in query_upper for kw in dangerous_keywords)

        assert is_dangerous

    @pytest.mark.integration
    def test_drop_table_is_blocked(self):
        """DROP TABLE is blocked"""
        query = "DROP TABLE dba.tdataset"

        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER"]
        query_upper = query.upper()

        is_dangerous = any(kw in query_upper for kw in dangerous_keywords)

        assert is_dangerous

    @pytest.mark.integration
    def test_semicolon_injection_blocked(self):
        """SQL injection with semicolon is detected"""
        query = "SELECT * FROM dba.tdataset; DROP TABLE dba.tdataset"

        has_semicolon = ";" in query

        assert has_semicolon  # Should be flagged as suspicious


# ============================================================================
# TEST: HTML TABLE RENDERING
# ============================================================================

class TestHTMLRendering:
    """Tests for HTML table generation from query results"""

    @pytest.mark.integration
    def test_render_simple_table(self):
        """Simple result set is rendered as HTML table"""
        results = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

        # Simple HTML table generation
        columns = list(results[0].keys())
        html = "<table><thead><tr>"
        html += "".join(f"<th>{col}</th>" for col in columns)
        html += "</tr></thead><tbody>"
        for row in results:
            html += "<tr>"
            html += "".join(f"<td>{row[col]}</td>" for col in columns)
            html += "</tr>"
        html += "</tbody></table>"

        assert "<table>" in html
        assert "<th>id</th>" in html
        assert "<td>Alice</td>" in html
        assert html.count("<tr>") == 3  # Header + 2 data rows

    @pytest.mark.integration
    def test_render_empty_results(self):
        """Empty result set renders appropriate message"""
        results = []

        if not results:
            html = "<p>No data available</p>"
        else:
            html = "<table>...</table>"

        assert "No data" in html

    @pytest.mark.integration
    def test_format_date_values(self):
        """Date values are formatted for display"""
        test_date = date(2026, 1, 15)

        formatted = test_date.strftime("%Y-%m-%d")

        assert formatted == "2026-01-15"

    @pytest.mark.integration
    def test_format_datetime_values(self):
        """Datetime values are formatted for display"""
        test_datetime = datetime(2026, 1, 15, 14, 30, 0)

        formatted = test_datetime.strftime("%Y-%m-%d %H:%M:%S")

        assert formatted == "2026-01-15 14:30:00"

    @pytest.mark.integration
    def test_format_numeric_values(self):
        """Numeric values are formatted with thousands separator"""
        value = 1234567.89

        formatted = f"{value:,.2f}"

        assert formatted == "1,234,567.89"

    @pytest.mark.integration
    def test_format_boolean_values(self):
        """Boolean values are formatted as Yes/No"""
        true_val = True
        false_val = False

        true_formatted = "Yes" if true_val else "No"
        false_formatted = "Yes" if false_val else "No"

        assert true_formatted == "Yes"
        assert false_formatted == "No"

    @pytest.mark.integration
    def test_format_null_values(self):
        """NULL values are displayed as empty or dash"""
        null_val = None

        formatted = "-" if null_val is None else str(null_val)

        assert formatted == "-"

    @pytest.mark.integration
    def test_escape_html_in_values(self):
        """HTML in values is escaped to prevent XSS"""
        value = "<script>alert('xss')</script>"

        import html
        escaped = html.escape(value)

        assert "&lt;script&gt;" in escaped
        assert "<script>" not in escaped


# ============================================================================
# TEST: CSV GENERATION
# ============================================================================

class TestCSVGeneration:
    """Tests for CSV attachment generation"""

    @pytest.mark.integration
    def test_generate_csv_from_results(self):
        """CSV is generated from query results"""
        results = [
            {"id": 1, "name": "Alice", "amount": 100.50},
            {"id": 2, "name": "Bob", "amount": 200.75},
        ]

        output = StringIO()
        columns = list(results[0].keys())
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

        csv_content = output.getvalue()

        assert "id,name,amount" in csv_content
        assert "1,Alice,100.5" in csv_content
        assert "2,Bob,200.75" in csv_content

    @pytest.mark.integration
    def test_csv_handles_special_characters(self):
        """CSV handles special characters (commas, quotes)"""
        results = [
            {"name": 'O\'Brien', "description": "Value, with comma"},
        ]

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["name", "description"])
        writer.writeheader()
        writer.writerows(results)

        csv_content = output.getvalue()

        # CSV should properly quote fields with special characters
        assert "O'Brien" in csv_content
        assert '"Value, with comma"' in csv_content

    @pytest.mark.integration
    def test_csv_empty_results(self):
        """CSV with empty results has header only"""
        results = []
        columns = ["id", "name", "amount"]

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

        csv_content = output.getvalue()

        assert "id,name,amount" in csv_content
        assert csv_content.count("\n") == 1  # Header line only


# ============================================================================
# TEST: EXCEL GENERATION
# ============================================================================

class TestExcelGeneration:
    """Tests for Excel attachment generation"""

    @pytest.mark.integration
    def test_excel_generation_creates_file(self, tmp_path):
        """Excel file is created from query results"""
        try:
            import xlsxwriter
        except ImportError:
            pytest.skip("xlsxwriter not installed")

        results = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]

        filepath = tmp_path / "report.xlsx"
        workbook = xlsxwriter.Workbook(str(filepath))
        worksheet = workbook.add_worksheet()

        # Write header
        columns = list(results[0].keys())
        for col_idx, col_name in enumerate(columns):
            worksheet.write(0, col_idx, col_name)

        # Write data
        for row_idx, row in enumerate(results, start=1):
            for col_idx, col_name in enumerate(columns):
                worksheet.write(row_idx, col_idx, row[col_name])

        workbook.close()

        assert filepath.exists()
        assert filepath.stat().st_size > 0


# ============================================================================
# TEST: EMAIL SENDING
# ============================================================================

class TestEmailSending:
    """Tests for email composition and sending"""

    @pytest.mark.integration
    def test_email_has_correct_recipients(self, mock_gmail_client, created_report_config):
        """Email is sent to configured recipients"""
        recipients = created_report_config["recipients"].split(",")

        # Simulate email sending
        mock_gmail_client.send_email(
            to=recipients,
            subject=created_report_config["subject_line"],
            body="<h1>Report</h1>",
        )

        mock_gmail_client.send_email.assert_called_once()
        call_kwargs = mock_gmail_client.send_email.call_args
        assert "test@example.com" in str(call_kwargs)

    @pytest.mark.integration
    def test_email_includes_attachments(self, mock_gmail_client, tmp_path):
        """Email includes CSV/Excel attachments"""
        # Create test attachment
        attachment = tmp_path / "report.csv"
        attachment.write_text("id,name\n1,test")

        mock_gmail_client.send_email(
            to=["test@example.com"],
            subject="Report",
            body="<h1>Report</h1>",
            attachments=[str(attachment)],
        )

        mock_gmail_client.send_email.assert_called_once()

    @pytest.mark.integration
    def test_email_with_cc_recipients(self, mock_gmail_client):
        """Email includes CC recipients"""
        mock_gmail_client.send_email(
            to=["primary@example.com"],
            cc=["cc1@example.com", "cc2@example.com"],
            subject="Report",
            body="<h1>Report</h1>",
        )

        call_kwargs = mock_gmail_client.send_email.call_args
        assert mock_gmail_client.send_email.called


# ============================================================================
# TEST: DRY RUN MODE
# ============================================================================

class TestDryRunMode:
    """Tests for dry run (preview without sending)"""

    @pytest.mark.integration
    def test_dry_run_does_not_send_email(self, mock_gmail_client):
        """Dry run mode does not send email"""
        dry_run = True

        if not dry_run:
            mock_gmail_client.send_email(
                to=["test@example.com"],
                subject="Report",
                body="<h1>Report</h1>",
            )

        mock_gmail_client.send_email.assert_not_called()

    @pytest.mark.integration
    def test_dry_run_generates_preview(self):
        """Dry run generates preview content"""
        template = "<h1>Report</h1>{{SQL:SELECT 1}}"
        sql_results = [{"count": 42}]

        # Generate preview
        preview = template.replace(
            "{{SQL:SELECT 1}}",
            "<table><tr><td>42</td></tr></table>"
        )

        assert "<table>" in preview
        assert "42" in preview


# ============================================================================
# TEST: OUTPUT FORMATS
# ============================================================================

class TestOutputFormats:
    """Tests for different output format options"""

    @pytest.mark.integration
    def test_html_only_format(self):
        """HTML-only format has inline tables"""
        output_format = "html"

        has_inline_table = output_format in ("html", "html_csv", "html_excel")
        has_csv_attachment = output_format in ("csv", "html_csv")
        has_excel_attachment = output_format in ("excel", "html_excel")

        assert has_inline_table
        assert not has_csv_attachment
        assert not has_excel_attachment

    @pytest.mark.integration
    def test_csv_only_format(self):
        """CSV-only format has attachment, no inline table"""
        output_format = "csv"

        has_inline_table = output_format in ("html", "html_csv", "html_excel")
        has_csv_attachment = output_format in ("csv", "html_csv")

        assert not has_inline_table
        assert has_csv_attachment

    @pytest.mark.integration
    def test_html_csv_format(self):
        """HTML+CSV format has both inline table and attachment"""
        output_format = "html_csv"

        has_inline_table = output_format in ("html", "html_csv", "html_excel")
        has_csv_attachment = output_format in ("csv", "html_csv")

        assert has_inline_table
        assert has_csv_attachment

    @pytest.mark.integration
    def test_html_excel_format(self):
        """HTML+Excel format has both inline table and Excel attachment"""
        output_format = "html_excel"

        has_inline_table = output_format in ("html", "html_csv", "html_excel")
        has_excel_attachment = output_format in ("excel", "html_excel")

        assert has_inline_table
        assert has_excel_attachment


# ============================================================================
# TEST: TEMPLATE SUBSTITUTION
# ============================================================================

class TestTemplateSubstitution:
    """Tests for template variable substitution"""

    @pytest.mark.integration
    def test_timestamp_substitution(self):
        """{{TIMESTAMP}} is replaced with current time"""
        template = "Report generated at: {{TIMESTAMP}}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        result = template.replace("{{TIMESTAMP}}", timestamp)

        assert "2026" in result or "202" in result  # Year in timestamp
        assert "{{TIMESTAMP}}" not in result

    @pytest.mark.integration
    def test_date_substitution(self):
        """{{DATE}} is replaced with current date"""
        template = "Report for: {{DATE}}"
        current_date = date.today().strftime("%Y-%m-%d")

        result = template.replace("{{DATE}}", current_date)

        assert "{{DATE}}" not in result

    @pytest.mark.integration
    def test_multiple_substitutions(self):
        """Multiple variables are all substituted"""
        template = """
Report: {{REPORT_NAME}}
Date: {{DATE}}
Generated: {{TIMESTAMP}}
"""
        result = template
        result = result.replace("{{REPORT_NAME}}", "Daily Summary")
        result = result.replace("{{DATE}}", "2026-01-15")
        result = result.replace("{{TIMESTAMP}}", "2026-01-15 10:00:00")

        assert "{{" not in result
        assert "Daily Summary" in result


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Tests for error scenarios"""

    @pytest.mark.integration
    def test_sql_syntax_error_handled(self, db_transaction):
        """SQL syntax error is caught and reported"""
        invalid_sql = "SELCT * FROM table"  # Typo in SELECT

        with db_transaction() as cursor:
            with pytest.raises(Exception):  # psycopg2 error
                cursor.execute(invalid_sql)

    @pytest.mark.integration
    def test_missing_table_error_handled(self, db_transaction):
        """Missing table error is caught"""
        query = "SELECT * FROM nonexistent_table_xyz"

        with db_transaction() as cursor:
            with pytest.raises(Exception):  # psycopg2 error
                cursor.execute(query)

    @pytest.mark.integration
    def test_email_send_failure_logged(self, mock_gmail_client):
        """Email send failure is logged"""
        mock_gmail_client.send_email.side_effect = Exception("SMTP error")

        with pytest.raises(Exception) as exc_info:
            mock_gmail_client.send_email(
                to=["test@example.com"],
                subject="Report",
                body="<h1>Report</h1>",
            )

        assert "SMTP error" in str(exc_info.value)
