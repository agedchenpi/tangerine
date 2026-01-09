"""Tangerine Admin Interface Test Suite

This test suite provides comprehensive regression testing for the admin interface
service layer, including:

- Unit tests for validators, formatters, and utilities
- Integration tests for import configuration management
- Integration tests for monitoring services
- Integration tests for reference data management
- Database constraint and stored procedure tests

Usage:
    # Run all tests
    pytest tests/

    # Run by category
    pytest tests/unit/
    pytest tests/integration/

    # Run by marker
    pytest -m unit
    pytest -m integration
    pytest -m crud
    pytest -m validation

    # Run with coverage
    pytest tests/ --cov=admin/services --cov-report=html
"""
