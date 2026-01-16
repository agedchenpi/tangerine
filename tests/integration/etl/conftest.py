"""ETL job test fixtures

Provides fixtures for testing ETL jobs:
- Temporary file system directories
- Mock Gmail client
- Sample configurations
- Test data files
"""

import csv
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# FILE SYSTEM FIXTURES
# ============================================================================

@pytest.fixture
def temp_source_dir(tmp_path):
    """Create a temporary source directory for test files"""
    source_dir = tmp_path / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    return source_dir


@pytest.fixture
def temp_archive_dir(tmp_path):
    """Create a temporary archive directory"""
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir


@pytest.fixture
def temp_inbox_dir(tmp_path):
    """Create a temporary inbox directory for downloaded attachments"""
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    return inbox_dir


# ============================================================================
# TEST FILE FIXTURES
# ============================================================================

@pytest.fixture
def sample_csv_file(temp_source_dir):
    """Create a sample CSV file for import testing"""
    filename = f"AdminTest_data_20260115.csv"
    filepath = temp_source_dir / filename

    data = [
        {"id": "1", "name": "Alice", "amount": "100.50", "date": "2026-01-15"},
        {"id": "2", "name": "Bob", "amount": "200.75", "date": "2026-01-15"},
        {"id": "3", "name": "Charlie", "amount": "300.25", "date": "2026-01-15"},
    ]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "amount", "date"])
        writer.writeheader()
        writer.writerows(data)

    return filepath


@pytest.fixture
def sample_json_file(temp_source_dir):
    """Create a sample JSON file for import testing"""
    filename = f"AdminTest_data_20260115.json"
    filepath = temp_source_dir / filename

    data = [
        {"id": 1, "name": "Alice", "amount": 100.50, "active": True},
        {"id": 2, "name": "Bob", "amount": 200.75, "active": False},
        {"id": 3, "name": "Charlie", "amount": 300.25, "active": True},
    ]

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    return filepath


@pytest.fixture
def sample_csv_with_nulls(temp_source_dir):
    """Create a CSV file with null/empty values for edge case testing"""
    filename = f"AdminTest_nulls_20260115.csv"
    filepath = temp_source_dir / filename

    # Write raw CSV with empty fields
    content = """id,name,amount,date
1,Alice,100.50,2026-01-15
2,,200.75,
3,Charlie,,2026-01-15
"""
    filepath.write_text(content)
    return filepath


@pytest.fixture
def sample_csv_different_columns(temp_source_dir):
    """Create a CSV with different columns than expected (for strategy testing)"""
    filename = f"AdminTest_different_20260115.csv"
    filepath = temp_source_dir / filename

    data = [
        {"id": "1", "name": "Alice", "new_column": "extra", "another_new": "data"},
        {"id": "2", "name": "Bob", "new_column": "value", "another_new": "more"},
    ]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "new_column", "another_new"])
        writer.writeheader()
        writer.writerows(data)

    return filepath


# ============================================================================
# IMPORT CONFIG FIXTURES
# ============================================================================

@pytest.fixture
def etl_import_config(created_datasource, created_datasettype, temp_source_dir, temp_archive_dir):
    """Create an import config suitable for ETL job testing

    Uses actual temp directories for file operations.
    """
    unique_id = uuid.uuid4().hex[:8]
    return {
        "config_name": f"AdminTest_ETL_{unique_id}",
        "datasource": created_datasource["sourcename"],
        "datasettype": created_datasettype["typename"],
        "source_directory": str(temp_source_dir),
        "archive_directory": str(temp_archive_dir),
        "file_pattern": r"AdminTest_data_\d{8}\.csv",
        "file_type": "CSV",
        "target_table": f"feeds.admintest_etl_{unique_id}",
        "importstrategyid": 1,  # Auto-add columns
        "metadata_label_source": "filename",
        "metadata_label_location": "2",
        "dateconfig": "filename",
        "datelocation": "1",
        "dateformat": "yyyyMMdd",
        "delimiter": "_",
        "is_active": True,
    }


@pytest.fixture
def created_etl_import_config(db_transaction, etl_import_config):
    """Insert ETL import config into database"""
    with db_transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO dba.timportconfig (
                config_name, datasource, datasettype,
                source_directory, archive_directory, file_pattern, file_type,
                target_table, importstrategyid,
                metadata_label_source, metadata_label_location,
                dateconfig, datelocation, dateformat, delimiter,
                is_active
            ) VALUES (
                %(config_name)s, %(datasource)s, %(datasettype)s,
                %(source_directory)s, %(archive_directory)s, %(file_pattern)s, %(file_type)s,
                %(target_table)s, %(importstrategyid)s,
                %(metadata_label_source)s, %(metadata_label_location)s,
                %(dateconfig)s, %(datelocation)s, %(dateformat)s, %(delimiter)s,
                %(is_active)s
            )
            RETURNING config_id
        """,
            etl_import_config,
        )
        config_id = cursor.fetchone()["config_id"]

        cursor.execute(
            "SELECT * FROM dba.timportconfig WHERE config_id = %s",
            (config_id,),
        )
        result = cursor.fetchone()

    return dict(result)


# ============================================================================
# GMAIL CLIENT MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_gmail_client():
    """Create a mocked Gmail client for testing"""
    mock_client = MagicMock()

    # Default return values
    mock_client.get_unread_emails.return_value = []
    mock_client.get_attachments.return_value = []
    mock_client.download_attachment.return_value = None
    mock_client.apply_label.return_value = None
    mock_client.remove_label.return_value = None
    mock_client.mark_as_read.return_value = None
    mock_client.send_email.return_value = None

    return mock_client


@pytest.fixture
def sample_email():
    """Sample email data for inbox processor testing"""
    return {
        "id": f"msg_{uuid.uuid4().hex[:12]}",
        "threadId": f"thread_{uuid.uuid4().hex[:12]}",
        "subject": "AdminTest Daily Report - 2026-01-15",
        "sender": "reports@example.com",
        "date": datetime(2026, 1, 15, 9, 0, 0),
        "snippet": "Please find attached the daily report...",
    }


@pytest.fixture
def sample_attachment():
    """Sample attachment data for inbox processor testing"""
    return {
        "id": f"att_{uuid.uuid4().hex[:12]}",
        "filename": "daily_report_20260115.pdf",
        "mimeType": "application/pdf",
        "size": 12345,
    }


# ============================================================================
# INBOX CONFIG FIXTURES
# ============================================================================

@pytest.fixture
def sample_inbox_config(temp_inbox_dir):
    """Sample inbox config for Gmail processor testing"""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "config_name": f"AdminTest_Inbox_{unique_id}",
        "subject_pattern": r".*Daily Report.*",
        "sender_pattern": r".*@example\.com",
        "attachment_pattern": "*.pdf",
        "target_directory": str(temp_inbox_dir),
        "processed_label": "Processed",
        "error_label": "ProcessingError",
        "date_prefix_format": "yyyyMMdd",
        "save_eml": False,
        "is_active": True,
    }


@pytest.fixture
def created_inbox_config(db_transaction, sample_inbox_config):
    """Insert inbox config into database"""
    with db_transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO dba.tinboxconfig (
                config_name, subject_pattern, sender_pattern, attachment_pattern,
                target_directory, processed_label, error_label,
                date_prefix_format, save_eml, is_active
            ) VALUES (
                %(config_name)s, %(subject_pattern)s, %(sender_pattern)s, %(attachment_pattern)s,
                %(target_directory)s, %(processed_label)s, %(error_label)s,
                %(date_prefix_format)s, %(save_eml)s, %(is_active)s
            )
            RETURNING inbox_config_id
        """,
            sample_inbox_config,
        )
        config_id = cursor.fetchone()["inbox_config_id"]

        cursor.execute(
            "SELECT * FROM dba.tinboxconfig WHERE inbox_config_id = %s",
            (config_id,),
        )
        result = cursor.fetchone()

    return dict(result)


# ============================================================================
# REPORT CONFIG FIXTURES
# ============================================================================

@pytest.fixture
def sample_report_config():
    """Sample report config for report generator testing"""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "report_name": f"AdminTest_Report_{unique_id}",
        "recipients": "test@example.com",
        "cc_recipients": "",
        "subject_line": "AdminTest Daily Summary Report",
        "body_template": """
<h1>Daily Summary</h1>
<p>Here is your daily summary:</p>
{{SQL:SELECT COUNT(*) as total FROM dba.tdataset}}
<p>Report generated at: {{TIMESTAMP}}</p>
""",
        "output_format": "html",
        "is_active": True,
    }


@pytest.fixture
def created_report_config(db_transaction, sample_report_config):
    """Insert report config into database"""
    with db_transaction() as cursor:
        cursor.execute(
            """
            INSERT INTO dba.treportmanager (
                report_name, recipients, cc_recipients,
                subject_line, body_template, output_format, is_active
            ) VALUES (
                %(report_name)s, %(recipients)s, %(cc_recipients)s,
                %(subject_line)s, %(body_template)s, %(output_format)s, %(is_active)s
            )
            RETURNING report_id
        """,
            sample_report_config,
        )
        report_id = cursor.fetchone()["report_id"]

        cursor.execute(
            "SELECT * FROM dba.treportmanager WHERE report_id = %s",
            (report_id,),
        )
        result = cursor.fetchone()

    return dict(result)


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def mock_etl_logger():
    """Mock ETL logger to prevent actual logging during tests"""
    with patch("common.logging_utils.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger
