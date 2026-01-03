# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tangerine is an AI-integrated ETL pipeline built with Vertical Slice Architecture (VSA). The project uses PostgreSQL for data storage, Python for ETL logic, and Docker for containerization. Development happens on Windows with deployment to Ubuntu 24.04 LTS server via SSH.

## Environment Setup

The project requires a `.env` file with the following variables (never commit this file):
```
POSTGRES_DB=tangerine_db
POSTGRES_USER=tangerine_admin
POSTGRES_PASSWORD=your_secure_password
ETL_USER_PASSWORD=your_etl_password
ADMIN_PASSWORD=your_admin_password
DB_URL=postgresql://tangerine_admin:your_secure_password@db:5432/tangerine_db
```

## Common Commands

### Local Development (Windows)
```bash
# Build and start services
docker compose up --build

# Run in detached mode
docker compose up -d

# Stop and remove volumes (resets database)
docker compose down --volumes

# View logs
docker compose logs -f tangerine
```

### Orchestration Script
```bash
# Run full pipeline (builds, starts, runs ETL, stops)
./run_all.sh
```

### Testing Database Connection
```bash
# Execute db_utils.py to test connection
docker compose exec tangerine python common/db_utils.py
```

### Running Python Scripts in Container
```bash
# General pattern for running scripts
docker compose exec tangerine python <path/to/script.py>
```

### Running Generic Import
```bash
# Run import using config_id from dba.timportconfig
docker compose exec tangerine python etl/jobs/generic_import.py --config-id <id>

# Dry run (no database writes)
docker compose exec tangerine python etl/jobs/generic_import.py --config-id <id> --dry-run

# With specific date
docker compose exec tangerine python etl/jobs/generic_import.py --config-id <id> --date 2026-01-15
```

### Running Regression Tests
```bash
# Run all regression tests
docker compose exec tangerine python etl/regression/run_regression_tests.py

# Run with verbose output
docker compose exec tangerine python etl/regression/run_regression_tests.py --verbose

# Run specific category
docker compose exec tangerine python etl/regression/run_regression_tests.py --category csv

# Generate test data files
docker compose exec tangerine python etl/regression/generate_test_files.py
```

## Data Flow: Docker to Database

Here's the complete workflow from Docker Compose startup to data persisted in the database:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE PHASE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  $ docker compose up --build                                                │
│                                                                              │
│  ┌──────────────────────────────────┐    ┌──────────────────────────────┐   │
│  │  db (PostgreSQL 18)              │    │  tangerine (Python 3.11)     │   │
│  │  ├─ Starts PostgreSQL            │    │  ├─ Builds Docker image      │   │
│  │  ├─ Mounts schema/ directory     │    │  ├─ Mounts .data/etl → /app  │   │
│  │  └─ Prepares for init scripts    │    │  └─ Ready for commands       │   │
│  └──────────────────────────────────┘    └──────────────────────────────┘   │
│                           ↓                                                  │
│              Volume Mount: ./.data/etl ↔ /app/data                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATABASE INITIALIZATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL executes /docker-entrypoint-initdb.d/init.sh                    │
│                                                                              │
│  1. Creates users: etl_user, admin                                          │
│  2. Creates group roles: app_rw, app_ro                                     │
│  3. Creates dba schema                                                      │
│     ├─ dba.tdataset (tracks dataset loads)                                  │
│     ├─ dba.tdatasettype (reference)                                        │
│     ├─ dba.tdatasource (reference)                                         │
│     ├─ dba.timportstrategy (import strategies 1, 2, 3)                     │
│     └─ dba.timportconfig (import configurations)                           │
│  4. Creates feeds schema                                                    │
│     └─ feeds.* (target tables for raw data)                                │
│  5. Creates procedures for configuration management                         │
│  6. Creates logging & audit tables                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│               IMPORT CONFIGURATION SETUP (User Action)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Step 1: Create Target Table (Local)                                        │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │ CREATE TABLE feeds.my_import (                                │         │
│  │     my_importid SERIAL PRIMARY KEY,                           │         │
│  │     datasetid INT REFERENCES dba.tdataset,                    │         │
│  │     -- business columns                                       │         │
│  │     created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP          │         │
│  │ );                                                             │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
│  Step 2: Place Data Files (Local Machine)                                   │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │ ./.data/etl/source/                                            │         │
│  │   ├─ 20260105T150000_VolumeTest.csv ←─────┐                   │         │
│  │   ├─ data_file_*.xlsx                      │ (volume synced)   │         │
│  │   └─ another_import.json                   │ → /app/data/      │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
│  Step 3: Create Import Configuration                                        │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │ CALL dba.pimportconfigi(                                       │         │
│  │     'MyImportConfig',                                          │         │
│  │     'MyDataSource',                                            │         │
│  │     'MyDataType',                                              │         │
│  │     '/app/data/source',       ← mounted path                  │         │
│  │     '/app/data/archive',      ← mounted path                  │         │
│  │     '.*MyPattern\\.csv',      ← file pattern                  │         │
│  │     'CSV',                                                     │         │
│  │     'filename',               ← metadata source               │         │
│  │     'Label1',                 ← metadata value                │         │
│  │     'filename',               ← date source                   │         │
│  │     '0',                      ← position in filename           │         │
│  │     'yyyyMMddTHHmmss',        ← date format                   │         │
│  │     '_',                      ← filename delimiter            │         │
│  │     'feeds.my_import',        ← target table                  │         │
│  │     1,                        ← strategy ID                   │         │
│  │     TRUE                                                       │         │
│  │ );                                                             │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                            ↓ (inserts config_id)                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│              IMPORT JOB EXECUTION (Triggered by User)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  $ docker compose exec tangerine python etl/jobs/generic_import.py \        │
│      --config-id 1                                                          │
│                                                                              │
│                        ↓↓↓ INSIDE CONTAINER ↓↓↓                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ PHASE 1: SETUP                                              │            │
│  ├─────────────────────────────────────────────────────────────┤            │
│  │ ✓ Fetch config_id from dba.timportconfig                   │            │
│  │ ✓ Validate config exists                                   │            │
│  │ ✓ Load import strategy from dba.timportstrategy            │            │
│  │ ✓ Create dataset record in dba.tdataset                    │            │
│  │ Result: run_uuid, dataset_id                               │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                           ↓                                                  │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ PHASE 2: EXTRACT                                            │            │
│  ├─────────────────────────────────────────────────────────────┤            │
│  │ ✓ Scan /app/data/source/ for matching files               │            │
│  │ ✓ For each file:                                           │            │
│  │   ├─ CSV: Read with csv.DictReader                        │            │
│  │   ├─ XLS/XLSX: Parse with openpyxl/xlrd                   │            │
│  │   ├─ JSON: Load as dict or array                          │            │
│  │   └─ XML: Parse as blob or structure                      │            │
│  │ ✓ Extract metadata_label (from filename/content/static)   │            │
│  │ ✓ Extract date (using dateformat parser)                  │            │
│  │ Result: raw_records list with source file info            │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                           ↓                                                  │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ PHASE 3: TRANSFORM                                          │            │
│  ├─────────────────────────────────────────────────────────────┤            │
│  │ ✓ Normalize column names (lowercase, spaces→underscores)   │            │
│  │ ✓ Add audit fields (created_date, created_by=etl_user)     │            │
│  │ ✓ Apply import strategy:                                   │            │
│  │   ├─ Strategy 1: Identify new columns, exclude metadata   │            │
│  │   ├─ Strategy 2: Filter to existing columns only          │            │
│  │   └─ Strategy 3: Validate all columns exist or FAIL        │            │
│  │ ✓ For JSON/XML: wrap in {raw_data: blob}                  │            │
│  │ Result: transformed_records list ready for load           │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                           ↓                                                  │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ PHASE 4: LOAD                                               │            │
│  ├─────────────────────────────────────────────────────────────┤            │
│  │ ✓ Check target table exists in feeds schema                │            │
│  │ ✓ Based on import strategy:                                │            │
│  │   ├─ Strategy 1: ALTER TABLE ADD COLUMN (new ones)        │            │
│  │   ├─ Strategy 2: Pass through to loader as-is             │            │
│  │   └─ Strategy 3: Already validated all columns exist       │            │
│  │ ✓ Filter out metadata columns before insert                │            │
│  │ ✓ Bulk insert via PostgresLoader (includes dataset_id FK)  │            │
│  │ ✓ Update dba.tdataset status to 'Active'                  │            │
│  │ Result: records inserted, dataset_id FK links created     │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                           ↓                                                  │
│  ┌─────────────────────────────────────────────────────────────┐            │
│  │ PHASE 5: CLEANUP                                            │            │
│  ├─────────────────────────────────────────────────────────────┤            │
│  │ ✓ Archive processed files:                                 │            │
│  │   /app/data/source/* → /app/data/archive/*                │            │
│  │ ✓ Update timportconfig last_modified_at timestamp          │            │
│  │ ✓ Log all metrics (files, records, run_uuid)              │            │
│  │ Result: files accessible at ./.data/etl/archive/ (local)   │            │
│  └─────────────────────────────────────────────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA AT REST                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PostgreSQL Database (tangerine_db)                                         │
│  ├─ dba.tdataset                                                            │
│  │  └─ [dataset_id=9, status='Active', created_at=..., ...]               │
│  │                                                                          │
│  ├─ dba.tlogentry                                                           │
│  │  └─ [run_uuid='55e5ff8c...', job_name='GenericImportJob', ...]         │
│  │                                                                          │
│  └─ feeds.my_import                                                        │
│     ├─ [my_importid=1, datasetid=9, product='Laptop', price=999.99, ...]  │
│     ├─ [my_importid=2, datasetid=9, product='Mouse', price=19.99, ...]    │
│     └─ [my_importid=3, datasetid=9, product='Keyboard', price=79.99, ...] │
│                                                                              │
│  Local File System (Archived)                                              │
│  └─ ./.data/etl/archive/                                                   │
│     ├─ 20260105T150000_VolumeTest.csv ✓ synced via volume                  │
│     └─ (timestamp preserved, bidirectional sync maintained)                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Architecture

### Vertical Slice Architecture
The project uses VSA to organize features as self-contained slices. Future AI agent features will live in `features/` directory (e.g., `features/agent1/main.py`).

### Database Schema Organization
PostgreSQL schemas are organized by domain:
- **dba schema**: ETL pipeline maintenance, logging, and dataset metadata
- **feeds schema**: Raw data feeds storage

### Database Initialization Flow
Database initialization happens via `schema/init.sh` which runs on container startup through Docker's entrypoint mechanism:

1. Creates users: `etl_user` (login) and `admin` (superuser)
2. Creates group roles: `app_rw` (read-write) and `app_ro` (read-only)
3. Executes SQL files in strict order from `schema/dba/` and `schema/feeds/`
4. Grants permissions based on roles

### SQL File Organization
All SQL files under `schema/` follow this structure:
- **schema.sql**: Creates the schema and grants permissions
- **tables/**: Table definitions with foreign keys and constraints
- **views/**: View definitions
- **functions/**: PL/pgSQL functions
- **procedures/**: Stored procedures
- **triggers/**: Trigger definitions
- **indexes/**: Index definitions
- **sequences/**: Sequence definitions
- **materialized_views/**: Materialized view definitions
- **types/**: Custom type definitions
- **extensions/**: PostgreSQL extension enablement
- **data/**: Initial data inserts and population scripts

Each SQL file uses `DO $$ ... END $$` blocks with `IF NOT EXISTS` checks to ensure idempotent execution.

### Key Database Tables (dba schema)
- **tdataset**: Tracks metadata for dataset loads with effective dating (efffromdate/effthrudate) and isactive flag
- **tdatasettype**: Reference table for dataset types
- **tdatasource**: Reference table for data sources
- **tdatastatus**: Reference table for dataset statuses
- **tlogentry**: ETL process logging with run_uuid for tracking individual runs
- **tcalendardays**: Calendar dimension with business day tracking
- **tholidays**: Holiday definitions
- **tddllogs**: DDL change tracking via event triggers
- **timportstrategy**: Reference table for import strategies (how to handle column mismatches)
- **timportconfig**: Configuration table for generic file imports (CSV, XLS, XLSX, JSON, XML)

### Import Configuration Tables

#### timportstrategy
Defines how to handle column mismatches during imports:
| ID | Strategy | Behavior |
|----|----------|----------|
| 1 | Import and create new columns if needed | ALTER TABLE to add new columns from source file |
| 2 | Import only (ignores new columns) | Silently ignores columns not in target table |
| 3 | Import or fail if columns missing | Raises error if source has columns not in target table |

#### timportconfig
Configuration-driven import settings:
- `config_id`: Primary key used to run imports
- `config_name`: Unique descriptive name
- `datasource`/`datasettype`: Must exist in tdatasource/tdatasettype
- `source_directory`/`archive_directory`: Absolute paths for file processing
- `file_pattern`: Regex pattern to match files (e.g., `.*\.csv`)
- `file_type`: CSV, XLS, XLSX, JSON, or XML
- `metadata_label_source`: Extract label from `filename`, `file_content`, or `static`
- `dateconfig`/`datelocation`/`dateformat`: Date extraction configuration
- `delimiter`: Delimiter for parsing filenames (e.g., `_`)
- `target_table`: Target table in `schema.table` format
- `importstrategyid`: FK to timportstrategy

#### Stored Procedures
- `dba.pimportconfigi`: Insert new import configuration
- `dba.pimportconfigu`: Update existing configuration (partial updates supported)

### Feeds Schema Table Conventions
Tables in the `feeds` schema for raw data storage must follow these conventions:
- **Primary key**: Named `{tablename}id` (e.g., `dynamic_importid` for table `dynamic_import`)
- **Second column**: `datasetid` as FK to `dba.tdataset(datasetid)`
- **Remaining columns**: Business data columns
- **Audit columns** (optional): `created_date`, `created_by`, `modified_date`, `modified_by`

Example:
```sql
CREATE TABLE feeds.my_import (
    my_importid SERIAL PRIMARY KEY,
    datasetid INT REFERENCES dba.tdataset(datasetid),
    -- business columns here
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50)
);
```

### Database Permissions Model
- **admin**: Full superuser access to all schemas
- **app_rw**: Usage and create rights on schemas, insert/update/select on tables
- **app_ro**: Read-only access
- **etl_user**: Assigned to app_rw group for ETL operations
- **PUBLIC**: Granted select on all dba schema tables for visibility

### Python Utilities
- **common/db_utils.py**: Database connection helper using psycopg2 and environment variables
  - `connect_db(db_url)`: Returns psycopg2 connection object or None on error
  - Reads `DB_URL` from environment when run as main script

### Generic Import System
- **etl/jobs/generic_import.py**: Configuration-driven file import job
  - Reads import settings from `dba.timportconfig`
  - Supports CSV, XLS, XLSX, JSON, XML file formats
  - Implements all 3 import strategies for column handling
  - Extracts metadata/dates from filename, file content, or static values
  - Archives files after successful processing
  - Integrates with ETL framework (BaseETLJob, dataset tracking, logging)

## Adding New Features

### Adding SQL Objects
1. Create SQL file in appropriate `schema/<schema_name>/<type>/` directory
2. Use idempotent `DO $$ IF NOT EXISTS ... END $$` pattern
3. Add execution line to `schema/init.sh` in the correct order (dependencies first)
4. Include appropriate `GRANT` statements for role-based access
5. Rebuild containers to apply changes: `docker compose down --volumes && docker compose up --build`

### Adding AI Agent Slices
1. Create feature directory: `features/<agent_name>/`
2. Add Python script with AI logic: `features/<agent_name>/main.py`
3. Update `Dockerfile` to install required dependencies (e.g., `RUN pip install --no-cache-dir langchain`)
4. Update `run_all.sh` to execute new agent script
5. Test locally before pushing to server

### Adding Dependencies
Edit `requirements/base.txt` to add pip packages:
```
# File format handling
openpyxl==3.1.2
xlrd==2.0.1
xlwt==1.3.0
lxml==5.1.0
```

## Recent Improvements

### Dataset Label Extraction (2026-01-02)
The ETL framework now correctly extracts dataset labels from import configuration settings instead of using hardcoded patterns.

**Previous Behavior:**
- Labels were hardcoded as: `{dataset_type}_{run_date}_{run_uuid[:8]}`
- Example: `RegressionTest_2026-01-02_f2909ee9`

**Current Behavior:**
- Labels extracted from `metadata_label_source` configuration in `dba.timportconfig`
- Supports three extraction modes:
  - `filename`: Extract from filename using delimiter and position
  - `file_content`: Extract from first record's specified column
  - `static`: Use provided static value
- Example labels: `Strategy1`, `MetadataFilename`, `EmptyTest`

**Implementation:**
- Modified `BaseETLJob` to accept optional `dataset_label` parameter
- Added `_extract_label_early()` method in `GenericImportJob`
- Label extracted before dataset record creation
- Consistent label used in both dataset creation and status updates

**Files Modified:**
- `etl/base/etl_job.py` - Added dataset_label parameter support
- `etl/jobs/generic_import.py` - Early label extraction logic

### Regression Testing Framework
Comprehensive regression test suite for the generic import system with 17 test configurations.

**Test Coverage:**
- **CSV Tests (6):** Strategy 1, 2, 3, metadata extraction, empty files, malformed data
- **XLS Tests (3):** Strategy 1, metadata from content, multiple sheets
- **XLSX Tests (3):** Strategy 2, date from content, large files (1000 records)
- **JSON Tests (3):** Array format, object format, nested objects
- **XML Tests (2):** Structured format, blob format

**Key Files:**
- `etl/regression/run_regression_tests.py` - Automated test runner
- `etl/regression/generate_test_files.py` - Test data generator (CSV, XLS, XLSX)
- `schema/dba/data/regression_test_configs.sql` - 17 test configurations
- `schema/dba/tables/tregressiontest.sql` - Test results tracking table
- `schema/dba/views/vregressiontest_summary.sql` - Test summary view

**Test Design Principles:**
1. **Consistent delimiters:** All configs use `_` delimiter
2. **Focused testing:** Each test validates ONE feature at a time
3. **Strategy 2 validation:** Uses same target table as Strategy 1 to test column ignoring
4. **Proper column structure:** Strategy 2 files have all Strategy 1 columns + extras

**Running Tests:**
```bash
# Run all regression tests
docker compose exec tangerine python etl/regression/run_regression_tests.py --verbose

# Run specific category
docker compose exec tangerine python etl/regression/run_regression_tests.py --category csv

# Generate test files
docker compose exec tangerine python etl/regression/generate_test_files.py
```

**Test Results Storage:**
- Individual test results: `dba.tregressiontest`
- Aggregated summaries: `dba.vregressiontest_summary`
- Linked to dataset records via `datasetid` and `run_uuid`

**Test Data Files Location:**
Regression test data files are stored in `./.data/etl/regression/` and are version-controlled in the repository:
```
./.data/etl/regression/
├── csv/
│   ├── Strategy1_Products_20260101T120000.csv       (5 records)
│   ├── Strategy2_Products_20260101T130000.csv       (3 records, extra columns)
│   ├── Strategy3_Orders_20260101T140000.csv         (4 records)
│   ├── MetadataFilename_20260101T150000.csv         (2 records)
│   ├── EmptyFile_20260101T160000.csv                (0 records, headers only)
│   └── MalformedData_20260101T170000.csv            (2 records)
├── xls/
│   ├── Strategy1_Inventory_20260101T110000.xls      (7 records)
│   ├── MetadataContent_20260101T120000.xls          (4 records)
│   └── MultipleSheets_20260101T130000.xls           (3 records)
├── xlsx/
│   ├── Strategy2_Sales_20260101T140000.xlsx         (10 records)
│   ├── DateContent_20260101T150000.xlsx             (5 records)
│   └── LargeFile_20260101T160000.xlsx               (1000 records)
├── json/
│   ├── ArrayFormat_20260104T120000.json
│   ├── ObjectFormat_20260104T130000.json
│   └── NestedObjects_20260104T140000.json
└── xml/
    ├── StructuredXML_20260105T120000.xml
    └── BlobXML_20260105T130000.xml
```

These files are automatically generated by `etl/regression/generate_test_files.py` and can be regenerated at any time. The files map to the 17 test configurations defined in `schema/dba/data/regression_test_configs.sql`.

### Adding a New Import Configuration

#### Directory Path Setup
The `source_directory` and `archive_directory` paths in `timportconfig` are **inside the Docker container** at `/app/data`. This path is mounted from your local machine via the volume configuration in `docker-compose.yml`:

```yaml
volumes:
  - ${ETL_DATA_PATH:-./.data/etl}:/app/data
```

This means:
- **Default path (local machine):** `./.data/etl` (relative to docker-compose.yml)
- **Inside container:** `/app/data`
- **Override path:** Set `ETL_DATA_PATH` environment variable

**Windows Development Setup:**
1. Create data directories (relative to docker-compose.yml):
```bash
mkdir -p ./.data/etl/source
mkdir -p ./.data/etl/archive
```
Actual Windows path: `C:\Users\...\tangerine\.data\etl\source`

2. Place your import files in `.\.data\etl\source\`

3. Use these paths in your import config:
   - `source_directory`: `/app/data/source`
   - `archive_directory`: `/app/data/archive`

Docker Desktop automatically mounts the Windows paths into the Linux container.

**Linux Server Deployment:**
Option 1: Use relative path (same as Windows):
```bash
mkdir -p ./.data/etl/source
mkdir -p ./.data/etl/archive
docker compose up --build
```

Option 2: Use custom path (recommended for production):
```bash
# Set environment variable before running docker compose
export ETL_DATA_PATH=/opt/tangerine/data
mkdir -p /opt/tangerine/data/source
mkdir -p /opt/tangerine/data/archive
docker compose up --build
```

Both approaches use the same `/app/data` paths inside the container.

#### Create Configuration
1. Ensure `datasource` exists in `dba.tdatasource`
2. Ensure `datasettype` exists in `dba.tdatasettype`
3. Create target table in `feeds` schema following naming conventions
4. Ensure source and archive directories exist in container (or are mounted from local machine)
5. Insert configuration into `dba.timportconfig`:
```sql
CALL dba.pimportconfigi(
    'MyImportConfig',           -- config_name
    'MyDataSource',             -- datasource (must exist in tdatasource)
    'MyDataType',               -- datasettype (must exist in tdatasettype)
    '/app/data/source',         -- source_directory (mounted via volume)
    '/app/data/archive',        -- archive_directory (mounted via volume)
    '.*MyPattern\\.csv',        -- file_pattern (regex)
    'CSV',                      -- file_type (CSV, XLS, XLSX, JSON, XML)
    'static',                   -- metadata_label_source (filename, file_content, static)
    'MyLabel',                  -- metadata_label_location
    'filename',                 -- dateconfig (filename, file_content, static)
    '0',                        -- datelocation (position index for filename)
    'yyyyMMddTHHmmss',          -- dateformat
    '_',                        -- delimiter (for parsing filenames)
    'feeds.my_table',           -- target_table
    1,                          -- importstrategyid (1=add cols, 2=ignore, 3=fail)
    TRUE                        -- is_active
);
```
6. Run import: `docker compose exec tangerine python etl/jobs/generic_import.py --config-id <new_id>`

### Volume Mount Verification

The volume mount for ETL data directories has been tested and verified as working correctly. Here's what was confirmed:

**Test Setup:**
- Created test directories: `./.data/etl/source/` and `./.data/etl/archive/`
- Created test CSV file: `20260105T150000_VolumeTest.csv` with 3 product records
- Created feeds table: `feeds.volume_test` with columns for product, price, quantity
- Created import config (config_id=4) "VolumeTestImport" with `/app/data/source` and `/app/data/archive` paths
- Rebuilt containers with `docker compose up --build`

**Import Execution Results:**
- ✓ CSV file successfully located in `/app/data/source` (mounted from local `.data/etl/source`)
- ✓ Extracted and loaded 3 records into `feeds.volume_test` table
- ✓ All business columns correctly populated: product, price, quantity
- ✓ Audit trail properly recorded: created_date, created_by (etl_user)
- ✓ Dataset tracking: all records linked to datasetid=9
- ✓ Files successfully archived from source to `/app/data/archive` inside container
- ✓ Archived files are also accessible on local machine at `.data/etl/archive/`

**Key Findings:**
- Windows bind mount works seamlessly with Docker Desktop
- Bidirectional file access confirmed (local → container → local)
- Volume mount uses `${ETL_DATA_PATH:-./.data/etl}` which allows:
  - **Development (Windows)**: Default `./.data/etl` maps to `/app/data`
  - **Deployment (Linux)**: Set `ETL_DATA_PATH=/opt/tangerine/data` environment variable
- File archiving preserves timestamps and handles bidirectional sync correctly

The generic import system is production-ready for CSV/XLS/XLSX/JSON/XML imports across all three import strategies.

## Docker Services

### db (PostgreSQL 18)
- Runs init scripts from `/docker-entrypoint-initdb.d/init.sh` on first startup
- Mounts `schema/` directory to `/app/schema` for SQL file access
- Persists data in named volume `db_data`
- Exposes port 5432

### tangerine (Python 3.11-slim)
- Current CMD runs `common/db_utils.py` for testing
- Update CMD in Dockerfile to change default execution
- Has access to all `/app` files and `DB_URL` environment variable

## Deployment Workflow

1. Develop and test locally on Windows using Docker Desktop
2. Commit and push changes: `git add . && git commit -m "message" && git push origin main`
3. SSH to server: `ssh user@server-ip`
4. Pull changes: `cd /opt/tangerine && git pull`
5. Rebuild and start: `docker compose up --build` (or use `./run_all.sh`)

## Troubleshooting

### Database Connection Issues
- Verify `.env` file exists and contains correct `DB_URL`
- Ensure PostgreSQL service is running: `docker compose ps`
- Check logs: `docker compose logs db`

### Schema Changes Not Applying
- Database initialization only runs on first container creation
- To reapply schema: `docker compose down --volumes && docker compose up --build`
- Volumes flag removes persisted data

### Git Authentication
- Ensure SSH keys are configured for GitHub access
- Test connection: `ssh -T git@github.com`