# Tangerine ETL - Project Status

> Last Updated: January 14, 2026

## Overview

Tangerine is an AI-integrated ETL pipeline with a Streamlit admin interface. This document tracks what has been completed and what is planned for future development.

---

## Completed Features

### Phase 1: Infrastructure
- [x] Docker containerization (db, tangerine, admin services)
- [x] PostgreSQL database with `dba` and `feeds` schemas
- [x] Connection pooling and transaction management
- [x] Streamlit admin landing page with dashboard

### Phase 2: Core Framework
- [x] Notification system (success/error/warning/info)
- [x] Validators (8 validation functions)
- [x] Database helpers (count, exists, distinct values)
- [x] Formatters (10 display utilities)
- [x] Enhanced dashboard with metrics

### Phase 3: Import Configuration Management
- [x] Full CRUD interface for `dba.timportconfig`
- [x] Form with all 19 configuration fields
- [x] Dynamic fields based on metadata/date source selection
- [x] Real-time validation (paths, regex, table names)
- [x] Duplicate name checking

### Phase 4: Reference Data Management
- [x] CRUD for datasources (`dba.tdatasource`)
- [x] CRUD for dataset types (`dba.tdatasettype`)
- [x] Read-only view of import strategies
- [x] Delete protection for referenced records

### Phase 5: Job Execution
- [x] Select and execute import jobs from UI
- [x] Real-time output streaming
- [x] Dry-run mode (validation without database writes)
- [x] 5-minute timeout protection
- [x] Job history viewer with filtering

### Phase 6: System Monitoring
- [x] **Logs Tab**: View/filter ETL logs with time range filters
- [x] **Datasets Tab**: Browse dataset records with filtering
- [x] **Statistics Tab**: Metrics cards, charts, and runtime stats

### Phase 7: Polish & Production Ready
- [x] Custom CSS styling with Tangerine theme
- [x] Enhanced UI components (cards, tables, buttons)
- [x] Loading spinners and progress indicators
- [x] Responsive design for mobile/tablet

### Phase 8: Email Services
- [x] **Gmail Integration**: OAuth2-based Gmail API client
  - Send emails with HTML body and attachments
  - Read inbox and download attachments
  - Apply/remove Gmail labels
  - Token auto-refresh
- [x] **Inbox Processor** (`5_Inbox_Configs.py`)
  - Subject/sender/attachment pattern matching
  - Date-prefixed filenames
  - Optional .eml file export
  - Link to import configs for auto-processing
- [x] **Report Generator** (`6_Report_Manager.py`)
  - `{{SQL:query}}` template syntax
  - HTML tables inline + CSV/Excel attachments
  - Multiple output formats (html, csv, excel, html_csv, html_excel)
- [x] **Scheduler** (`7_Scheduler.py`)
  - Configure jobs via admin UI
  - Generate crontab from database
  - Support for inbox, report, import, and custom job types

### Phase 9: Pub/Sub Event System (NEW - January 2026)
- [x] **Database Schema**
  - `dba.tpubsub_events` - Event queue table
  - `dba.tpubsub_subscribers` - Subscriber configuration table
  - `ppubsub_iu` - Stored procedure for upserts
- [x] **Python Daemon** (`pubsub/listener.py`)
  - File watcher for event triggers
  - Database poller for queued events
  - Subscriber notification system
- [x] **Admin UI** (`8_Event_System.py`)
  - Event Queue tab - View pending/processed events
  - Subscribers tab - CRUD for event subscribers
  - Event Log tab - Historical event tracking
  - Service Status tab - Monitor pubsub daemon
- [x] **Service Layer** (`pubsub_service.py`)
  - Full CRUD for events and subscribers
  - Event filtering by type, source, status
  - Subscriber management with webhook/email/script handlers
- [x] **ETL Integration**
  - `generic_import.py` emits `import_complete` event
  - `run_report_generator.py` emits `report_sent` event
  - `run_gmail_inbox_processor.py` emits `email_received` event
- [x] **Docker Integration**
  - `Dockerfile.pubsub` for listener container
  - docker-compose.yml updated with pubsub service

### Testing Infrastructure
- [x] **ETL Regression Tests**: 17 tests (100% pass rate)
- [x] **Admin Tests**: 310 pytest-based tests
  - Unit tests for validators and pattern matching
  - Integration tests for all services:
    - `test_import_config_service.py` - Import config CRUD
    - `test_reference_data_service.py` - Datasource/type management
    - `test_monitoring_service.py` - Logs, datasets, statistics
    - `test_inbox_config_service.py` - Inbox config CRUD
    - `test_scheduler_service.py` - Scheduler CRUD, cron helpers
    - `test_report_manager_service.py` - Report config CRUD
    - `test_pubsub_service.py` - Event system (44+ tests)
  - Transaction-based test isolation with automatic rollback

---

## Database Tables

### Configuration & Reference
| Table | Description |
|-------|-------------|
| `dba.timportconfig` | Import job configurations |
| `dba.tdatasource` | Data source reference |
| `dba.tdatasettype` | Dataset type reference |
| `dba.timportstrategy` | Import strategies (3 predefined) |

### Email Services
| Table | Description |
|-------|-------------|
| `dba.tinboxconfig` | Gmail inbox processing rules |
| `dba.treportmanager` | Report configurations |
| `dba.tscheduler` | Cron job scheduler |

### Pub/Sub System
| Table | Description |
|-------|-------------|
| `dba.tpubsub_events` | Event queue (pending/processed) |
| `dba.tpubsub_subscribers` | Event subscribers (webhook/email/script) |

### Tracking & Logging
| Table | Description |
|-------|-------------|
| `dba.tdataset` | Dataset metadata |
| `dba.tlogentry` | ETL execution logs |

---

## Admin UI Pages

| Page | File | Description |
|------|------|-------------|
| Dashboard | `app.py` | System metrics and overview |
| Import Configs | `1_Import_Configs.py` | CRUD for import configurations |
| Reference Data | `2_Reference_Data.py` | Manage datasources and types |
| Run Jobs | `3_Run_Jobs.py` | Execute imports, view history |
| Monitoring | `4_Monitoring.py` | Logs, datasets, statistics |
| Inbox Configs | `5_Inbox_Configs.py` | Gmail inbox processing rules |
| Report Manager | `6_Report_Manager.py` | Email report configuration |
| Scheduler | `7_Scheduler.py` | Cron job management |
| Event System | `8_Event_System.py` | Pub/sub event monitoring |

---

## Planned Features

### Near-Term (Next Sprint)

#### Event-Driven Automation
- [ ] Auto-trigger import jobs when `email_received` event fires
- [ ] Chain events: `email_received` → `import_complete` → `report_sent`
- [ ] Retry logic for failed event handlers
- [ ] Event-based alerts for job failures

#### Enhanced Monitoring
- [ ] Real-time job status dashboard
- [ ] Email/Slack notifications for job failures
- [ ] Performance metrics and trending
- [ ] Resource utilization monitoring

### Medium-Term

#### Data Quality & Validation
- [ ] Automated data quality checks
- [ ] Anomaly detection with configurable thresholds
- [ ] Data profiling and statistics
- [ ] Validation rule builder in UI

#### Authentication & Security
- [ ] User authentication (OAuth or session-based)
- [ ] Role-based access control (RBAC)
- [ ] Audit logging for all admin actions
- [ ] API key management for external integrations

#### Bulk Operations
- [ ] Import/export configurations as JSON/YAML
- [ ] Bulk enable/disable jobs
- [ ] Configuration templates for common patterns
- [ ] Clone/duplicate configurations

### Long-Term

#### AI Integration
- [ ] LLM-powered data analysis and recommendations
- [ ] Natural language query interface
- [ ] Automated configuration suggestions
- [ ] Intelligent error diagnosis and fixes

#### Advanced Features
- [ ] Data lineage visualization
- [ ] Dependency graph for jobs
- [ ] Version control for configurations
- [ ] Multi-environment support (dev/staging/prod)
- [ ] API endpoints for external integration

---

## Recent Changes

### January 14, 2026

**Pub/Sub System Implementation**
- Added complete pub/sub event system with database tables, Python daemon, and admin UI
- Integrated event emission into all ETL jobs (import, report, inbox processor)
- Created comprehensive test suite (44+ tests for pubsub_service)

**Test Infrastructure Fixes**
- Fixed schema mismatch in test fixtures (VARCHAR columns vs FK IDs)
- Added missing `datasetdate` column to dataset fixtures
- Renamed `test_*` pattern-checking functions to `validate_*` to prevent pytest collection
- Fixed foreign key constraint ordering in cleanup fixtures
- Added 65+ new tests for scheduler and report manager services

**Files Added**
- `Dockerfile.pubsub` - Pubsub listener container
- `admin/pages/8_Event_System.py` - Event system admin UI
- `admin/services/pubsub_service.py` - Pubsub service layer
- `pubsub/listener.py` - Event listener daemon
- `schema/dba/tables/tpubsub_events.sql` - Events table
- `schema/dba/tables/tpubsub_subscribers.sql` - Subscribers table
- `schema/dba/procedures/ppubsub_iu.sql` - Upsert procedure
- `tests/integration/services/test_pubsub_service.py`
- `tests/integration/services/test_scheduler_service.py`
- `tests/integration/services/test_report_manager_service.py`
- `tests/integration/services/test_inbox_config_service.py`
- `tests/unit/test_pattern_validators.py`

**Files Modified**
- `etl/jobs/generic_import.py` - Added `import_complete` event emission
- `etl/jobs/run_report_generator.py` - Added `report_sent` event emission
- `etl/jobs/run_gmail_inbox_processor.py` - Added `email_received` event emission
- `admin/services/inbox_config_service.py` - Renamed test functions to validate
- `tests/conftest.py` - Fixed fixture column names
- `tests/fixtures/database_fixtures.py` - Added datasetdate column
- `tests/fixtures/import_config_fixtures.py` - Updated column names
- `docker-compose.yml` - Added pubsub service
- `schema/init.sh` - Added pubsub table initialization

---

## Running Tests

```bash
# Run all tests
docker compose exec tangerine pytest tests/ -v

# Run unit tests only (fast, no database)
docker compose exec tangerine pytest tests/unit/ -v -m unit

# Run integration tests only
docker compose exec tangerine pytest tests/integration/ -v -m integration

# Run specific service tests
docker compose exec tangerine pytest tests/integration/services/test_pubsub_service.py -v

# Run with coverage
docker compose exec tangerine pytest tests/ --cov=admin --cov-report=html
```

---

## Quick Start

```bash
# Start all services
docker compose up --build -d

# Access admin UI
open http://localhost:8501

# Check logs
docker compose logs -f admin
docker compose logs -f pubsub

# Run an import job
docker compose exec tangerine python etl/jobs/generic_import.py --config-id 1

# Process Gmail inbox
docker compose exec tangerine python etl/jobs/run_gmail_inbox_processor.py

# Generate and send a report
docker compose exec tangerine python etl/jobs/run_report_generator.py --report-id 1
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TANGERINE ETL                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   Gmail     │───▶│   Inbox     │───▶│   Import    │                 │
│  │   Inbox     │    │  Processor  │    │    Job      │                 │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘                 │
│                            │                   │                        │
│                            ▼                   ▼                        │
│                    ┌───────────────────────────────────┐               │
│                    │         PUBSUB EVENT QUEUE        │               │
│                    │  (email_received, import_complete) │               │
│                    └───────────────────────────────────┘               │
│                            │                   │                        │
│                            ▼                   ▼                        │
│                    ┌─────────────┐    ┌─────────────┐                  │
│                    │  Pubsub     │    │   Report    │                  │
│                    │  Listener   │    │  Generator  │                  │
│                    └─────────────┘    └──────┬──────┘                  │
│                                              │                          │
│                                              ▼                          │
│                                      ┌─────────────┐                   │
│                                      │   Gmail     │                   │
│                                      │   Send      │                   │
│                                      └─────────────┘                   │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         ADMIN UI (Streamlit)                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ Import  │ │Reference│ │  Run    │ │ Monitor │ │  Inbox  │          │
│  │ Configs │ │  Data   │ │  Jobs   │ │  Logs   │ │ Configs │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                                   │
│  │ Report  │ │Scheduler│ │ Event   │                                   │
│  │ Manager │ │         │ │ System  │                                   │
│  └─────────┘ └─────────┘ └─────────┘                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                         PostgreSQL Database                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐             │
│  │      dba schema         │  │     feeds schema        │             │
│  │  - timportconfig        │  │  - (target tables)      │             │
│  │  - tdataset             │  │                         │             │
│  │  - tlogentry            │  │                         │             │
│  │  - tinboxconfig         │  │                         │             │
│  │  - treportmanager       │  │                         │             │
│  │  - tscheduler           │  │                         │             │
│  │  - tpubsub_events       │  │                         │             │
│  │  - tpubsub_subscribers  │  │                         │             │
│  └─────────────────────────┘  └─────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
```
