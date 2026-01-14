"""Unit tests for pattern matching validation functions

Tests the pattern testing functions added in Phase 1:
- check_regex_match()
- check_glob_match()
- check_patterns_batch()

These functions are used for the "Test Patterns" tab in Inbox Configs.
"""

import pytest
from admin.components.validators import (
    check_regex_match,
    check_glob_match,
    check_patterns_batch
)


# ============================================================================
# TEST check_regex_match()
# ============================================================================

@pytest.mark.unit
class TestRegexMatch:
    """Tests for check_regex_match function"""

    def test_simple_match(self):
        """Simple pattern should match"""
        result = check_regex_match(r'.*Report.*', 'Daily Report Q1')
        assert result['is_valid'] is True
        assert result['matches'] is True
        assert result['match_text'] == 'Daily Report Q1'
        assert result['error'] is None

    def test_no_match(self):
        """Non-matching pattern should return matches=False"""
        result = check_regex_match(r'.*Invoice.*', 'Daily Report Q1')
        assert result['is_valid'] is True
        assert result['matches'] is False
        assert result['match_text'] is None

    def test_pattern_with_groups(self):
        """Pattern with capture groups should return groups"""
        result = check_regex_match(r'Report-(\d+)-(\w+)', 'Report-2026-Q1')
        assert result['is_valid'] is True
        assert result['matches'] is True
        assert result['groups'] == ['2026', 'Q1']

    def test_empty_groups(self):
        """Pattern without groups should return empty groups list"""
        result = check_regex_match(r'.*Report.*', 'Daily Report')
        assert result['groups'] == []

    def test_start_anchor(self):
        """Start anchor should work correctly"""
        result = check_regex_match(r'^Invoice', 'Invoice 2026')
        assert result['matches'] is True

        result = check_regex_match(r'^Invoice', 'Daily Invoice 2026')
        assert result['matches'] is False

    def test_end_anchor(self):
        """End anchor should work correctly"""
        result = check_regex_match(r'\.csv$', 'file.csv')
        assert result['matches'] is True

        result = check_regex_match(r'\.csv$', 'file.csv.txt')
        assert result['matches'] is False

    def test_digit_pattern(self):
        """Digit patterns should work"""
        result = check_regex_match(r'\d{4}-\d{2}-\d{2}', 'Date: 2026-01-15')
        assert result['matches'] is True
        assert result['match_text'] == '2026-01-15'

    def test_word_pattern(self):
        """Word patterns should work"""
        result = check_regex_match(r'\w+@\w+\.com', 'user@example.com')
        assert result['matches'] is True

    def test_invalid_regex(self):
        """Invalid regex should return error"""
        result = check_regex_match(r'[unclosed', 'test')
        assert result['is_valid'] is False
        assert result['matches'] is False
        assert result['error'] is not None
        assert 'invalid' in result['error'].lower() or 'regex' in result['error'].lower()

    def test_unclosed_group(self):
        """Unclosed group should return error"""
        result = check_regex_match(r'test_(abc', 'test_abc')
        assert result['is_valid'] is False
        assert result['error'] is not None

    def test_empty_pattern(self):
        """Empty pattern should return error"""
        result = check_regex_match('', 'test')
        assert result['error'] is not None
        assert 'empty' in result['error'].lower()

    def test_empty_input(self):
        """Empty input should be testable"""
        result = check_regex_match(r'.*', '')
        assert result['is_valid'] is True
        assert result['matches'] is True

    def test_special_characters_in_input(self):
        """Special characters in input should be handled"""
        result = check_regex_match(r'file\.\w+', 'file.csv')
        assert result['matches'] is True

    def test_case_sensitive(self):
        """Regex should be case sensitive by default"""
        result = check_regex_match(r'Report', 'REPORT')
        assert result['matches'] is False

        result = check_regex_match(r'Report', 'Report')
        assert result['matches'] is True

    def test_alternation(self):
        """Alternation patterns should work"""
        result = check_regex_match(r'(Invoice|Receipt)', 'Invoice 123')
        assert result['matches'] is True

        result = check_regex_match(r'(Invoice|Receipt)', 'Receipt 456')
        assert result['matches'] is True

        result = check_regex_match(r'(Invoice|Receipt)', 'Order 789')
        assert result['matches'] is False


# ============================================================================
# TEST check_glob_match()
# ============================================================================

@pytest.mark.unit
class TestGlobMatch:
    """Tests for check_glob_match function"""

    def test_star_pattern(self):
        """Star pattern should match any characters"""
        result = check_glob_match('*.csv', 'report.csv')
        assert result['is_valid'] is True
        assert result['matches'] is True

    def test_star_no_match(self):
        """Star pattern should not match wrong extension"""
        result = check_glob_match('*.csv', 'report.xlsx')
        assert result['matches'] is False

    def test_prefix_star_pattern(self):
        """Pattern with prefix and star should work"""
        result = check_glob_match('report_*.csv', 'report_2026.csv')
        assert result['matches'] is True

        result = check_glob_match('report_*.csv', 'data_2026.csv')
        assert result['matches'] is False

    def test_question_mark_pattern(self):
        """Question mark should match single character"""
        result = check_glob_match('file_?.txt', 'file_1.txt')
        assert result['matches'] is True

        result = check_glob_match('file_?.txt', 'file_12.txt')
        assert result['matches'] is False

    def test_character_class(self):
        """Character class patterns should work"""
        result = check_glob_match('file[0-9].txt', 'file5.txt')
        assert result['matches'] is True

        result = check_glob_match('file[0-9].txt', 'filea.txt')
        assert result['matches'] is False

    def test_multiple_extensions(self):
        """Pattern matching multiple extensions"""
        result = check_glob_match('*.csv', 'data.csv')
        assert result['matches'] is True

        result = check_glob_match('*.xlsx', 'data.xlsx')
        assert result['matches'] is True

    def test_complex_pattern(self):
        """Complex pattern with multiple wildcards"""
        result = check_glob_match('*_202[0-9]_*.csv', 'report_2026_q1.csv')
        assert result['matches'] is True

        result = check_glob_match('*_202[0-9]_*.csv', 'report_2019_q1.csv')
        assert result['matches'] is False

    def test_empty_pattern(self):
        """Empty pattern should return error"""
        result = check_glob_match('', 'test.csv')
        assert result['is_valid'] is False
        assert result['error'] is not None

    def test_exact_match(self):
        """Exact filename should match"""
        result = check_glob_match('specific_file.csv', 'specific_file.csv')
        assert result['matches'] is True

        result = check_glob_match('specific_file.csv', 'other_file.csv')
        assert result['matches'] is False

    def test_case_sensitive(self):
        """Glob should be case sensitive"""
        result = check_glob_match('*.CSV', 'file.csv')
        assert result['matches'] is False

        result = check_glob_match('*.csv', 'file.CSV')
        assert result['matches'] is False

    def test_hidden_files(self):
        """Hidden files (starting with .) should be matchable"""
        result = check_glob_match('.*', '.hidden')
        assert result['matches'] is True

        result = check_glob_match('*.csv', '.hidden.csv')
        assert result['matches'] is True


# ============================================================================
# TEST check_patterns_batch()
# ============================================================================

@pytest.mark.unit
class TestPatternsBatch:
    """Tests for check_patterns_batch function"""

    def test_regex_batch_multiple_matches(self):
        """Batch regex test with multiple inputs"""
        pattern = r'.*Report.*'
        inputs = ['Daily Report', 'Invoice 123', 'Weekly Report', 'Order 456']

        results = check_patterns_batch(pattern, inputs, pattern_type='regex')

        assert len(results) == 4
        assert results[0]['matches'] is True  # Daily Report
        assert results[1]['matches'] is False  # Invoice 123
        assert results[2]['matches'] is True  # Weekly Report
        assert results[3]['matches'] is False  # Order 456

    def test_regex_batch_includes_input(self):
        """Batch results should include original input"""
        pattern = r'test'
        inputs = ['test1', 'test2']

        results = check_patterns_batch(pattern, inputs, pattern_type='regex')

        assert results[0]['input'] == 'test1'
        assert results[1]['input'] == 'test2'

    def test_glob_batch_multiple_matches(self):
        """Batch glob test with multiple inputs"""
        pattern = '*.csv'
        inputs = ['file.csv', 'file.xlsx', 'report.csv', 'data.json']

        results = check_patterns_batch(pattern, inputs, pattern_type='glob')

        assert len(results) == 4
        assert results[0]['matches'] is True  # file.csv
        assert results[1]['matches'] is False  # file.xlsx
        assert results[2]['matches'] is True  # report.csv
        assert results[3]['matches'] is False  # data.json

    def test_batch_empty_inputs(self):
        """Empty inputs list should return empty results"""
        results = check_patterns_batch(r'.*', [], pattern_type='regex')
        assert results == []

    def test_batch_single_input(self):
        """Single input should work"""
        results = check_patterns_batch(r'test', ['testing'], pattern_type='regex')
        assert len(results) == 1
        assert results[0]['matches'] is True

    def test_batch_invalid_pattern(self):
        """Invalid pattern should propagate error to all results"""
        results = check_patterns_batch(r'[unclosed', ['test1', 'test2'], pattern_type='regex')

        assert len(results) == 2
        assert results[0]['is_valid'] is False
        assert results[1]['is_valid'] is False
        assert results[0]['error'] is not None

    def test_batch_default_pattern_type(self):
        """Default pattern type should be regex"""
        # Not specifying pattern_type should use regex
        results = check_patterns_batch(r'\d+', ['abc123', 'abc'])

        assert results[0]['matches'] is True  # Contains digits
        assert results[1]['matches'] is False  # No digits

    def test_batch_preserves_order(self):
        """Results should maintain input order"""
        inputs = ['first', 'second', 'third']
        results = check_patterns_batch(r'.*', inputs, pattern_type='regex')

        assert results[0]['input'] == 'first'
        assert results[1]['input'] == 'second'
        assert results[2]['input'] == 'third'

    def test_batch_with_capture_groups(self):
        """Batch regex should capture groups for each match"""
        pattern = r'Report-(\d+)'
        inputs = ['Report-123', 'Report-456', 'Invoice-789']

        results = check_patterns_batch(pattern, inputs, pattern_type='regex')

        assert results[0]['groups'] == ['123']
        assert results[1]['groups'] == ['456']
        assert results[2]['groups'] == []  # No match, no groups
