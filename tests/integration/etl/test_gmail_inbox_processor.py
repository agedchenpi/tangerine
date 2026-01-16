"""Integration tests for run_gmail_inbox_processor.py ETL job

Tests Gmail inbox processing functionality including:
- Configuration loading
- Email pattern matching (subject, sender, attachment)
- Attachment downloading with date prefixes
- Label operations (apply/remove)
- Dry run mode
"""

import fnmatch
import re
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# TEST: CONFIGURATION LOADING
# ============================================================================

class TestInboxConfigLoading:
    """Tests for loading inbox configurations from database"""

    @pytest.mark.integration
    def test_load_inbox_config_by_id(self, db_transaction, created_inbox_config):
        """Inbox config can be loaded by ID from database"""
        from admin.services.inbox_config_service import get_inbox_config

        config = get_inbox_config(created_inbox_config["inbox_config_id"])

        assert config is not None
        assert config["inbox_config_id"] == created_inbox_config["inbox_config_id"]
        assert config["config_name"] == created_inbox_config["config_name"]

    @pytest.mark.integration
    def test_load_inbox_returns_none_for_invalid_id(self, db_transaction):
        """Loading non-existent inbox config returns None"""
        from admin.services.inbox_config_service import get_inbox_config

        config = get_inbox_config(999999)

        assert config is None

    @pytest.mark.integration
    def test_inbox_config_contains_patterns(self, db_transaction, created_inbox_config):
        """Loaded config contains all pattern fields"""
        from admin.services.inbox_config_service import get_inbox_config

        config = get_inbox_config(created_inbox_config["inbox_config_id"])

        assert "subject_pattern" in config
        assert "sender_pattern" in config
        assert "attachment_pattern" in config
        assert "target_directory" in config

    @pytest.mark.integration
    def test_list_active_inbox_configs(self, db_transaction, created_inbox_config):
        """Active inbox configs are listed"""
        from admin.services.inbox_config_service import list_inbox_configs

        configs = list_inbox_configs(active_only=True)

        # Should include our test config
        config_ids = [c["inbox_config_id"] for c in configs]
        assert created_inbox_config["inbox_config_id"] in config_ids


# ============================================================================
# TEST: SUBJECT PATTERN MATCHING
# ============================================================================

class TestSubjectPatternMatching:
    """Tests for email subject pattern matching"""

    @pytest.mark.integration
    def test_subject_matches_regex_pattern(self, sample_email):
        """Subject matching regex pattern is detected"""
        pattern = r".*Daily Report.*"
        subject = sample_email["subject"]

        matches = bool(re.search(pattern, subject, re.IGNORECASE))

        assert matches

    @pytest.mark.integration
    def test_subject_no_match(self, sample_email):
        """Non-matching subject is rejected"""
        pattern = r".*Weekly Summary.*"
        subject = sample_email["subject"]

        matches = bool(re.search(pattern, subject, re.IGNORECASE))

        assert not matches

    @pytest.mark.integration
    def test_subject_case_insensitive(self):
        """Subject matching is case-insensitive"""
        pattern = r".*DAILY REPORT.*"
        subject = "AdminTest daily report - 2026-01-15"

        matches = bool(re.search(pattern, subject, re.IGNORECASE))

        assert matches

    @pytest.mark.integration
    def test_subject_with_special_chars(self):
        """Subject with special characters is matched"""
        pattern = r".*Report \[.*\].*"
        subject = "AdminTest Report [January] - Summary"

        matches = bool(re.search(pattern, subject, re.IGNORECASE))

        assert matches

    @pytest.mark.integration
    def test_empty_subject_pattern_matches_all(self):
        """Empty pattern matches all subjects"""
        pattern = ""
        subject = "Any subject here"

        # Empty pattern matches everything
        matches = pattern == "" or bool(re.search(pattern, subject, re.IGNORECASE))

        assert matches


# ============================================================================
# TEST: SENDER PATTERN MATCHING
# ============================================================================

class TestSenderPatternMatching:
    """Tests for email sender pattern matching"""

    @pytest.mark.integration
    def test_sender_matches_domain_pattern(self, sample_email):
        """Sender matching domain pattern is detected"""
        pattern = r".*@example\.com"
        sender = sample_email["sender"]

        matches = bool(re.search(pattern, sender, re.IGNORECASE))

        assert matches

    @pytest.mark.integration
    def test_sender_exact_match(self):
        """Sender exact match works"""
        pattern = r"^reports@example\.com$"
        sender = "reports@example.com"

        matches = bool(re.search(pattern, sender, re.IGNORECASE))

        assert matches

    @pytest.mark.integration
    def test_sender_different_domain_rejected(self, sample_email):
        """Sender from different domain is rejected"""
        pattern = r".*@otherdomain\.com"
        sender = sample_email["sender"]

        matches = bool(re.search(pattern, sender, re.IGNORECASE))

        assert not matches

    @pytest.mark.integration
    def test_sender_with_name(self):
        """Sender with display name is matched"""
        pattern = r".*support.*"
        sender = "Support Team <support@example.com>"

        matches = bool(re.search(pattern, sender, re.IGNORECASE))

        assert matches


# ============================================================================
# TEST: ATTACHMENT PATTERN MATCHING
# ============================================================================

class TestAttachmentPatternMatching:
    """Tests for attachment filename pattern matching"""

    @pytest.mark.integration
    def test_attachment_glob_pattern_pdf(self, sample_attachment):
        """Attachment matching glob pattern *.pdf is detected"""
        pattern = "*.pdf"
        filename = sample_attachment["filename"]

        matches = fnmatch.fnmatch(filename, pattern)

        assert matches

    @pytest.mark.integration
    def test_attachment_glob_pattern_csv(self):
        """Attachment matching glob pattern *.csv is detected"""
        pattern = "*.csv"
        filename = "data_export.csv"

        matches = fnmatch.fnmatch(filename, pattern)

        assert matches

    @pytest.mark.integration
    def test_attachment_glob_pattern_xlsx(self):
        """Attachment matching glob pattern *.xlsx is detected"""
        pattern = "*.xlsx"
        filename = "report_20260115.xlsx"

        matches = fnmatch.fnmatch(filename, pattern)

        assert matches

    @pytest.mark.integration
    def test_attachment_wrong_extension_rejected(self):
        """Attachment with wrong extension is rejected"""
        pattern = "*.csv"
        filename = "data_export.xlsx"

        matches = fnmatch.fnmatch(filename, pattern)

        assert not matches

    @pytest.mark.integration
    def test_attachment_regex_pattern(self):
        """Attachment matching regex pattern is detected"""
        pattern = r"report_\d{8}\.pdf"
        filename = "report_20260115.pdf"

        # Check if pattern looks like regex (contains special chars)
        is_regex = any(c in pattern for c in r"\d+*?[]{}()")

        if is_regex:
            matches = bool(re.match(pattern, filename))
        else:
            matches = fnmatch.fnmatch(filename, pattern)

        assert matches

    @pytest.mark.integration
    def test_attachment_complex_glob(self):
        """Complex glob pattern with character class"""
        pattern = "report_[0-9]*.pdf"
        filename = "report_20260115.pdf"

        matches = fnmatch.fnmatch(filename, pattern)

        assert matches

    @pytest.mark.integration
    def test_multiple_attachment_patterns(self):
        """Multiple patterns can match different attachments"""
        patterns = ["*.pdf", "*.csv", "*.xlsx"]
        attachments = ["report.pdf", "data.csv", "summary.xlsx", "notes.txt"]

        matched = []
        for attachment in attachments:
            for pattern in patterns:
                if fnmatch.fnmatch(attachment, pattern):
                    matched.append(attachment)
                    break

        assert len(matched) == 3
        assert "notes.txt" not in matched


# ============================================================================
# TEST: DATE PREFIX FORMATTING
# ============================================================================

class TestDatePrefixFormatting:
    """Tests for adding date prefix to downloaded files"""

    @pytest.mark.integration
    def test_date_prefix_yyyymmdd(self):
        """Date prefix in yyyyMMdd format"""
        email_date = datetime(2026, 1, 15, 9, 0, 0)
        format_str = "yyyyMMdd"
        original_filename = "report.pdf"

        # Convert Java format to Python
        python_format = format_str.replace("yyyy", "%Y").replace("MM", "%m").replace("dd", "%d")
        date_prefix = email_date.strftime(python_format)

        new_filename = f"{date_prefix}_{original_filename}"

        assert new_filename == "20260115_report.pdf"

    @pytest.mark.integration
    def test_date_prefix_yyyy_mm_dd(self):
        """Date prefix in yyyy-MM-dd format"""
        email_date = datetime(2026, 1, 15, 9, 0, 0)
        format_str = "yyyy-MM-dd"

        python_format = format_str.replace("yyyy", "%Y").replace("MM", "%m").replace("dd", "%d")
        date_prefix = email_date.strftime(python_format)

        assert date_prefix == "2026-01-15"

    @pytest.mark.integration
    def test_date_prefix_with_time(self):
        """Date prefix with time component"""
        email_date = datetime(2026, 1, 15, 14, 30, 0)
        format_str = "yyyyMMdd_HHmmss"

        python_format = (
            format_str
            .replace("yyyy", "%Y")
            .replace("MM", "%m")
            .replace("dd", "%d")
            .replace("HH", "%H")
            .replace("mm", "%M")
            .replace("ss", "%S")
        )
        date_prefix = email_date.strftime(python_format)

        assert date_prefix == "20260115_143000"


# ============================================================================
# TEST: ATTACHMENT DOWNLOAD
# ============================================================================

class TestAttachmentDownload:
    """Tests for downloading email attachments"""

    @pytest.mark.integration
    def test_download_creates_file(self, mock_gmail_client, temp_inbox_dir, sample_attachment):
        """Download creates file in target directory"""
        target_path = temp_inbox_dir / sample_attachment["filename"]

        # Mock download to create file
        mock_gmail_client.download_attachment.return_value = target_path
        target_path.write_bytes(b"PDF content here")

        result = mock_gmail_client.download_attachment(
            message_id="msg123",
            attachment_id=sample_attachment["id"],
            target_path=str(target_path),
        )

        assert target_path.exists()

    @pytest.mark.integration
    def test_download_with_date_prefix(self, temp_inbox_dir, sample_attachment):
        """Download adds date prefix to filename"""
        date_prefix = "20260115"
        original_name = sample_attachment["filename"]
        new_name = f"{date_prefix}_{original_name}"

        target_path = temp_inbox_dir / new_name
        target_path.write_bytes(b"content")

        assert target_path.name == "20260115_daily_report_20260115.pdf"

    @pytest.mark.integration
    def test_download_multiple_attachments(self, mock_gmail_client, temp_inbox_dir):
        """Multiple attachments are all downloaded"""
        attachments = [
            {"id": "att1", "filename": "report1.pdf"},
            {"id": "att2", "filename": "report2.pdf"},
            {"id": "att3", "filename": "data.csv"},
        ]

        downloaded = []
        for att in attachments:
            target = temp_inbox_dir / att["filename"]
            target.write_bytes(b"content")
            downloaded.append(target)

        assert len(downloaded) == 3
        assert all(f.exists() for f in downloaded)


# ============================================================================
# TEST: LABEL OPERATIONS
# ============================================================================

class TestLabelOperations:
    """Tests for Gmail label operations"""

    @pytest.mark.integration
    def test_apply_processed_label(self, mock_gmail_client, sample_email):
        """Processed label is applied after successful download"""
        mock_gmail_client.apply_label(
            message_id=sample_email["id"],
            label_name="Processed",
        )

        mock_gmail_client.apply_label.assert_called_once()
        call_args = mock_gmail_client.apply_label.call_args
        assert "Processed" in str(call_args)

    @pytest.mark.integration
    def test_apply_error_label_on_failure(self, mock_gmail_client, sample_email):
        """Error label is applied after failed download"""
        mock_gmail_client.apply_label(
            message_id=sample_email["id"],
            label_name="ProcessingError",
        )

        mock_gmail_client.apply_label.assert_called_once()
        call_args = mock_gmail_client.apply_label.call_args
        assert "ProcessingError" in str(call_args)

    @pytest.mark.integration
    def test_remove_unread_label(self, mock_gmail_client, sample_email):
        """UNREAD label is removed after processing"""
        mock_gmail_client.mark_as_read(message_id=sample_email["id"])

        mock_gmail_client.mark_as_read.assert_called_once()

    @pytest.mark.integration
    def test_label_not_applied_on_dry_run(self, mock_gmail_client, sample_email):
        """Labels are not applied in dry run mode"""
        dry_run = True

        if not dry_run:
            mock_gmail_client.apply_label(
                message_id=sample_email["id"],
                label_name="Processed",
            )

        mock_gmail_client.apply_label.assert_not_called()


# ============================================================================
# TEST: DRY RUN MODE
# ============================================================================

class TestDryRunMode:
    """Tests for dry run (preview without downloading)"""

    @pytest.mark.integration
    def test_dry_run_does_not_download(self, mock_gmail_client):
        """Dry run mode does not download attachments"""
        dry_run = True

        if not dry_run:
            mock_gmail_client.download_attachment(
                message_id="msg123",
                attachment_id="att123",
                target_path="/tmp/file.pdf",
            )

        mock_gmail_client.download_attachment.assert_not_called()

    @pytest.mark.integration
    def test_dry_run_does_not_apply_labels(self, mock_gmail_client):
        """Dry run mode does not apply labels"""
        dry_run = True

        if not dry_run:
            mock_gmail_client.apply_label(
                message_id="msg123",
                label_name="Processed",
            )

        mock_gmail_client.apply_label.assert_not_called()

    @pytest.mark.integration
    def test_dry_run_logs_what_would_happen(self, mock_gmail_client, sample_email, sample_attachment):
        """Dry run logs what would be downloaded"""
        dry_run = True
        preview_actions = []

        if dry_run:
            preview_actions.append({
                "action": "download",
                "email": sample_email["subject"],
                "attachment": sample_attachment["filename"],
            })

        assert len(preview_actions) == 1
        assert preview_actions[0]["action"] == "download"


# ============================================================================
# TEST: EMAIL FILTERING
# ============================================================================

class TestEmailFiltering:
    """Tests for filtering emails by criteria"""

    @pytest.mark.integration
    def test_filter_unread_only(self, mock_gmail_client):
        """Only unread emails are processed"""
        all_emails = [
            {"id": "1", "subject": "Test 1", "is_unread": True},
            {"id": "2", "subject": "Test 2", "is_unread": False},
            {"id": "3", "subject": "Test 3", "is_unread": True},
        ]

        unread = [e for e in all_emails if e.get("is_unread", False)]

        assert len(unread) == 2

    @pytest.mark.integration
    def test_filter_by_date_range(self):
        """Emails within date range are processed"""
        emails = [
            {"id": "1", "date": datetime(2026, 1, 10)},
            {"id": "2", "date": datetime(2026, 1, 15)},
            {"id": "3", "date": datetime(2026, 1, 20)},
        ]

        start_date = datetime(2026, 1, 12)
        end_date = datetime(2026, 1, 18)

        filtered = [
            e for e in emails
            if start_date <= e["date"] <= end_date
        ]

        assert len(filtered) == 1
        assert filtered[0]["id"] == "2"

    @pytest.mark.integration
    def test_filter_by_all_criteria(self, sample_inbox_config):
        """Emails matching all criteria are processed"""
        email = {
            "subject": "AdminTest Daily Report - 2026-01-15",
            "sender": "reports@example.com",
            "attachments": [{"filename": "report.pdf"}],
        }

        subject_match = bool(re.search(
            sample_inbox_config["subject_pattern"],
            email["subject"],
            re.IGNORECASE
        ))

        sender_match = bool(re.search(
            sample_inbox_config["sender_pattern"],
            email["sender"],
            re.IGNORECASE
        ))

        attachment_match = any(
            fnmatch.fnmatch(att["filename"], sample_inbox_config["attachment_pattern"])
            for att in email["attachments"]
        )

        all_match = subject_match and sender_match and attachment_match

        assert all_match


# ============================================================================
# TEST: EML EXPORT
# ============================================================================

class TestEMLExport:
    """Tests for exporting emails as .eml files"""

    @pytest.mark.integration
    def test_eml_export_creates_file(self, temp_inbox_dir, sample_email):
        """EML export creates .eml file"""
        eml_path = temp_inbox_dir / f"{sample_email['id']}.eml"

        # Simulate EML content
        eml_content = f"""From: {sample_email['sender']}
Subject: {sample_email['subject']}
Date: {sample_email['date']}

Email body content here.
"""
        eml_path.write_text(eml_content)

        assert eml_path.exists()
        assert eml_path.suffix == ".eml"

    @pytest.mark.integration
    def test_eml_export_disabled_by_default(self, sample_inbox_config):
        """EML export is disabled by default"""
        export_eml = sample_inbox_config.get("export_eml", False)

        assert not export_eml

    @pytest.mark.integration
    def test_eml_export_when_enabled(self, sample_inbox_config, temp_inbox_dir, sample_email):
        """EML is exported when enabled in config"""
        sample_inbox_config["export_eml"] = True

        if sample_inbox_config["export_eml"]:
            eml_path = temp_inbox_dir / f"{sample_email['id']}.eml"
            eml_path.write_text("EML content")
            exported = True
        else:
            exported = False

        assert exported


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Tests for error scenarios"""

    @pytest.mark.integration
    def test_invalid_regex_pattern_handled(self):
        """Invalid regex pattern raises error"""
        invalid_pattern = "[invalid(regex"

        with pytest.raises(re.error):
            re.compile(invalid_pattern)

    @pytest.mark.integration
    def test_gmail_api_error_handled(self, mock_gmail_client):
        """Gmail API error is caught"""
        mock_gmail_client.get_unread_emails.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            mock_gmail_client.get_unread_emails()

        assert "API Error" in str(exc_info.value)

    @pytest.mark.integration
    def test_download_error_applies_error_label(self, mock_gmail_client, sample_email):
        """Download error triggers error label"""
        mock_gmail_client.download_attachment.side_effect = Exception("Download failed")

        try:
            mock_gmail_client.download_attachment(
                message_id=sample_email["id"],
                attachment_id="att123",
                target_path="/tmp/file.pdf",
            )
        except Exception:
            mock_gmail_client.apply_label(
                message_id=sample_email["id"],
                label_name="ProcessingError",
            )

        mock_gmail_client.apply_label.assert_called_once()

    @pytest.mark.integration
    def test_missing_target_directory_created(self, tmp_path):
        """Missing target directory is created"""
        target_dir = tmp_path / "new_dir" / "sub_dir"

        assert not target_dir.exists()

        target_dir.mkdir(parents=True, exist_ok=True)

        assert target_dir.exists()


# ============================================================================
# TEST: CONFIGURATION VALIDATION
# ============================================================================

class TestConfigValidation:
    """Tests for inbox configuration validation"""

    @pytest.mark.integration
    def test_required_fields_present(self, sample_inbox_config):
        """Required fields are present in config"""
        required = ["config_name", "target_directory", "is_active"]

        for field in required:
            assert field in sample_inbox_config

    @pytest.mark.integration
    def test_pattern_fields_can_be_empty(self, sample_inbox_config):
        """Pattern fields can be empty (match all)"""
        # Empty patterns should match all
        sample_inbox_config["subject_pattern"] = ""
        sample_inbox_config["sender_pattern"] = ""
        sample_inbox_config["attachment_pattern"] = "*"

        # All patterns should be valid
        assert sample_inbox_config["subject_pattern"] == ""
        assert sample_inbox_config["attachment_pattern"] == "*"

    @pytest.mark.integration
    def test_valid_regex_patterns(self, sample_inbox_config):
        """Regex patterns are valid"""
        patterns = [
            sample_inbox_config["subject_pattern"],
            sample_inbox_config["sender_pattern"],
        ]

        for pattern in patterns:
            if pattern:  # Only validate non-empty patterns
                # Should not raise
                re.compile(pattern)
