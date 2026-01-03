# Regression Test Data Files

This directory contains test data files for the Tangerine ETL regression test suite.

## Directory Structure

```
regression/
├── csv/      - CSV test files (6 tests)
├── xls/      - XLS test files (3 tests)
├── xlsx/     - XLSX test files (3 tests)
├── json/     - JSON test files (3 tests)
├── xml/      - XML test files (2 tests)
└── archive/  - Archived files after processing (not committed)
```

## Test Files Overview

### CSV Tests (6)
1. `Strategy1_Products_20260101T120000.csv` - Tests Strategy 1 (auto-add columns), 5 records
2. `Strategy2_Products_20260101T130000.csv` - Tests Strategy 2 (ignore extra columns), 3 records
3. `Strategy3_Orders_20260101T140000.csv` - Tests Strategy 3 (strict validation), 4 records
4. `MetadataFilename_20260101T150000.csv` - Tests metadata extraction from filename, 2 records
5. `EmptyFile_20260101T160000.csv` - Tests empty file handling, 0 records
6. `MalformedData_20260101T170000.csv` - Tests malformed data handling, 2 records

### XLS Tests (3)
1. `Strategy1_Inventory_20260101T110000.xls` - Tests XLS with Strategy 1, 7 records
2. `MetadataContent_20260101T120000.xls` - Tests metadata from file content, 4 records
3. `MultipleSheets_20260101T130000.xls` - Tests multi-sheet XLS files, 3 records

### XLSX Tests (3)
1. `Strategy2_Sales_20260101T140000.xlsx` - Tests XLSX with Strategy 2, 10 records
2. `DateContent_20260101T150000.xlsx` - Tests date extraction from content, 5 records
3. `LargeFile_20260101T160000.xlsx` - Tests large file performance, 1000 records

### JSON Tests (3)
1. `ArrayFormat_20260104T120000.json` - Tests JSON array format
2. `ObjectFormat_20260104T130000.json` - Tests JSON object format
3. `NestedObjects_20260104T140000.json` - Tests nested JSON objects

### XML Tests (2)
1. `StructuredXML_20260105T120000.xml` - Tests structured XML parsing
2. `BlobXML_20260105T130000.xml` - Tests XML blob storage

## Regenerating Test Files

Test files can be regenerated at any time using:

```bash
docker compose exec tangerine python etl/regression/generate_test_files.py
```

This will recreate all CSV, XLS, and XLSX files. JSON and XML files are pre-created and stored in the repository.

## Running Regression Tests

```bash
# Run all tests
docker compose exec tangerine python etl/regression/run_regression_tests.py --verbose

# Run specific category
docker compose exec tangerine python etl/regression/run_regression_tests.py --category csv
```

## Test Configurations

All test configurations are defined in:
- `schema/dba/data/regression_test_configs.sql`

Test results are stored in:
- `dba.tregressiontest` - Individual test results
- `dba.vregressiontest_summary` - Aggregated test summary

## Notes

- The `archive/` directory is created during test execution and contains processed files
- Archive directory should NOT be committed to the repository
- All test files use deterministic timestamps for reproducibility
- File naming convention: `{Description}_{Timestamp}.{ext}` where timestamp is `yyyyMMddTHHmmss`
