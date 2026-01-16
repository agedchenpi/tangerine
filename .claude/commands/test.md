---
name: test
description: Run pytest with filters for unit, integration, or specific tests
---

# Test Command

Run the Tangerine test suite with optional filters.

## Usage

Parse the arguments to determine which tests to run:

| Argument | Action |
|----------|--------|
| (none) | Run all tests |
| `unit` | Run unit tests only (fast, no database) |
| `integration` | Run integration tests (requires database) |
| `services` | Run service integration tests |
| `{filename}` | Run specific test file |

## Commands

### All Tests
```bash
docker compose exec tangerine pytest tests/ -v
```

### Unit Tests Only (Fast)
```bash
docker compose exec tangerine pytest tests/unit/ -v -m unit
```

### Integration Tests (Requires DB)
```bash
docker compose exec tangerine pytest tests/integration/ -v -m integration
```

### Service Tests
```bash
docker compose exec tangerine pytest tests/integration/services/ -v
```

### Specific Test File
```bash
docker compose exec tangerine pytest tests/{path_to_file} -v
```

### With Coverage Report
```bash
docker compose exec tangerine pytest tests/ --cov=admin --cov-report=term-missing
```

## Examples

- `/test` → Run all 310+ tests
- `/test unit` → Run ~99 unit tests (no DB, fast)
- `/test integration` → Run ~212 integration tests
- `/test services` → Run service layer tests
- `/test validators` → Run tests/unit/test_validators.py

## Notes

- Unit tests have no external dependencies and run quickly
- Integration tests require the database container to be running
- The `AdminTest_` prefix is used for all test data
- Tests use transaction-based isolation with auto-rollback
