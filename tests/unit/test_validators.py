"""Unit tests for input validation functions

Tests all 8 validator functions from admin/components/validators.py with
various valid and invalid inputs, edge cases, and error conditions.
"""

import pytest
from admin.components.validators import (
    validate_directory_path,
    validate_file_pattern,
    validate_table_name,
    validate_date_format,
    validate_config_name,
    validate_positive_integer,
    validate_required,
    validate_max_length
)


# ============================================================================
# TEST validate_directory_path()
# ============================================================================

@pytest.mark.unit
class TestValidateDirectoryPath:
    """Tests for validate_directory_path function"""

    def test_valid_absolute_path(self):
        """Valid absolute path should pass"""
        is_valid, error = validate_directory_path('/app/data/source')
        assert is_valid is True
        assert error is None

    def test_valid_nested_path(self):
        """Valid nested absolute path should pass"""
        is_valid, error = validate_directory_path('/app/data/source/subfolder')
        assert is_valid is True
        assert error is None

    def test_invalid_missing_leading_slash(self):
        """Path without leading slash should fail"""
        is_valid, error = validate_directory_path('app/data/source')
        assert is_valid is False
        assert 'absolute' in error.lower()

    def test_invalid_trailing_slash(self):
        """Path with trailing slash should fail"""
        is_valid, error = validate_directory_path('/app/data/source/')
        assert is_valid is False
        assert 'end' in error.lower() or 'trailing' in error.lower()

    def test_invalid_characters(self):
        """Path with invalid characters should fail"""
        invalid_paths = [
            '/app/data/<test>',
            '/app/data/test>file',
            '/app/data/test|file',
            '/app/data/test?file',
            '/app/data/test*file'
        ]
        for path in invalid_paths:
            is_valid, error = validate_directory_path(path)
            assert is_valid is False
            assert 'invalid' in error.lower()

    def test_empty_string(self):
        """Empty path should fail"""
        is_valid, error = validate_directory_path('')
        assert is_valid is False
        assert 'required' in error.lower()

    def test_root_path(self):
        """Root path should pass"""
        is_valid, error = validate_directory_path('/app')
        assert is_valid is True
        assert error is None


# ============================================================================
# TEST validate_file_pattern()
# ============================================================================

@pytest.mark.unit
class TestValidateFilePattern:
    """Tests for validate_file_pattern function"""

    def test_valid_simple_pattern(self):
        """Simple regex pattern should pass"""
        is_valid, error = validate_file_pattern(r'.*\.csv')
        assert is_valid is True
        assert error is None

    def test_valid_complex_pattern(self):
        """Complex regex pattern should pass"""
        is_valid, error = validate_file_pattern(r'test_\d{8}_.*\.csv')
        assert is_valid is True
        assert error is None

    def test_valid_wildcard_pattern(self):
        """Wildcard pattern should pass"""
        is_valid, error = validate_file_pattern(r'file_.*\.(csv|txt)')
        assert is_valid is True
        assert error is None

    def test_invalid_regex(self):
        """Invalid regex should fail"""
        is_valid, error = validate_file_pattern('[unclosed')
        assert is_valid is False
        assert 'invalid' in error.lower() or 'regex' in error.lower()

    def test_invalid_regex_unclosed_group(self):
        """Unclosed group should fail"""
        is_valid, error = validate_file_pattern(r'test_(abc')
        assert is_valid is False
        assert 'invalid' in error.lower() or 'regex' in error.lower()

    def test_empty_string(self):
        """Empty pattern should fail"""
        is_valid, error = validate_file_pattern('')
        assert is_valid is False
        assert 'required' in error.lower()


# ============================================================================
# TEST validate_table_name()
# ============================================================================

@pytest.mark.unit
class TestValidateTableName:
    """Tests for validate_table_name function"""

    def test_valid_table_name(self):
        """Valid schema.table format should pass"""
        is_valid, error = validate_table_name('feeds.my_table')
        assert is_valid is True
        assert error is None

    def test_valid_with_numbers(self):
        """Table name with numbers should pass"""
        is_valid, error = validate_table_name('feeds.table_123')
        assert is_valid is True
        assert error is None

    def test_valid_with_underscores(self):
        """Table name with underscores should pass"""
        is_valid, error = validate_table_name('dba.t_import_config')
        assert is_valid is True
        assert error is None

    def test_invalid_missing_schema(self):
        """Table without schema should fail"""
        is_valid, error = validate_table_name('my_table')
        assert is_valid is False
        assert 'schema.table' in error.lower() or 'format' in error.lower()

    def test_invalid_too_many_parts(self):
        """Table with extra dots should fail"""
        is_valid, error = validate_table_name('feeds.table.extra')
        assert is_valid is False
        assert 'exactly one' in error.lower() or 'schema and one table' in error.lower()

    def test_invalid_schema_name_starts_with_number(self):
        """Schema starting with number should fail"""
        is_valid, error = validate_table_name('123feeds.table')
        assert is_valid is False
        assert 'invalid' in error.lower() or 'schema' in error.lower()

    def test_invalid_table_name_starts_with_number(self):
        """Table starting with number should fail"""
        is_valid, error = validate_table_name('feeds.123table')
        assert is_valid is False
        assert 'invalid' in error.lower() or 'table' in error.lower()

    def test_invalid_uppercase(self):
        """Uppercase names should fail"""
        is_valid, error = validate_table_name('Feeds.MyTable')
        assert is_valid is False
        assert 'invalid' in error.lower()

    def test_invalid_special_characters(self):
        """Special characters should fail"""
        is_valid, error = validate_table_name('feeds.my-table')
        assert is_valid is False
        assert 'invalid' in error.lower()

    def test_empty_string(self):
        """Empty table name should fail"""
        is_valid, error = validate_table_name('')
        assert is_valid is False
        assert 'required' in error.lower()


# ============================================================================
# TEST validate_date_format()
# ============================================================================

@pytest.mark.unit
class TestValidateDateFormat:
    """Tests for validate_date_format function"""

    def test_valid_common_format_yyyyMMddTHHmmss(self):
        """Common format yyyyMMddTHHmmss should pass"""
        is_valid, warning = validate_date_format('yyyyMMddTHHmmss')
        assert is_valid is True
        assert warning is None

    def test_valid_common_format_yyyy_MM_dd(self):
        """Common format yyyy-MM-dd should pass"""
        is_valid, warning = validate_date_format('yyyy-MM-dd')
        assert is_valid is True
        assert warning is None

    def test_valid_common_format_MM_dd_yyyy(self):
        """Common format MM/dd/yyyy should pass"""
        is_valid, warning = validate_date_format('MM/dd/yyyy')
        assert is_valid is True
        assert warning is None

    def test_valid_common_format_yyyyMMdd(self):
        """Common format yyyyMMdd should pass"""
        is_valid, warning = validate_date_format('yyyyMMdd')
        assert is_valid is True
        assert warning is None

    def test_uncommon_format_returns_warning(self):
        """Uncommon format should pass but return warning"""
        is_valid, warning = validate_date_format('custom_format')
        assert is_valid is True  # Still valid
        assert warning is not None
        assert 'uncommon' in warning.lower()

    def test_empty_string(self):
        """Empty format should fail"""
        is_valid, warning = validate_date_format('')
        assert is_valid is False
        assert 'required' in warning.lower()


# ============================================================================
# TEST validate_config_name()
# ============================================================================

@pytest.mark.unit
class TestValidateConfigName:
    """Tests for validate_config_name function"""

    def test_valid_simple_name(self):
        """Simple alphanumeric name should pass"""
        is_valid, error = validate_config_name('MyConfig')
        assert is_valid is True
        assert error is None

    def test_valid_with_underscores(self):
        """Name with underscores should pass"""
        is_valid, error = validate_config_name('My_Config_01')
        assert is_valid is True
        assert error is None

    def test_valid_with_hyphens(self):
        """Name with hyphens should pass"""
        is_valid, error = validate_config_name('My-Config-01')
        assert is_valid is True
        assert error is None

    def test_valid_mixed_characters(self):
        """Mixed valid characters should pass"""
        is_valid, error = validate_config_name('Config_Test-01')
        assert is_valid is True
        assert error is None

    def test_invalid_with_spaces(self):
        """Name with spaces should fail"""
        is_valid, error = validate_config_name('My Config')
        assert is_valid is False
        assert 'alphanumeric' in error.lower() or 'underscore' in error.lower() or 'hyphen' in error.lower()

    def test_invalid_with_special_characters(self):
        """Name with special characters should fail"""
        invalid_names = ['My@Config', 'My.Config', 'My$Config', 'My!Config']
        for name in invalid_names:
            is_valid, error = validate_config_name(name)
            assert is_valid is False
            assert 'alphanumeric' in error.lower() or 'underscore' in error.lower() or 'hyphen' in error.lower()

    def test_invalid_too_long(self):
        """Name longer than 100 characters should fail"""
        is_valid, error = validate_config_name('a' * 101)
        assert is_valid is False
        assert '100' in error

    def test_valid_exactly_100_chars(self):
        """Name exactly 100 characters should pass"""
        is_valid, error = validate_config_name('a' * 100)
        assert is_valid is True
        assert error is None

    def test_empty_string(self):
        """Empty name should fail"""
        is_valid, error = validate_config_name('')
        assert is_valid is False
        assert 'required' in error.lower()


# ============================================================================
# TEST validate_positive_integer()
# ============================================================================

@pytest.mark.unit
class TestValidatePositiveInteger:
    """Tests for validate_positive_integer function"""

    def test_valid_zero(self):
        """Zero should pass as positive integer"""
        is_valid, error = validate_positive_integer('0')
        assert is_valid is True
        assert error is None

    def test_valid_positive_number(self):
        """Positive number should pass"""
        is_valid, error = validate_positive_integer('42')
        assert is_valid is True
        assert error is None

    def test_valid_large_number(self):
        """Large positive number should pass"""
        is_valid, error = validate_positive_integer('999999')
        assert is_valid is True
        assert error is None

    def test_invalid_negative(self):
        """Negative number should fail"""
        is_valid, error = validate_positive_integer('-1')
        assert is_valid is False
        assert 'positive' in error.lower()

    def test_invalid_float(self):
        """Float should fail"""
        is_valid, error = validate_positive_integer('1.5')
        assert is_valid is False
        assert 'integer' in error.lower()

    def test_invalid_text(self):
        """Non-numeric text should fail"""
        is_valid, error = validate_positive_integer('abc')
        assert is_valid is False
        assert 'integer' in error.lower()

    def test_empty_string(self):
        """Empty string should fail"""
        is_valid, error = validate_positive_integer('')
        assert is_valid is False
        assert 'required' in error.lower()

    def test_custom_field_name(self):
        """Custom field name should appear in error"""
        is_valid, error = validate_positive_integer('abc', field_name='Position Index')
        assert is_valid is False
        assert 'Position Index' in error


# ============================================================================
# TEST validate_required()
# ============================================================================

@pytest.mark.unit
class TestValidateRequired:
    """Tests for validate_required function"""

    def test_valid_non_empty(self):
        """Non-empty value should pass"""
        is_valid, error = validate_required('test')
        assert is_valid is True
        assert error is None

    def test_invalid_empty_string(self):
        """Empty string should fail"""
        is_valid, error = validate_required('')
        assert is_valid is False
        assert 'required' in error.lower()

    def test_invalid_whitespace_only(self):
        """Whitespace-only string should fail"""
        is_valid, error = validate_required('   ')
        assert is_valid is False
        assert 'required' in error.lower()

    def test_invalid_none(self):
        """None value should fail"""
        is_valid, error = validate_required(None)
        assert is_valid is False
        assert 'required' in error.lower()

    def test_custom_field_name(self):
        """Custom field name should appear in error"""
        is_valid, error = validate_required('', field_name='Config Name')
        assert is_valid is False
        assert 'Config Name' in error


# ============================================================================
# TEST validate_max_length()
# ============================================================================

@pytest.mark.unit
class TestValidateMaxLength:
    """Tests for validate_max_length function"""

    def test_valid_within_limit(self):
        """Value within limit should pass"""
        is_valid, error = validate_max_length('test', 10)
        assert is_valid is True
        assert error is None

    def test_valid_exactly_at_limit(self):
        """Value exactly at limit should pass"""
        is_valid, error = validate_max_length('test', 4)
        assert is_valid is True
        assert error is None

    def test_invalid_exceeds_limit(self):
        """Value exceeding limit should fail"""
        is_valid, error = validate_max_length('test', 3)
        assert is_valid is False
        assert '3' in error
        assert 'characters' in error.lower()

    def test_valid_empty_string(self):
        """Empty string should pass (not enforced by this validator)"""
        is_valid, error = validate_max_length('', 10)
        assert is_valid is True
        assert error is None

    def test_valid_none(self):
        """None value should pass (not enforced by this validator)"""
        is_valid, error = validate_max_length(None, 10)
        assert is_valid is True
        assert error is None

    def test_custom_field_name(self):
        """Custom field name should appear in error"""
        is_valid, error = validate_max_length('toolong', 3, field_name='Description')
        assert is_valid is False
        assert 'Description' in error
