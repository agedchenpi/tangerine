# CLAUDE.md

This file provides guidance to Claude Code when working with the Tangerine ETL project.

## Working Instructions

**Load up context prompt:**
Take a look at the app and architecture. Understand deeply how it works inside and out. Ask me any questions if there are things you don't understand. This will be the basis for the rest of our conversation.

**Tool use summaries:**
After completing a task that involves tool use, provide a quick summary of the work you've done.

**Adjust eagerness down:**
Do not jump into implementation or change files unless clearly instructed to make changes. When the user's intent is ambiguous, default to providing information, doing research, and providing recommendations rather than taking action. Only proceed with edits, modifications, or implementations when the user explicitly requests them.

**Use parallel tool calls:**
If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the actions can be done in parallel rather than sequentially. For example, when reading 3 files, run 3 tool calls in parallel to read all 3 files into context at the same time. Maximize use of parallel tool calls where possible to increase speed and efficiency. However, if some tool calls depend on previous calls to inform dependent values like the parameters, do not call these tools in parallel and instead call them sequentially. Never use placeholders or guess missing parameters in tool calls.

**Reduce hallucinations:**
Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer - give grounded and hallucination-free answers.

## Project Overview

Tangerine is an AI-integrated ETL pipeline built with Vertical Slice Architecture (VSA). The project uses:
- **PostgreSQL 18** for data storage
- **Python 3.11** for ETL logic
- **Docker** for containerization
- **Streamlit** for web-based admin interface

**Development**: Windows with Docker Desktop
**Deployment**: Ubuntu 24.04 LTS server via SSH

## Codebase Structure

```
/opt/tangerine/
├── admin/                          # Streamlit web interface
│   ├── app.py                      # Landing page
│   ├── pages/                      # Auto-discovered pages
│   │   ├── 1_Import_Configs.py     # CRUD for import configs
│   │   ├── 2_Reference_Data.py     # Manage datasources/types
│   │   ├── 3_Run_Jobs.py           # Execute imports, view history
│   │   └── 4_Monitoring.py         # View logs, datasets, statistics
│   ├── components/                 # Reusable UI components
│   │   ├── forms.py                # Form builders
│   │   ├── tables.py               # Data display
│   │   ├── validators.py           # Input validation
│   │   └── notifications.py        # User messages
│   ├── services/                   # Business logic
│   │   ├── import_config_service.py
│   │   ├── reference_data_service.py
│   │   ├── job_execution_service.py
│   │   └── monitoring_service.py   # Logs, datasets, statistics
│   ├── utils/                      # Helper utilities
│   │   ├── db_helpers.py
│   │   ├── formatters.py
│   │   └── ui_helpers.py           # UI functions (loading, errors, etc.)
│   └── styles/                     # CSS styling
│       └── custom.css              # Professional Tangerine theme
├── common/                         # Shared utilities
│   ├── db_utils.py                 # Database connection pooling
│   ├── config.py                   # Configuration management
│   └── logging_utils.py            # ETL logging
├── etl/                            # ETL jobs and framework
│   ├── base/
│   │   └── etl_job.py              # Base ETL job class
│   ├── jobs/
│   │   └── generic_import.py       # Config-driven imports
│   └── regression/
│       ├── run_regression_tests.py
│       └── generate_test_files.py
├── tests/                          # Admin interface test suite
│   ├── conftest.py                 # Test fixtures and config
│   ├── pytest.ini                  # Pytest configuration
│   ├── unit/                       # Unit tests (validators, utils)
│   ├── integration/                # Integration tests (services)
│   └── fixtures/                   # Reusable test data
├── schema/                         # Database definitions
│   ├── init.sh                     # Initialization script
│   ├── dba/                        # Pipeline schema
│   │   ├── schema.sql
│   │   ├── tables/                 # timportconfig, tdataset, etc.
│   │   ├── procedures/             # pimportconfigi, pimportconfigu
│   │   ├── views/
│   │   └── data/                   # Reference data inserts
│   └── feeds/                      # Raw data schema
├── .data/etl/                      # Volume mount (local)
│   ├── source/                     # Input files
│   ├── archive/                    # Processed files
│   └── regression/                 # Test data
├── docker-compose.yml              # Service definitions
├── Dockerfile                      # ETL container
├── Dockerfile.streamlit            # Admin container
└── requirements/
    ├── base.txt                    # ETL dependencies
    └── admin.txt                   # Streamlit dependencies
```

## Architecture Patterns

**Vertical Slice Architecture:**
- Each feature is self-contained with its own UI, logic, and data access
- Admin pages are independent slices
- Services encapsulate database operations

**Service Layer Pattern:**
- `services/` contain business logic and database operations
- `components/` are pure UI elements
- `utils/` are stateless helper functions

**Database Design:**
- `dba` schema: ETL pipeline configuration and logging
- `feeds` schema: Raw data storage
- All tables use idempotent SQL with `IF NOT EXISTS` checks

## What's Been Accomplished

### ✅ Phase 1: Infrastructure (Complete)
- Docker containerization (db, tangerine, admin services)
- PostgreSQL database with schemas
- Connection pooling and transaction management
- Streamlit admin landing page

### ✅ Phase 2: Core Framework (Complete)
- Notification system (success/error/warning/info)
- Validators (8 validation functions)
- Database helpers (count, exists, distinct values)
- Formatters (10 display utilities)
- Enhanced dashboard with metrics

### ✅ Phase 3: Import Configuration Management (Complete)
- Full CRUD interface for `dba.timportconfig`
- Form with all 19 configuration fields
- Dynamic fields based on metadata/date source selection
- Real-time validation (paths, regex, table names)
- Duplicate name checking
- Success messages with session state persistence

### ✅ Phase 4: Reference Data Management (Complete)
- CRUD for datasources (`dba.tdatasource`)
- CRUD for dataset types (`dba.tdatasettype`)
- Read-only view of import strategies
- Duplicate checking and referential integrity
- Delete protection for referenced records

### ✅ Phase 5: Job Execution (Complete)
- Select and execute import jobs from UI
- Real-time output streaming using subprocess
- Dry-run mode (validation without database writes)
- 5-minute timeout protection
- Job history viewer with filtering
- Detailed output lookup by run_uuid
- Status indicators (Success/Failed/Running)

### ✅ Phase 6: System Monitoring (Complete)
- **Logs Tab**: View/filter ETL logs from `dba.tlogentry`
  - Time range filters (1h, 6h, 24h, 7d, 30d, all time)
  - Process type and run_uuid filtering
  - CSV export functionality
- **Datasets Tab**: Browse `dba.tdataset` records
  - Filter by datasource, datasettype, date range
  - Display status and metadata
- **Statistics Tab**: Metrics and charts
  - 6 key metrics cards
  - Jobs per day line chart (30 days)
  - Process type distribution bar chart
  - Runtime statistics table

### ✅ Phase 7: Polish & Production Ready (Complete)
- Custom CSS styling with Tangerine theme
- Enhanced UI components (cards, tables, buttons)
- Loading spinners and progress indicators
- Improved error handling throughout
- Responsive design for mobile/tablet
- Professional animations and transitions

### ✅ ETL Framework (Complete)
- Generic import system supporting CSV, XLS, XLSX, JSON, XML
- 3 import strategies (auto-add columns, ignore extras, strict)
- Metadata extraction (filename, file_content, static)
- Date parsing with configurable formats
- File archiving after processing
- Dataset tracking with run_uuid

### ✅ Testing Infrastructure (Complete)
**ETL Tests:**
- 17 ETL regression tests (100% pass rate)
- Test data generation scripts
- Volume mount verification

**Admin Tests:**
- 137 pytest-based tests for admin interface
- 57 unit tests for validators (100% pass rate)
- 80 integration tests for services (CRUD, filtering, monitoring)
- Transaction-based test isolation with automatic rollback
- Comprehensive fixtures for test data

## What's Planned

### 🔮 Future Enhancements
- **Authentication/authorization**: Session-based auth or OAuth
- **Scheduled jobs**: Cron-like job scheduler with recurring imports
- **Email notifications**: Alert on job failures or completion
- **Data quality checks**: Automated validation rules and anomaly detection
- **AI agent integration**: LLM-powered data analysis and recommendations
- **Performance dashboard**: Real-time metrics and health monitoring
- **Audit logging**: Track all admin actions and changes
- **Bulk operations**: Import/export multiple configs at once
- **Configuration templates**: Reusable config templates for common patterns
- **Data lineage**: Visual graph of data flow and dependencies

## Key Database Tables

**Configuration & Reference:**
- `dba.timportconfig` - Import job configurations (config_id, config_name, file_pattern, etc.)
- `dba.tdatasource` - Data source reference
- `dba.tdatasettype` - Dataset type reference
- `dba.timportstrategy` - Import strategies (3 predefined)

**Tracking & Logging:**
- `dba.tdataset` - Dataset metadata (datasetid, label, status, dates)
- `dba.tlogentry` - ETL execution logs (run_uuid, message, stepruntime)

**Data Storage:**
- `feeds.*` - Target tables for imported data (must have datasetid FK)

## Common Commands

### Development
```bash
# Start all services
docker compose up --build

# Detached mode
docker compose up -d

# Rebuild specific service
docker compose up --build -d admin

# View logs
docker compose logs -f admin
docker compose logs -f tangerine

# Reset database (WARNING: deletes all data)
docker compose down --volumes && docker compose up --build
```

### Running Jobs
```bash
# Execute import job
docker compose exec tangerine python etl/jobs/generic_import.py --config-id 1

# Dry run mode
docker compose exec tangerine python etl/jobs/generic_import.py --config-id 1 --dry-run

# With specific date
docker compose exec tangerine python etl/jobs/generic_import.py --config-id 1 --date 2026-01-15

# Run ETL regression tests
docker compose exec tangerine python etl/regression/run_regression_tests.py --verbose
```

### Running Tests
```bash
# Run all admin tests
docker compose exec tangerine pytest tests/ -v

# Run unit tests only (fast, no database)
docker compose exec tangerine pytest tests/unit/ -v -m unit

# Run integration tests only (requires database)
docker compose exec tangerine pytest tests/integration/ -v -m integration

# Run specific test file
docker compose exec tangerine pytest tests/unit/test_validators.py -v

# Run with coverage report
docker compose exec tangerine pytest tests/ --cov=admin --cov-report=html
```

### Database Access
```bash
# Connect to database
docker compose exec db psql -U tangerine_admin -d tangerine_db

# Test connection from ETL container
docker compose exec tangerine python common/db_utils.py

# Test connection from admin container
docker compose exec admin python -c "from common.db_utils import test_connection; print(test_connection())"
```

### Admin Interface
**Access:** `http://localhost:8501` (local) or `http://<server-ip>:8501` (server)

**Features:**
- Dashboard with system metrics
- Import Configs: Create, view, edit, delete configurations
- Reference Data: Manage datasources and dataset types
- Run Jobs: Execute imports with real-time output
- Monitoring: View logs, datasets, and statistics with charts

## Environment Variables

Required `.env` file (never commit):
```
POSTGRES_DB=tangerine_db
POSTGRES_USER=tangerine_admin
POSTGRES_PASSWORD=your_secure_password
ETL_USER_PASSWORD=your_etl_password
ADMIN_PASSWORD=your_admin_password
DB_URL=postgresql://tangerine_admin:your_secure_password@db:5432/tangerine_db
```

## Volume Mounts

**ETL Data:** `./.data/etl ↔ /app/data` (bidirectional)
- Local: `./.data/etl/source/` → Container: `/app/data/source/`
- Local: `./.data/etl/archive/` ← Container: `/app/data/archive/`

**Tested and verified:** Files sync bidirectionally between Windows and Linux container

## Critical Implementation Details

### UI Helpers and Styling
**Custom CSS**: `admin/styles/custom.css` - Professional Tangerine theme
- Color palette with CSS variables
- Enhanced buttons, forms, tables, tabs
- Metric cards with hover effects
- Responsive design for mobile/tablet
- Smooth animations and transitions

**UI Helper Functions**: `admin/utils/ui_helpers.py`
- `load_custom_css()` - Load custom styling
- `add_page_header()` - Styled page headers with icon/subtitle
- `with_loading()` - Execute functions with spinner
- `safe_execute()` - Error handling wrapper
- `render_empty_state()` - Placeholder for no data
- `render_stat_card()` - Custom metric cards
- `show_loading_progress()` - Multi-step progress indicator

### Import Strategies
1. **Strategy 1**: Auto-add columns (ALTER TABLE if new columns detected)
2. **Strategy 2**: Ignore extras (only import matching columns)
3. **Strategy 3**: Strict validation (fail if column mismatch)

### Metadata Extraction Modes
- **filename**: Extract from filename using delimiter and position index
- **file_content**: Extract from specified column in data
- **static**: Use fixed value for all records

### SQL Pattern Escaping
**IMPORTANT**: When using LIKE patterns in psycopg2 queries, double the percent signs:
```python
# WRONG - causes "tuple index out of range"
query = "SELECT * FROM table WHERE message LIKE '%ERROR%'"

# CORRECT
query = "SELECT * FROM table WHERE message LIKE '%%ERROR%%'"
```

### Streamlit Form Keys
All forms need unique keys even across tabs:
```python
# WRONG - conflicts if multiple forms exist
with st.form(key="my_form"):

# CORRECT - unique per context
form_key = "my_form_edit" if is_edit else "my_form_create"
with st.form(key=form_key):
```

### Session State for Success Messages
Use session state to persist messages across `st.rerun()`:
```python
# Store message
st.session_state.success_message = "Operation completed!"
st.rerun()

# Display and clear
if 'success_message' in st.session_state:
    show_success(st.session_state.success_message)
    del st.session_state.success_message
```

## Deployment Workflow

1. **Develop locally** on Windows with Docker Desktop
2. **Commit and push**: `git add . && git commit -m "message" && git push`
3. **SSH to server**: `ssh user@server-ip`
4. **Pull and rebuild**: `cd /opt/tangerine && git pull && docker compose up --build -d`

## Troubleshooting

**Admin won't start:**
- Check logs: `docker compose logs admin`
- Rebuild: `docker compose up --build admin`

**Database connection failed:**
- Verify `.env` file exists with correct `DB_URL`
- Check db service is healthy: `docker compose ps`

**Volume mount not working:**
- Verify `./.data/etl/` directories exist
- Check docker-compose.yml volume configuration
- Restart Docker Desktop (Windows)

**Job execution timeout:**
- Default 5 minutes - increase in `job_execution_service.py` if needed
- Check for large files or slow processing

## Important Notes

- **Never commit `.env` files** - contains secrets
- **Always use parameterized queries** - prevents SQL injection
- **Connection pooling** - max 10 connections, reuse via `db_transaction()`
- **All SQL is idempotent** - safe to re-run initialization
- **Volume mounts are bidirectional** - files sync both ways
- **Admin service auto-reloads** - edit files and refresh browser in dev mode
