# Tangerine: AI-Integrated ETL Project

## Overview
Tangerine is an ETL (Extract, Transform, Load) pipeline project designed to integrate AI agents using Vertical Slice Architecture (VSA) for modularity, readability, and efficiency in AI-driven workflows. It leverages PostgreSQL for data storage, Python for scripting, Docker for containerization and isolation, and Git for version control. Development occurs on a Windows desktop, with deployment to a Linux server (Ubuntu 24.04 LTS) via SSH. The setup enables reproducible environments, easy scaling for AI agents for monitoring database, agents, and filesystem activity accessible via browser on desktop.

The architecture emphasizes atomic, composable slices to facilitate AI agent integration, making it easier to build, test, and maintain components independently.

## Data Flow: Docker to Database

Here's the complete workflow from Docker startup to data persisted in the database:

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
│  │  └─ Executes init.sh             │    │  └─ Ready for commands       │   │
│  └──────────────────────────────────┘    └──────────────────────────────┘   │
│                           ↓                                                  │
│        Volume Mount: ./.data/etl ↔ /app/data (bidirectional)               │
└─────────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATABASE INITIALIZATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Schema creation: dba (pipeline config) & feeds (raw data storage)         │
│  Table setup: timportconfig, timportstrategy, tdataset, tlogentry          │
│  User/Role setup: etl_user (for ETL), app_rw (read-write), app_ro (read) │
└─────────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│               USER: PLACE FILES & CREATE CONFIGURATION                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Place CSV/XLS/XLSX/JSON/XML files in ./.data/etl/source/              │
│  2. Create target table in feeds schema (with datasetid FK)                │
│  3. Insert import config row into dba.timportconfig                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│              IMPORT JOB EXECUTION: 5-Phase Pipeline                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 1: SETUP                                                             │
│  └─ Fetch config, create dataset record, load import strategy              │
│                                 ↓                                            │
│  PHASE 2: EXTRACT                                                           │
│  └─ Scan files, parse CSV/Excel/JSON/XML, extract metadata & dates         │
│                                 ↓                                            │
│  PHASE 3: TRANSFORM                                                         │
│  └─ Normalize columns, apply import strategy, add audit fields              │
│                                 ↓                                            │
│  PHASE 4: LOAD                                                              │
│  └─ Validate schema, ALTER TABLE if needed, bulk insert records            │
│                                 ↓                                            │
│  PHASE 5: CLEANUP                                                           │
│  └─ Archive files, update config, log metrics                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA AT REST                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  PostgreSQL Database:                                                       │
│  ├─ dba.tdataset (tracks dataset load metadata)                            │
│  ├─ dba.tlogentry (audit trail with run_uuid)                             │
│  └─ feeds.* (raw business data linked to dataset)                          │
│                                                                              │
│  Local File System (via volume mount):                                      │
│  └─ ./.data/etl/archive/ (processed files synced bidirectionally)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **Files are bidirectional**: Place files in `./.data/etl/source/` on Windows, they appear at `/app/data/source/` in container
- **All operations inside container**: The import job runs inside the Docker container, reading from and writing to mounted volumes
- **Archived files sync back**: After import, files are moved to `/app/data/archive/` and automatically sync back to `./.data/etl/archive/` on Windows
- **Dataset tracking**: All imported records are linked to a dataset record (dba.tdataset) for auditability
- **3 Import Strategies**: Control how to handle column mismatches (add/ignore/fail)

## Project Structure

The project follows a Vertical Slice Architecture (VSA) for modularity, with shared SQL schemas and utils to support AI agents in ETL workflows.

```
/opt/tangerine/
├── admin/                          # Streamlit web interface
│   ├── app.py                      # Landing page
│   ├── pages/                      # Auto-discovered pages
│   │   ├── 1_Import_Configs.py     # CRUD for import configs
│   │   ├── 2_Reference_Data.py     # Manage datasources/types
│   │   ├── 3_Run_Jobs.py           # Execute imports, view history
│   │   ├── 4_Monitoring.py         # View logs, datasets, statistics
│   │   ├── 5_Inbox_Configs.py      # Gmail inbox processing rules
│   │   ├── 6_Report_Manager.py     # Email report configuration
│   │   └── 7_Scheduler.py          # Cron job management
│   ├── components/                 # Reusable UI components
│   │   ├── forms.py                # Form builders
│   │   ├── tables.py               # Data display
│   │   ├── validators.py           # Input validation
│   │   └── notifications.py        # User messages
│   ├── services/                   # Business logic
│   │   ├── import_config_service.py
│   │   ├── reference_data_service.py
│   │   ├── job_execution_service.py
│   │   ├── monitoring_service.py   # Logs, datasets, statistics
│   │   ├── inbox_config_service.py # Gmail inbox config CRUD
│   │   ├── report_manager_service.py # Report config CRUD
│   │   └── scheduler_service.py    # Scheduler CRUD
│   ├── utils/                      # Helper utilities
│   │   ├── db_helpers.py
│   │   ├── formatters.py
│   │   └── ui_helpers.py           # UI functions (loading, errors, etc.)
│   └── styles/                     # CSS styling
│       └── custom.css              # Professional Tangerine theme
├── common/                         # Shared utilities
│   ├── db_utils.py                 # Database connection pooling
│   ├── config.py                   # Configuration management
│   ├── logging_utils.py            # ETL logging
│   └── gmail_client.py             # Gmail API wrapper (OAuth2)
├── etl/                            # ETL jobs and framework
│   ├── base/
│   │   └── etl_job.py              # Base ETL job class
│   ├── jobs/
│   │   ├── generic_import.py       # Config-driven imports
│   │   ├── run_gmail_inbox_processor.py  # Download email attachments
│   │   ├── run_report_generator.py       # Generate & send reports
│   │   └── generate_crontab.py           # Generate cron from DB
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
│   │   ├── tables/                 # timportconfig, tdataset, tinboxconfig, etc.
│   │   ├── procedures/             # pimportconfigi, pimportconfigu, etc.
│   │   ├── views/
│   │   └── data/                   # Reference data inserts
│   └── feeds/                      # Raw data schema
├── secrets/                        # Gmail OAuth credentials (gitignored)
│   ├── credentials.json            # OAuth client ID/secret
│   └── token.json                  # Access/refresh tokens
├── .data/etl/                      # Volume mount (local)
│   ├── source/                     # Input files
│   │   └── inbox/                  # Email attachments landing
│   ├── archive/                    # Processed files
│   └── regression/                 # Test data
├── .claude/                        # Claude Code configuration
│   ├── commands/                   # Slash commands
│   ├── hooks/                      # Event hooks (Python)
│   ├── skills/                     # Domain-specific guidelines
│   ├── agents/                     # Sub-agent templates
│   ├── codemaps/                   # Architecture documentation
│   └── settings.json               # Hook configuration
├── docker-compose.yml              # Service definitions
├── Dockerfile                      # ETL container
├── Dockerfile.streamlit            # Admin container
└── requirements/
    ├── base.txt                    # ETL dependencies
    └── admin.txt                   # Streamlit dependencies
```

### Key Directories

- **admin/**: Streamlit web interface with pages, components, services, and utilities
- **common/**: Shared utilities for database, logging, and Gmail integration
- **etl/**: ETL jobs and framework for data imports and processing
- **tests/**: Pytest test suite for admin interface
- **schema/**: PostgreSQL schema definitions (dba and feeds schemas)
- **.claude/**: Claude Code configuration (commands, hooks, skills, agents)

## Prerequisites
- **Server**: Ubuntu 24.04 LTS with SSH access enabled.
- **Git**: Installed on both server and Windows.
- **Docker**: Docker Engine and Compose on the server; Docker Desktop on Windows for local testing.
- **GitHub Account**: For hosting the repo.
- **Windows Tools**: Git Bash or PowerShell for CLI; optional editor like VS Code.

## Setup and Run Steps
Cloning the repo deploys the core code structure, but additional intermediate steps are required for full functionality, such as directory ownership, environment variables, and Docker installation. Follow these sequentially.

### 1. Server Initial Setup (One-Time)
SSH into your Ubuntu server and run these to prepare the environment:

sudo apt update && sudo apt upgrade -y
sudo apt install git -y  # Install Git if not present
sudo mkdir /opt/tangerine
sudo chown $USER:$USER /opt/tangerine  # Replace $USER with your username, e.g., chenpi
cd /opt/tangerine
git clone git@github.com:agedchenpi/tangerine.git .  # Clone into the dir (note the dot)


Install Docker and Compose (if not already done):

```
sudo apt install apt-transport-https ca-certificates curl software-properties-common -y
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y
sudo usermod -aG docker $USER  # Log out and SSH back in for effect
```

Verify Docker:
```
docker --version
docker compose version
```

Create a local .env file in /opt/tangerine for secrets (use nano or vi; do not commit this file):
```
POSTGRES_DB=tangerine_db
POSTGRES_USER=tangerine_admin
POSTGRES_PASSWORD=your_secure_password
DB_URL=postgresql://tangerine_admin:your_secure_password@db:5432/tangerine_db
```

Make run_all.sh executable:
```
chmod +x run_all.sh
```

### 2. Windows Development Setup (One-Time)
Install Git on Windows if not already (from git-scm.com). Install Docker Desktop from docker.com for local testing.

Clone the repo:
```
git clone git@github.com:agedchenpi/tangerine.git
cd tangerine
```

Create a local .env file in the tangerine dir (use Notepad or VS Code) with the same content as on the server (adjust passwords as needed).

### 2.5 Local Testing on Windows
For quick iteration without SSH:
- Ensure Docker Desktop is running.
- Run: `docker compose up --build` (expect "Connected to DB" if testing db_utils.py).
- Shutdown: `docker compose down --volumes` (resets data if needed).

### 3. Deploy and Test on Server
After editing on Windows, commit and push changes:
```
git add .
git commit -m "Your commit message"
git push origin main
```

On server:
```
cd /opt/tangerine
git pull
docker compose up --build  # Attach for logs; add -d for detached mode
```

Test DB connection: Look for "Connected to DB" in output. Shutdown:


To run the orchestration script:

```
./run_all.sh
```


### 4. Adding AI Agents
- Create a new slice directory (e.g., mkdir features/agent1).
- Add Python script (e.g., features/agent1/main.py) with AI logic (import LangChain or similar).
- Update Dockerfile to add dependencies: e.g., add 
```
RUN pip install --no-cache-dir langchain
```
 after existing installs.
- Update run_all.sh to exec the new script: e.g., `docker compose exec tangerine python features/agent1/main.py`.
- Test locally on Windows first, then push and deploy on server.

### 5. Adding Dashboards
- Add a new service in docker-compose.yml for Streamlit (e.g., image: python:3.11-slim, command: streamlit run dashboard.py).
- Create dashboard.py with monitoring logic (e.g., query DB, display agent status).
- Access via SSH tunnel from Windows: `ssh -L 8501:localhost:8501 user@server-ip` (then open localhost:8501 in browser).

## Streamlit Admin Interface

The Tangerine ETL pipeline includes a comprehensive web-based administration interface built with Streamlit. This interface allows users to manage ETL configurations, execute jobs, and monitor pipeline health without needing SQL knowledge or command-line access.

### Accessing the Admin Interface

**Local Development (Windows):**
```
http://localhost:8501
```

**Server Deployment (Ubuntu):**
```
http://<server-ip>:8501
```

Example: If your server IP is `192.168.1.100`, access at `http://192.168.1.100:8501`

**Network Configuration:**
- The admin service binds to `0.0.0.0:8501` and is accessible from any machine on the local network
- No authentication required (relies on network-level security)
- For production, restrict access using firewall rules:
  ```bash
  # Ubuntu server - allow port 8501 from local subnet only
  sudo ufw allow from 192.168.1.0/24 to any port 8501
  sudo ufw reload
  ```

### Starting the Admin Service

The admin service is part of the Docker Compose stack:

```bash
# Start all services including admin
docker compose up --build

# Start in detached mode
docker compose up -d

# View admin service logs
docker compose logs -f admin

# Restart just the admin service
docker compose restart admin

# Stop all services
docker compose down
```

### Admin Features Implementation Status

**✅ Phase 1: Basic Infrastructure (Complete)**
- Landing page with system overview
- Database connection status indicator
- Navigation sidebar with feature descriptions
- Responsive layout with wide mode enabled
- Custom CSS with Tangerine color scheme

**✅ Phase 2: Core Framework Components (Complete)**
- **Notifications** (`admin/components/notifications.py`): Success/error/warning/info message system
- **Validators** (`admin/components/validators.py`): 8 validation functions for forms (paths, regex, table names, etc.)
- **Database Helpers** (`admin/utils/db_helpers.py`): Count, exists, distinct values, error formatting
- **Formatters** (`admin/utils/formatters.py`): 10 display formatting utilities (timestamps, durations, booleans, etc.)
- **Enhanced Dashboard** (`admin/app.py`):
  - Live metrics: Active configs, jobs (24h), total datasets
  - Feature tabs with detailed descriptions
  - Quick start guide
  - Refresh button with timestamp display

**✅ Phase 3: Import Configuration Management (Complete)**
- **Full CRUD Interface** for `dba.timportconfig` with 4 tabs:
  - **View All Configs**: Searchable table with all 19 fields
  - **Create New**: Form-based creation with validation
  - **Edit Existing**: Update configurations with duplicate checking
  - **Delete**: Safe deletion with confirmation dialogs
- **Features:**
  - All 19 `timportconfig` fields supported
  - Dropdown selection for datasource, datasettype, and import strategy
  - Dynamic form fields based on metadata/date source selection
  - Real-time validation (directory paths, regex patterns, table names)
  - Duplicate name checking with exclude logic for updates
  - Success messages persist across page reloads using session state
  - Editable configuration names during updates

**✅ Phase 4: Reference Data Management (Complete)**
- **Data Sources Tab** (`dba.tdatasource`):
  - View all data sources
  - Add new data sources
  - Edit existing sources
  - Delete with referential integrity checking
- **Dataset Types Tab** (`dba.tdatasettype`):
  - View all dataset types
  - Add new types
  - Edit existing types
  - Delete with referential integrity checking
- **Import Strategies Tab** (read-only):
  - View 3 predefined strategies
  - Display strategy IDs and descriptions
  - No create/edit/delete (strategies are system-defined)
- **Features:**
  - Duplicate name checking
  - Prevent deletion if referenced by import configs
  - Session state for success messages
  - Inline editing with unique form keys

**✅ Phase 5: Job Execution (Complete)**
- **Execute Job Tab**:
  - Select active import configuration from dropdown
  - Set run date (default: today)
  - Toggle dry-run mode (validation without database writes)
  - Real-time output streaming (subprocess-based)
  - 5-minute timeout protection
  - Visual status indicators (✅ Success, ❌ Failed, ⏳ Running)
  - Configuration details preview
  - Full output display with last 50 lines shown live
- **Job History Tab**:
  - View recent job runs (10/25/50/100)
  - Sortable columns: run_uuid, process type, start time, steps, status, runtime
  - Detailed output viewer by run_uuid
  - Formatted timestamps and durations
  - Refresh button for manual updates
- **Features:**
  - Executes `etl/jobs/generic_import.py` from UI
  - Streams stdout/stderr in real-time
  - Handles job completion/failure detection
  - Archive viewing capability
  - No page refresh required during execution

**✅ Phase 6: System Monitoring (Complete)**
- **Logs Tab**: View/filter ETL logs from `dba.tlogentry`
  - Time range filters (1h, 6h, 24h, 7d, 30d, all time)
  - Process type and run_uuid filtering
  - Max results selection (50/100/250/500/1000)
  - CSV export with proper quote escaping
  - Real-time data refresh
- **Datasets Tab**: Browse dataset records from `dba.tdataset`
  - Filter by datasource and datasettype (with JOINs to reference tables)
  - Date range selection (from/to)
  - Max results selection (50/100/250/500)
  - Display status, metadata, and active state
  - Formatted timestamps and boolean indicators
- **Statistics Tab**: System metrics and charts
  - 6 key metric cards (logs 24h, unique processes, avg runtime, datasets 30d, active datasets, active configs)
  - Jobs per day line chart (last 30 days)
  - Process type distribution bar chart with data table
  - Runtime statistics table (avg/min/max by process type, last 7 days)
- **Monitoring Service** (`admin/services/monitoring_service.py`):
  - Complete query functions for logs, datasets, and statistics
  - CSV export functionality for log data
  - Optimized database queries with proper JOINs

**✅ Phase 7: Polish & Production Ready (Complete)**
- **Custom CSS Styling**: Professional Tangerine theme with enhanced UI
  - Color palette using CSS variables
  - Hover effects and smooth transitions
  - Enhanced buttons, forms, tables, and tabs
  - Responsive design for mobile/tablet devices
- **UI Helper Module** (`admin/utils/ui_helpers.py`):
  - `load_custom_css()` - Automatic CSS loading
  - `add_page_header()` - Styled page headers with icons
  - `with_loading()` - Execute functions with spinners
  - `safe_execute()` - Error handling wrapper
  - `render_empty_state()` - No data placeholders
  - `render_stat_card()` - Custom metric cards
  - `show_loading_progress()` - Multi-step progress bars
- **Enhanced User Experience**:
  - Loading spinners for all long operations
  - Professional error messages with helpful context
  - Smooth animations and fade-in effects
  - Improved visual hierarchy and spacing

**✅ Phase 8: Testing Infrastructure (Complete)**
- **ETL Tests**: 17 regression tests for ETL pipeline (100% pass rate)
- **Admin Tests**: 310 pytest-based tests for admin interface (100% pass rate)
  - Unit tests for validators and pattern matching
  - Integration tests for all services (import config, reference data, monitoring, inbox config, scheduler, report manager, pubsub)
  - Transaction-based test isolation with automatic rollback
  - Comprehensive fixtures for test data
- **Test Execution**: `pytest tests/ -v` or `pytest tests/unit/ -m unit`

**✅ Phase 9: Pub/Sub Event System (Complete - January 2026)**
- **Database Schema**
  - `dba.tpubsub_events` - Event queue table
  - `dba.tpubsub_subscribers` - Subscriber configuration table
  - `ppubsub_iu` - Stored procedure for upserts
- **Python Daemon** (`pubsub/listener.py`)
  - File watcher for event triggers
  - Database poller for queued events
  - Subscriber notification system
- **Admin UI** (`8_Event_System.py`)
  - Event Queue tab - View pending/processed events
  - Subscribers tab - CRUD for event subscribers
  - Event Log tab - Historical event tracking
  - Service Status tab - Monitor pubsub daemon
- **Service Layer** (`pubsub_service.py`)
  - Full CRUD for events and subscribers
  - Event filtering by type, source, status
- **ETL Integration**
  - `generic_import.py` emits `import_complete` event
  - `run_report_generator.py` emits `report_sent` event
  - `run_gmail_inbox_processor.py` emits `email_received` event
- **Docker Integration**: `Dockerfile.pubsub` and docker-compose.yml updated

### What's Planned

**Future Enhancements:**
- **Authentication/authorization**: Session-based auth or OAuth
- **Data quality checks**: Automated validation rules and anomaly detection
- **AI agent integration**: LLM-powered data analysis and recommendations
- **Performance dashboard**: Real-time metrics and health monitoring
- **Audit logging**: Track all admin actions and changes
- **Bulk operations**: Import/export multiple configs at once
- **Configuration templates**: Reusable config templates for common patterns
- **Data lineage**: Visual graph of data flow and dependencies

### Architecture Overview

**Directory Structure:**
```
/opt/tangerine/
├── admin/                          # Streamlit admin interface
│   ├── app.py                      # Main entry point (landing page)
│   ├── pages/                      # Multi-page app (auto-discovered)
│   │   ├── 1_Import_Configs.py     # Import config CRUD
│   │   ├── 2_Reference_Data.py     # Manage datasource/datasettype
│   │   ├── 3_Run_Jobs.py           # Execute generic_import.py
│   │   └── 4_Monitoring.py         # View logs, datasets, and statistics
│   ├── components/                 # Reusable UI components
│   │   ├── forms.py                # Form builders with validation
│   │   ├── tables.py               # Data display tables
│   │   ├── validators.py           # Input validation
│   │   └── notifications.py        # Success/error messages
│   ├── services/                   # Business logic layer
│   │   ├── import_config_service.py    # Config CRUD operations
│   │   ├── reference_data_service.py   # Reference data operations
│   │   ├── job_execution_service.py    # Job execution logic
│   │   └── monitoring_service.py       # Logs, datasets, and statistics queries
│   ├── utils/                      # Admin utilities
│   │   ├── db_helpers.py           # Database query wrappers
│   │   ├── formatters.py           # Display formatting
│   │   └── ui_helpers.py           # UI helper functions (loading, error handling, etc.)
│   └── styles/                     # CSS styling
│       └── custom.css              # Professional Tangerine theme
├── tests/                          # Admin test suite
│   ├── conftest.py                 # Test fixtures and config
│   ├── pytest.ini                  # Pytest configuration
│   ├── unit/                       # Unit tests (validators, utils)
│   ├── integration/                # Integration tests (services)
│   └── fixtures/                   # Reusable test data
├── Dockerfile.streamlit            # Admin container build
└── requirements/
    └── admin.txt                   # Streamlit dependencies
```

**Design Pattern:** Vertical Slice Architecture with service layer
- `pages/`: One page per feature (Streamlit auto-discovers files)
- `components/`: Reusable UI elements (DRY principle)
- `services/`: Database operations and business logic (testable, reusable)
- `utils/`: Helper functions for formatting and validation

**Docker Services:**
- **db**: PostgreSQL 18 database
- **tangerine**: ETL job execution container
- **admin**: Streamlit web interface (port 8501)

All services communicate via the `tangerine_network` bridge network.

### Database Integration

The admin interface reuses existing database utilities:
- **Connection Pooling**: Uses `common/db_utils.py` connection pool (max 10 connections)
- **Stored Procedures**: Calls `dba.pimportconfigi` and `dba.pimportconfigu` for config management
- **Parameterized Queries**: All queries use parameterized statements (SQL injection protection)
- **Transaction Management**: Uses `db_transaction()` context manager for atomicity

**Tables Used:**
- `dba.timportconfig`: Import configurations (CRUD operations)
- `dba.tdatasource`: Data source reference (dropdown population)
- `dba.tdatasettype`: Dataset type reference (dropdown population)
- `dba.timportstrategy`: Import strategies (read-only, 3 predefined)
- `dba.tlogentry`: ETL process logs (monitoring)
- `dba.tdataset`: Dataset records (monitoring)

**No Schema Changes Required** - All functionality uses existing tables and procedures.

### Critical Implementation Details

#### Metadata Extraction Configuration
Import configurations support three metadata extraction modes:

1. **filename**: Extract from filename using delimiter and position index
   - Example: `20260105T150000_ProductData.csv` with delimiter `_` and position `1` extracts `ProductData`

2. **file_content**: Extract from specified column in first data record
   - Example: Column name `category` extracts value from that column

3. **static**: Use fixed value for all records in the dataset
   - Example: Static value `Q1_Sales` used for entire import

The form dynamically shows different input fields based on the selected mode.

#### Date Extraction Configuration
Similar to metadata extraction, supports three modes:

1. **filename**: Parse date from filename using delimiter, position index, and date format
   - Example: `20260105T150000_Data.csv` with position `0` and format `yyyyMMddTHHmmss`

2. **file_content**: Extract date from specified column in data
   - Example: Column name `transaction_date`

3. **static**: Use fixed date value
   - Example: Static value `2026-01-01`

#### Import Strategies
Three strategies control how column mismatches are handled:

| ID | Strategy | Behavior |
|----|----------|----------|
| 1 | Import and create new columns if needed | Uses `ALTER TABLE` to add new columns from source file |
| 2 | Import only (ignores new columns) | Silently ignores columns not in target table |
| 3 | Import or fail if columns missing | Raises error if source has columns not in target table |

#### SQL LIKE Pattern Escaping (CRITICAL)
When using LIKE patterns in psycopg2 queries, percent signs must be doubled to avoid being interpreted as parameter placeholders:

```python
# WRONG - causes "tuple index out of range" error
query = "SELECT * FROM table WHERE message LIKE '%ERROR%'"

# CORRECT - double all percent signs
query = "SELECT * FROM table WHERE message LIKE '%%ERROR%%'"
```

**Files affected by this issue:**
- `admin/services/job_execution_service.py` (job history query)
- Any future queries using LIKE patterns

#### Streamlit Form Key Uniqueness
Streamlit requires unique form keys even across tabs in the same page:

```python
# WRONG - conflicts if multiple forms exist
with st.form(key="import_config_form"):

# CORRECT - unique per context
form_key = "import_config_form_edit" if is_edit else "import_config_form_create"
with st.form(key=form_key):
```

**Files using this pattern:**
- `admin/components/forms.py` (all form builders)
- `admin/pages/1_Import_Configs.py` (edit vs create forms)
- `admin/pages/2_Reference_Data.py` (edit vs create forms)

#### Session State for Success Messages
Success messages must be stored in session state to persist across `st.rerun()`:

```python
# In the form submission handler
if update_config(config_id, form_data):
    # Store message in session state BEFORE rerun
    st.session_state.update_success_message = "✅ Configuration updated successfully!"
    st.rerun()

# At the top of the page (before form)
if 'update_success_message' in st.session_state:
    show_success(st.session_state.update_success_message)
    st.balloons()
    # Clean up after display
    del st.session_state.update_success_message
```

**Files using this pattern:**
- `admin/pages/1_Import_Configs.py` (update/delete messages)
- `admin/pages/2_Reference_Data.py` (all CRUD messages)

#### Real-time Job Execution
Jobs are executed using subprocess with real-time output streaming:

```python
def execute_import_job(config_id, run_date=None, dry_run=False, timeout=300):
    cmd = [
        "docker", "compose", "exec", "-T", "tangerine",
        "python", "etl/jobs/generic_import.py",
        "--config-id", str(config_id)
    ]

    if run_date:
        cmd.extend(["--date", run_date.strftime("%Y-%m-%d")])

    if dry_run:
        cmd.append("--dry-run")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Yield output line by line
    for line in process.stdout:
        yield line.rstrip('\n')

    process.wait(timeout=timeout)
```

**Key features:**
- `-T` flag prevents pseudo-TTY allocation (required for subprocess)
- `bufsize=1` enables line-buffering for real-time output
- Generator pattern allows streaming to UI without blocking
- Timeout protection prevents hung jobs

### Common Admin Workflows

#### Creating a New Import Configuration

1. Navigate to **Import Configs** → **Create New**
2. Fill in all required fields:
   - **Config Name**: Unique identifier (e.g., `DailySalesImport`)
   - **Data Source**: Select from dropdown or create new in Reference Data
   - **Dataset Type**: Select from dropdown or create new in Reference Data
   - **Source Directory**: `/app/data/source` (mounted from `./.data/etl/source/`)
   - **Archive Directory**: `/app/data/archive` (mounted from `./.data/etl/archive/`)
   - **File Pattern**: Regex pattern (e.g., `.*Sales.*\.csv`)
   - **File Type**: CSV, XLS, XLSX, JSON, or XML
   - **Metadata Label Source**: Choose filename/file_content/static
     - For filename: Specify delimiter and position index
     - For file_content: Specify column name
     - For static: Enter fixed value
   - **Date Source**: Choose filename/file_content/static (same options as metadata)
   - **Date Format**: For filename parsing (e.g., `yyyyMMddTHHmmss`)
   - **Filename Delimiter**: Character to split filename (e.g., `_`)
   - **Target Table**: Schema.table format (e.g., `feeds.sales_data`)
   - **Import Strategy**: Select 1, 2, or 3 based on column handling needs
   - **Is Active**: Check to enable for execution
3. Click **Create Configuration**
4. Success message displays with balloons animation
5. Config appears in View All Configs tab

#### Running an Import Job

1. Navigate to **Run Jobs** → **Execute Job**
2. Select import configuration from dropdown
3. Review configuration details in expander
4. Set execution parameters:
   - **Run Date**: Default is today, or select specific date
   - **Dry Run Mode**: Check for validation without database writes
5. Click **▶️ Run Import Job**
6. Watch real-time output stream in code block
7. Job completes with success (✅) or failure (❌) indicator
8. View full output in expander if needed
9. Check **Job History** tab to see completed run

#### Viewing Job History

1. Navigate to **Run Jobs** → **Job History**
2. Select number of recent runs to display (10/25/50/100)
3. Review table with run_uuid, process, start time, steps, status, runtime
4. Copy run_uuid for detailed output lookup
5. Enter run_uuid in "Enter Run UUID" field
6. Click **📄 Load Output**
7. View formatted log entries with step counters and runtimes

### Security Considerations

**Current Design (Phases 1-5):**
- No authentication/authorization implemented
- Relies on network-level security (firewall, VPN, local subnet)
- Suitable for small teams on private networks
- All admin operations logged via `dba.tlogentry`

**SQL Injection Protection:**
- All queries use parameterized statements
- Never use string concatenation for dynamic SQL
- Form validation prevents malicious input
- Regex patterns validated before database insert

**Future Security Enhancements (Optional):**
1. Basic Auth via nginx reverse proxy
2. VPN-only access (bind to localhost, expose via VPN tunnel)
3. Streamlit custom authentication with session state
4. Role-based access control (admin vs viewer roles)
5. Audit logging for all admin actions

### Adding New Admin Features

The architecture supports easy addition of new features:

1. **Create new page file:** `admin/pages/5_New_Feature.py`
2. **Create service:** `admin/services/new_feature_service.py`
3. **Reuse components:** Import from `components/forms.py`, `components/tables.py`, etc.
4. **Add database table:** `schema/dba/tables/tnewfeature.sql` (if needed)
5. **Streamlit auto-discovers** new page and adds to sidebar navigation

**Example: Adding a Cron Scheduler**
```python
# admin/pages/5_Cron_Scheduler.py
import streamlit as st
from services.scheduler_service import create_schedule, list_schedules
from components.forms import render_cron_form
from components.tables import render_schedule_table

st.title("⏰ Cron Scheduler")

# Create schedule form
schedule_data = render_cron_form()
if st.button("Create Schedule"):
    create_schedule(schedule_data)
    st.success("Schedule created!")

# Display existing schedules
schedules = list_schedules()
render_schedule_table(schedules)
```

### Troubleshooting Admin Interface

**Admin service won't start:**
```bash
# Check admin service logs
docker compose logs admin

# Common issues:
# 1. Port 8501 already in use
#    Solution: Stop other services using port 8501 or change port in docker-compose.yml
# 2. Database not healthy
#    Solution: Wait for db service to pass healthcheck (check with: docker compose ps)
# 3. Missing dependencies
#    Solution: Rebuild with docker compose up --build
```

**Cannot access from another machine:**
```bash
# Check firewall rules (Ubuntu server)
sudo ufw status

# Allow port 8501 from local network
sudo ufw allow from 192.168.1.0/24 to any port 8501
sudo ufw reload

# Check admin service is listening on 0.0.0.0
docker compose logs admin | grep "URL:"
# Should show: URL: http://0.0.0.0:8501
```

**Database connection shows "Disconnected":**
```bash
# Test database connection from admin container
docker compose exec admin python -c "from common.db_utils import test_connection; print(test_connection())"

# Check DB_URL environment variable
docker compose exec admin env | grep DB_URL

# Verify DB_URL matches format: postgresql://user:password@db:5432/tangerine_db
```

**Streamlit showing errors:**
```bash
# Restart admin service
docker compose restart admin

# View detailed error logs
docker compose logs -f admin

# Check Python dependencies installed correctly
docker compose exec admin pip list | grep streamlit
```

**Form validation errors:**
- **Path validation**: Ensure directories exist in container (`/app/data/source/`, `/app/data/archive/`)
- **Regex validation**: Test patterns at regex101.com before entering
- **Table validation**: Verify target table exists in feeds schema
- **Duplicate names**: Check View All tabs for existing names

**Job execution timeout:**
```bash
# Default timeout is 5 minutes (300 seconds)
# To increase, edit admin/services/job_execution_service.py:
# Change timeout parameter in execute_import_job() function

# For very large imports, run from command line instead:
docker compose exec tangerine python etl/jobs/generic_import.py --config-id <id>
```

**Success messages not showing:**
- Ensure session state is being used correctly
- Check browser console for JavaScript errors
- Try refreshing the page manually

### Development Workflow

**Testing Changes Locally:**
```bash
# Make changes to admin/*.py files
# Streamlit auto-reloads on file changes (development mode)

# If you modify requirements/admin.txt or Dockerfile.streamlit:
docker compose down
docker compose up --build admin

# View real-time logs during development
docker compose logs -f admin
```

**Deploying to Server:**
```bash
# On local machine
git add admin/ Dockerfile.streamlit docker-compose.yml requirements/admin.txt
git commit -m "Update admin interface"
git push origin main

# On Ubuntu server
ssh user@server-ip
cd /opt/tangerine
git pull
docker compose down
docker compose up --build -d

# Verify services
docker compose ps
docker compose logs -f admin

# Access from browser: http://<server-ip>:8501
```

### Known Issues and Fixes

#### Issue 1: Import Error - render_dataframe_table
**Error:** `ImportError: cannot import name 'render_dataframe_table' from 'components.tables'`

**Cause:** Function didn't exist in components/tables.py

**Fix:** Removed unused import - page already had its own table rendering logic

#### Issue 2: Import Error - format_timestamp and truncate_text
**Error:** `ImportError: cannot import name 'format_timestamp' from 'utils.formatters'`

**Cause:** Functions were named `format_datetime` and `truncate_string`

**Fix:** Added aliases in `utils/formatters.py`:
```python
# Aliases for convenience
format_timestamp = format_datetime
truncate_text = truncate_string
```

#### Issue 3: Duplicate Form Keys
**Error:** "There are multiple identical forms with key='import_config_form'"

**Cause:** Same form key used in both Create and Edit tabs

**Fix:** Dynamic form keys based on context:
```python
form_key = "import_config_form_edit" if is_edit else "import_config_form_create"
```

#### Issue 4: Config Name Not Editable
**Issue:** Configuration name field was disabled during edit

**Fix:** Removed `disabled=is_edit` restriction and added duplicate checking with `exclude_id` parameter:
```python
def config_name_exists(config_name: str, exclude_id: Optional[int] = None) -> bool:
    query = "SELECT COUNT(*) FROM dba.timportconfig WHERE config_name = %s"
    params = [config_name]
    if exclude_id is not None:
        query += " AND config_id != %s"
        params.append(exclude_id)
    # ...
```

#### Issue 5: Success Messages Disappearing
**Issue:** Messages disappeared before user could see them due to fast `st.rerun()`

**Fix:** Store messages in session state before rerun:
```python
# Store message
st.session_state.update_success_message = "✅ Configuration updated!"
st.rerun()

# Display after rerun
if 'update_success_message' in st.session_state:
    show_success(st.session_state.update_success_message)
    del st.session_state.update_success_message
```

#### Issue 6: Job History "Tuple Index Out of Range"
**Error:** `IndexError: tuple index out of range` when loading job history

**Cause:** psycopg2 interpreting `%ERROR%` in LIKE patterns as parameter placeholders

**Fix:** Escape all percent signs in LIKE patterns:
```python
# Before
query = "... WHERE message LIKE '%ERROR%'"

# After
query = "... WHERE message LIKE '%%ERROR%%'"
```

Also fixed:
- Used `timestamp` column instead of non-existent `starttime`
- Changed `MAX(stepcounter)` to `COUNT(*)` for total_steps
- Added `COALESCE(SUM(stepruntime), 0)` for NULL-safe runtime aggregation

### Performance Considerations

**Connection Pooling:**
- Admin service shares connection pool with ETL jobs
- Max 10 connections configured in `common/db_utils.py`
- Connections automatically returned via `db_transaction()` context manager
- Monitor pool usage: If exhausted, increase `pool_size` in `common/config.py`

**Query Optimization:**
- All list queries use `ORDER BY` and `LIMIT` to prevent large result sets
- Indexes exist on frequently queried columns (config_id, run_uuid, etc.)
- Use pagination for large tables (implemented in job history)

**Streamlit Caching:**
- Consider adding `@st.cache_data` for expensive queries
- Currently not used to ensure real-time data freshness
- Add caching if performance degrades with large datasets

**Job Execution:**
- Subprocess timeout prevents hung processes
- Output streaming prevents memory overflow from large logs
- Last 50 lines displayed, full output in expander

## Email Services Architecture

Tangerine includes Gmail integration for automated email processing and report generation.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SERVER (Ubuntu)                          │
│                                                                  │
│  ┌─────────────────────┐     ┌─────────────────────────────┐   │
│  │  /opt/tangerine/    │     │     Docker Containers        │   │
│  │                     │     │                               │   │
│  │  secrets/           │     │  ┌─────────────────────────┐ │   │
│  │  ├─ credentials.json│────▶│  │  tangerine (ETL)        │ │   │
│  │  └─ token.json      │     │  │  - gmail_client.py      │ │   │
│  │                     │     │  │  - inbox_processor.py   │ │   │
│  │                     │     │  │  - report_generator.py  │ │   │
│  └─────────────────────┘     │  └─────────────────────────┘ │   │
│                              │                               │   │
│                              │  ┌─────────────────────────┐ │   │
│                              │  │  admin (Streamlit UI)   │ │   │
│                              │  │  - Inbox Configs page   │ │   │
│                              │  │  - Report Manager page  │ │   │
│                              │  │  - Scheduler page       │ │   │
│                              │  └─────────────────────────┘ │   │
│                              │                               │   │
│                              │  ┌─────────────────────────┐ │   │
│                              │  │  db (PostgreSQL)        │ │   │
│                              │  │  - tinboxconfig         │ │   │
│                              │  │  - treportmanager       │ │   │
│                              │  │  - tscheduler           │ │   │
│                              │  └─────────────────────────┘ │   │
│                              └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │  Gmail API    │
                            │  (Google)     │
                            └───────────────┘
```

### Component Locations

| Component | Location | Purpose |
|-----------|----------|---------|
| `credentials.json` | Server (`/opt/tangerine/secrets/`) | OAuth app identity |
| `token.json` | Server (`/opt/tangerine/secrets/`) | Access token to Gmail |
| `gmail_client.py` | Docker container (`tangerine`) | Python wrapper for Gmail API |
| ETL jobs | Docker container (`tangerine`) | Run inbox processor & reports |
| Config tables | Docker container (`db`) | Store rules in PostgreSQL |
| Admin UI | Docker container (`admin`) | Manage configs via browser |

### How It Works

1. **Secrets stay on server** - mounted read-only into Docker via volume
2. **Code runs in Docker** - isolated, reproducible environment
3. **Database in Docker** - configs stored in PostgreSQL
4. **Cron on server or Docker** - triggers scheduled jobs

### Email Capabilities

- **Send emails**: Reports with HTML tables and file attachments (CSV/Excel)
- **Receive emails**: Download attachments based on configurable rules
- **Gmail labels**: Auto-apply labels to processed/error emails
- **OAuth2 authentication**: Secure token-based access with auto-refresh

### Gmail OAuth Setup

1. Create OAuth credentials in Google Cloud Console
2. Save `credentials.json` to `/opt/tangerine/secrets/`
3. Run token generation script (requires browser for initial auth)
4. Token auto-refreshes - one-time setup only

## Key Database Tables

**Configuration & Reference:**
- `dba.timportconfig` - Import job configurations (config_id, config_name, file_pattern, etc.)
- `dba.tdatasource` - Data source reference
- `dba.tdatasettype` - Dataset type reference
- `dba.timportstrategy` - Import strategies (3 predefined)

**Email Services:**
- `dba.tinboxconfig` - Gmail inbox processing rules (patterns, target directory, labels)
- `dba.treportmanager` - Report configurations (recipients, SQL templates, output format)
- `dba.tscheduler` - Cron job scheduler (job_type, cron fields, config references)

**Pub/Sub System:**
- `dba.tpubsub_events` - Event queue (event_type, event_source, event_data, status)
- `dba.tpubsub_subscribers` - Event subscribers (event_type, handler_type, handler_config)

**Tracking & Logging:**
- `dba.tdataset` - Dataset metadata (datasetid, label, status, dates)
- `dba.tlogentry` - ETL execution logs (run_uuid, message, stepruntime)

**Data Storage:**
- `feeds.*` - Target tables for imported data (must have datasetid FK)

## Code Style

Follow these conventions when writing or modifying code:

**SQL Objects:** Use type prefixes (`t` table, `p` procedure, `f` function, `v` view, `idx_` index, `fk_` foreign key)

**Python:**
- snake_case for functions/variables, PascalCase for classes
- Type hints on all function signatures
- Google-style docstrings
- f-strings for formatting
- Parameterized queries only (never f-strings with SQL)

**Linting:** Run `ruff check` before committing. Config in `ruff.toml`.

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

### Email Services
```bash
# Process Gmail inbox (download attachments)
docker compose exec tangerine python etl/jobs/run_gmail_inbox_processor.py --config-id 1

# Generate and send report
docker compose exec tangerine python etl/jobs/run_report_generator.py --report-id 1

# Preview report without sending (dry run)
docker compose exec tangerine python etl/jobs/run_report_generator.py --report-id 1 --dry-run

# Generate crontab from database
docker compose exec tangerine python etl/jobs/generate_crontab.py --preview
docker compose exec tangerine python etl/jobs/generate_crontab.py --apply
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
```

### Database Access
```bash
# Connect to database
docker compose exec db psql -U tangerine_admin -d tangerine_db

# Test connection from ETL container
docker compose exec tangerine python common/db_utils.py
```

## Troubleshooting
- **Command not found (exit 127)**: Check CMD in Dockerfile points to an existing script.
- **Auth errors with Git**: Ensure SSH keys are set up correctly.
- **DB connection issues**: Verify .env vars match and Postgres service is up.
- **Volume/data errors on upgrade**: Run `docker compose down --volumes` to reset.
- **Obsolete warnings in Compose**: Ensure 'version' is removed from yml.
- **No schema subdirs in Git**: Add placeholders and commit.
- **Gmail authentication errors**: Ensure `token.json` exists in secrets folder and hasn't expired.

## Important Notes

- **Never commit `.env` files** - contains secrets
- **Always use parameterized queries** - prevents SQL injection
- **Connection pooling** - max 10 connections, reuse via `db_transaction()`
- **All SQL is idempotent** - safe to re-run initialization
- **Volume mounts are bidirectional** - files sync both ways
- **Admin service auto-reloads** - edit files and refresh browser in dev mode

