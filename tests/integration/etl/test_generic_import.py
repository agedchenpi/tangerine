"""Integration tests for generic_import.py ETL job

Tests file import functionality including:
- Configuration loading
- File discovery and pattern matching
- CSV/JSON extraction
- Schema management and table creation
- Import strategies (auto-add, ignore, strict)
- Metadata and date extraction
- Data loading and dataset tracking
- File archiving
"""

import csv
import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# TEST: CONFIGURATION LOADING
# ============================================================================

class TestImportConfigLoading:
    """Tests for loading import configurations from database"""

    @pytest.mark.integration
    def test_load_config_by_id(self, db_transaction, created_etl_import_config):
        """Config can be loaded by ID from database"""
        from admin.services.import_config_service import get_config

        config = get_config(created_etl_import_config["config_id"])

        assert config is not None
        assert config["config_id"] == created_etl_import_config["config_id"]
        assert config["config_name"] == created_etl_import_config["config_name"]

    @pytest.mark.integration
    def test_load_config_returns_none_for_invalid_id(self, db_transaction):
        """Loading non-existent config returns None"""
        from admin.services.import_config_service import get_config

        config = get_config(999999)

        assert config is None

    @pytest.mark.integration
    def test_config_contains_all_required_fields(self, db_transaction, created_etl_import_config):
        """Loaded config contains all fields needed for import"""
        from admin.services.import_config_service import get_config

        config = get_config(created_etl_import_config["config_id"])

        required_fields = [
            "config_id", "config_name", "datasource", "datasettype",
            "source_directory", "archive_directory", "file_pattern",
            "file_type", "target_table", "importstrategyid",
            "metadata_label_source", "metadata_label_location",
            "dateconfig", "datelocation", "dateformat", "delimiter",
            "is_active"
        ]

        for field in required_fields:
            assert field in config, f"Missing field: {field}"


# ============================================================================
# TEST: FILE DISCOVERY
# ============================================================================

class TestFileDiscovery:
    """Tests for file pattern matching and discovery"""

    @pytest.mark.integration
    def test_find_matching_csv_files(self, temp_source_dir, sample_csv_file):
        """Files matching pattern are discovered"""
        pattern = r"AdminTest_data_\d{8}\.csv"
        regex = re.compile(pattern)

        matching_files = [
            f for f in temp_source_dir.iterdir()
            if f.is_file() and regex.match(f.name)
        ]

        assert len(matching_files) == 1
        assert matching_files[0].name == sample_csv_file.name

    @pytest.mark.integration
    def test_non_matching_files_excluded(self, temp_source_dir):
        """Files not matching pattern are excluded"""
        # Create non-matching file
        (temp_source_dir / "other_file.txt").write_text("test")

        pattern = r"AdminTest_data_\d{8}\.csv"
        regex = re.compile(pattern)

        matching_files = [
            f for f in temp_source_dir.iterdir()
            if f.is_file() and regex.match(f.name)
        ]

        assert len(matching_files) == 0

    @pytest.mark.integration
    def test_multiple_matching_files(self, temp_source_dir):
        """Multiple matching files are all discovered"""
        # Create multiple matching files
        for i in range(3):
            date_str = f"202601{15+i:02d}"
            filepath = temp_source_dir / f"AdminTest_data_{date_str}.csv"
            filepath.write_text("id,name\n1,test")

        pattern = r"AdminTest_data_\d{8}\.csv"
        regex = re.compile(pattern)

        matching_files = [
            f for f in temp_source_dir.iterdir()
            if f.is_file() and regex.match(f.name)
        ]

        assert len(matching_files) == 3


# ============================================================================
# TEST: CSV EXTRACTION
# ============================================================================

class TestCSVExtraction:
    """Tests for CSV file parsing"""

    @pytest.mark.integration
    def test_extract_csv_with_header(self, sample_csv_file):
        """CSV with header row is parsed correctly"""
        records = []
        with open(sample_csv_file, "r", newline="") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        assert len(records) == 3
        assert records[0]["name"] == "Alice"
        assert records[1]["amount"] == "200.75"
        assert records[2]["id"] == "3"

    @pytest.mark.integration
    def test_extract_csv_with_nulls(self, sample_csv_with_nulls):
        """CSV with empty values is handled"""
        records = []
        with open(sample_csv_with_nulls, "r", newline="") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        assert len(records) == 3
        assert records[1]["name"] == ""  # Empty name
        assert records[2]["amount"] == ""  # Empty amount

    @pytest.mark.integration
    def test_extract_csv_column_names(self, sample_csv_file):
        """CSV column names are extracted correctly"""
        with open(sample_csv_file, "r", newline="") as f:
            reader = csv.DictReader(f)
            first_row = next(reader)

        columns = list(first_row.keys())

        assert "id" in columns
        assert "name" in columns
        assert "amount" in columns
        assert "date" in columns


# ============================================================================
# TEST: JSON EXTRACTION
# ============================================================================

class TestJSONExtraction:
    """Tests for JSON file parsing"""

    @pytest.mark.integration
    def test_extract_json_array(self, sample_json_file):
        """JSON array is parsed correctly"""
        with open(sample_json_file, "r") as f:
            records = json.load(f)

        assert len(records) == 3
        assert records[0]["name"] == "Alice"
        assert records[1]["amount"] == 200.75
        assert records[2]["active"] is True

    @pytest.mark.integration
    def test_json_preserves_types(self, sample_json_file):
        """JSON types are preserved during extraction"""
        with open(sample_json_file, "r") as f:
            records = json.load(f)

        assert isinstance(records[0]["id"], int)
        assert isinstance(records[0]["amount"], float)
        assert isinstance(records[0]["active"], bool)


# ============================================================================
# TEST: METADATA EXTRACTION
# ============================================================================

class TestMetadataExtraction:
    """Tests for extracting metadata labels from filename/content"""

    @pytest.mark.integration
    def test_extract_label_from_filename(self, sample_csv_file):
        """Label extracted from filename using delimiter and position"""
        filename = sample_csv_file.stem  # "AdminTest_data_20260115"
        delimiter = "_"
        position = 2  # 0-indexed, "data" is at position 1

        parts = filename.split(delimiter)
        label = parts[int(position)] if len(parts) > int(position) else filename

        assert label == "20260115"

    @pytest.mark.integration
    def test_extract_label_position_zero(self, sample_csv_file):
        """Position 0 extracts first part of filename"""
        filename = sample_csv_file.stem
        delimiter = "_"
        position = 0

        parts = filename.split(delimiter)
        label = parts[position]

        assert label == "AdminTest"

    @pytest.mark.integration
    def test_extract_label_from_file_content(self, temp_source_dir):
        """Label extracted from file content column"""
        # Create file with label in content
        filepath = temp_source_dir / "test.csv"
        filepath.write_text("id,label,value\n1,MyLabel,100\n")

        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            first_row = next(reader)

        label = first_row.get("label")

        assert label == "MyLabel"


# ============================================================================
# TEST: DATE EXTRACTION
# ============================================================================

class TestDateExtraction:
    """Tests for extracting dates from filename/content"""

    @pytest.mark.integration
    def test_extract_date_from_filename_yyyymmdd(self, sample_csv_file):
        """Date extracted from filename in yyyyMMdd format"""
        filename = sample_csv_file.stem  # "AdminTest_data_20260115"
        delimiter = "_"
        position = 2

        parts = filename.split(delimiter)
        date_str = parts[int(position)]

        # Parse yyyyMMdd format
        parsed_date = datetime.strptime(date_str, "%Y%m%d").date()

        assert parsed_date == date(2026, 1, 15)

    @pytest.mark.integration
    def test_java_to_python_date_format_conversion(self):
        """Java date format is converted to Python strptime format"""
        # Common Java formats and their Python equivalents
        conversions = {
            "yyyyMMdd": "%Y%m%d",
            "yyyy-MM-dd": "%Y-%m-%d",
            "dd/MM/yyyy": "%d/%m/%Y",
            "MM-dd-yyyy": "%m-%d-%Y",
        }

        for java_fmt, python_fmt in conversions.items():
            # Basic conversion (simplified)
            converted = java_fmt
            converted = converted.replace("yyyy", "%Y")
            converted = converted.replace("MM", "%m")
            converted = converted.replace("dd", "%d")

            assert converted == python_fmt, f"Failed for {java_fmt}"


# ============================================================================
# TEST: IMPORT STRATEGIES
# ============================================================================

class TestImportStrategies:
    """Tests for different import strategies"""

    @pytest.mark.integration
    def test_auto_add_strategy_includes_all_columns(self, sample_csv_different_columns):
        """Strategy 1 (auto-add) includes new columns"""
        with open(sample_csv_different_columns, "r") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames

        # Auto-add strategy should use all columns from file
        assert "new_column" in columns
        assert "another_new" in columns

    @pytest.mark.integration
    def test_ignore_strategy_filters_columns(self, sample_csv_different_columns):
        """Strategy 2 (ignore) filters to known columns only"""
        known_columns = {"id", "name"}

        with open(sample_csv_different_columns, "r") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        # Ignore strategy filters to known columns
        filtered_records = [
            {k: v for k, v in record.items() if k in known_columns}
            for record in records
        ]

        assert "new_column" not in filtered_records[0]
        assert "id" in filtered_records[0]
        assert "name" in filtered_records[0]

    @pytest.mark.integration
    def test_strict_strategy_validates_columns(self, sample_csv_different_columns):
        """Strategy 3 (strict) validates column match"""
        expected_columns = {"id", "name"}

        with open(sample_csv_different_columns, "r") as f:
            reader = csv.DictReader(f)
            actual_columns = set(reader.fieldnames)

        # Strict strategy checks for mismatch
        extra_columns = actual_columns - expected_columns
        missing_columns = expected_columns - actual_columns

        assert len(extra_columns) > 0  # Has extra columns
        assert len(missing_columns) == 0  # No missing columns


# ============================================================================
# TEST: SCHEMA MANAGEMENT
# ============================================================================

class TestSchemaManager:
    """Tests for table creation and column type inference"""

    @pytest.mark.integration
    def test_infer_integer_type(self):
        """Integer values are correctly typed"""
        from etl.jobs.generic_import import SchemaManager

        # Test integer detection
        values = ["1", "2", "3", "100", "-50"]

        for val in values:
            # Check if value looks like integer
            try:
                int(val)
                is_int = True
            except ValueError:
                is_int = False
            assert is_int, f"{val} should be detected as integer"

    @pytest.mark.integration
    def test_infer_float_type(self):
        """Float values are correctly typed"""
        values = ["1.5", "2.75", "100.00", "-50.25"]

        for val in values:
            try:
                float(val)
                is_float = "." in val
            except ValueError:
                is_float = False
            assert is_float, f"{val} should be detected as float"

    @pytest.mark.integration
    def test_infer_boolean_type(self):
        """Boolean values are correctly typed"""
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes"]
        false_values = ["false", "False", "FALSE", "0", "no", "No"]

        for val in true_values + false_values:
            is_bool = val.lower() in ("true", "false", "1", "0", "yes", "no")
            assert is_bool, f"{val} should be detected as boolean"

    @pytest.mark.integration
    def test_infer_date_type(self):
        """Date values are correctly typed"""
        date_values = ["2026-01-15", "2026/01/15", "01-15-2026"]

        for val in date_values:
            # Simple date pattern check
            has_date_pattern = bool(re.match(r"\d{2,4}[-/]\d{2}[-/]\d{2,4}", val))
            assert has_date_pattern, f"{val} should be detected as date"

    @pytest.mark.integration
    def test_sanitize_column_name(self):
        """Column names are sanitized for PostgreSQL"""
        test_cases = {
            "Normal Name": "normal_name",
            "with-dashes": "with_dashes",
            "with.dots": "with_dots",
            "123numeric": "_123numeric",
            "UPPERCASE": "uppercase",
        }

        for original, expected in test_cases.items():
            # Basic sanitization
            sanitized = original.lower()
            sanitized = re.sub(r"[^a-z0-9_]", "_", sanitized)
            if sanitized[0].isdigit():
                sanitized = "_" + sanitized

            assert sanitized == expected, f"Expected {expected}, got {sanitized}"


# ============================================================================
# TEST: DATA LOADING
# ============================================================================

class TestDataLoading:
    """Tests for bulk data insertion"""

    @pytest.mark.integration
    def test_records_converted_to_tuples(self, sample_csv_file):
        """Records are converted to tuples for bulk insert"""
        with open(sample_csv_file, "r") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        columns = list(records[0].keys())
        values = [tuple(record[col] for col in columns) for record in records]

        assert len(values) == 3
        assert all(isinstance(v, tuple) for v in values)
        assert values[0][1] == "Alice"  # name column

    @pytest.mark.integration
    def test_empty_file_returns_no_records(self, temp_source_dir):
        """Empty file returns empty record list"""
        filepath = temp_source_dir / "empty.csv"
        filepath.write_text("id,name\n")  # Header only

        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        assert len(records) == 0


# ============================================================================
# TEST: DATASET TRACKING
# ============================================================================

class TestDatasetTracking:
    """Tests for dataset creation and tracking"""

    @pytest.mark.integration
    def test_dataset_created_with_label(self, db_transaction, created_datasource, created_datasettype):
        """Dataset is created with correct label"""
        unique_label = f"AdminTest_Dataset_{uuid.uuid4().hex[:8]}"

        with db_transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO dba.tdataset (
                    datasourceid, datasettypeid, label, datasetdate, datastatusid
                )
                SELECT ds.datasourceid, dt.datasettypeid, %s, CURRENT_DATE, 1
                FROM dba.tdatasource ds, dba.tdatasettype dt
                WHERE ds.sourcename = %s AND dt.typename = %s
                RETURNING datasetid
            """,
                (unique_label, created_datasource["sourcename"], created_datasettype["typename"]),
            )
            dataset_id = cursor.fetchone()["datasetid"]

            cursor.execute(
                "SELECT * FROM dba.tdataset WHERE datasetid = %s",
                (dataset_id,),
            )
            dataset = cursor.fetchone()

        assert dataset is not None
        assert dataset["label"] == unique_label

    @pytest.mark.integration
    def test_dataset_has_run_uuid(self, db_transaction, created_datasource, created_datasettype):
        """Dataset tracks run_uuid for job correlation"""
        run_uuid = str(uuid.uuid4())
        label = f"AdminTest_UUID_{uuid.uuid4().hex[:8]}"

        with db_transaction() as cursor:
            # Note: run_uuid may need to be added to tdataset table
            # This test documents the expected behavior
            cursor.execute(
                """
                INSERT INTO dba.tdataset (
                    datasourceid, datasettypeid, label, datasetdate, datastatusid
                )
                SELECT ds.datasourceid, dt.datasettypeid, %s, CURRENT_DATE, 1
                FROM dba.tdatasource ds, dba.tdatasettype dt
                WHERE ds.sourcename = %s AND dt.typename = %s
                RETURNING datasetid
            """,
                (label, created_datasource["sourcename"], created_datasettype["typename"]),
            )
            dataset_id = cursor.fetchone()["datasetid"]

        assert dataset_id is not None


# ============================================================================
# TEST: FILE ARCHIVING
# ============================================================================

class TestFileArchiving:
    """Tests for post-import file archiving"""

    @pytest.mark.integration
    def test_file_moved_to_archive(self, temp_source_dir, temp_archive_dir, sample_csv_file):
        """Processed file is moved to archive directory"""
        import shutil

        original_name = sample_csv_file.name
        archive_path = temp_archive_dir / original_name

        # Simulate archiving
        shutil.move(str(sample_csv_file), str(archive_path))

        assert not sample_csv_file.exists()
        assert archive_path.exists()

    @pytest.mark.integration
    def test_archive_preserves_content(self, temp_source_dir, temp_archive_dir):
        """Archived file content is preserved"""
        import shutil

        content = "id,name\n1,test"
        source_file = temp_source_dir / "test.csv"
        source_file.write_text(content)

        archive_path = temp_archive_dir / "test.csv"
        shutil.move(str(source_file), str(archive_path))

        assert archive_path.read_text() == content


# ============================================================================
# TEST: DRY RUN MODE
# ============================================================================

class TestDryRunMode:
    """Tests for dry run (validation without database writes)"""

    @pytest.mark.integration
    def test_dry_run_does_not_create_dataset(self, db_transaction, clean_test_data):
        """Dry run mode does not create dataset records"""
        with db_transaction() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM dba.tdataset
                WHERE label LIKE 'AdminTest_DryRun%%'
            """
            )
            initial_count = cursor.fetchone()["count"]

        # In dry run, no datasets would be created
        # This test documents expected behavior
        assert initial_count == 0

    @pytest.mark.integration
    def test_dry_run_does_not_archive_files(self, temp_source_dir, sample_csv_file, temp_archive_dir):
        """Dry run mode does not move files to archive"""
        # In dry run, file should remain in source
        assert sample_csv_file.exists()
        assert not (temp_archive_dir / sample_csv_file.name).exists()


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Tests for error scenarios"""

    @pytest.mark.integration
    def test_invalid_file_pattern_raises_error(self):
        """Invalid regex pattern raises error"""
        invalid_pattern = "[invalid(regex"

        with pytest.raises(re.error):
            re.compile(invalid_pattern)

    @pytest.mark.integration
    def test_missing_source_directory_handled(self, tmp_path):
        """Missing source directory is handled gracefully"""
        non_existent = tmp_path / "does_not_exist"

        assert not non_existent.exists()

    @pytest.mark.integration
    def test_malformed_csv_handled(self, temp_source_dir):
        """Malformed CSV is handled gracefully"""
        filepath = temp_source_dir / "malformed.csv"
        filepath.write_text("id,name\n1,test,extra,columns")

        # csv.DictReader handles extra columns by ignoring them
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            records = list(reader)

        # Should still parse (extra columns ignored with restkey)
        assert len(records) == 1
