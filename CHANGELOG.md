# Changelog

All notable changes to the Tangerine ETL project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Skills and hooks auto-activation system for Claude Code
- Dev docs system for preserving context across sessions
- Feature documentation workflow with `/doc-feature` command

### Changed
- Updated CLAUDE.md with skills, hooks, and documentation sections
- **Inbox Rules UX**: Added inline pattern examples, improved help text, and Quick Start guide for non-technical users
- **Imports UX**: Added file pattern and date format examples with Quick Start guide
- **Scheduler UX**: Added cron expression examples and Quick Start guide for common schedules
- **Reports UX**: Added SQL template syntax and recipient format examples with Quick Start guide
- **Admin Theme**: Improved inline code readability in both light and dark modes

---

## [1.0.0] - 2026-01-16

### Added

#### Infrastructure
- Docker containerization with db, tangerine, admin, and pubsub services
- PostgreSQL 18 database with `dba` and `feeds` schemas
- Connection pooling and transaction management
- Streamlit admin interface at port 8501

#### ETL Framework
- **Generic Import System**: Config-driven file imports supporting CSV, XLS, XLSX, JSON, XML
- **Import Strategies**: Auto-add columns, ignore extras, strict validation
- **Metadata Extraction**: From filename, file content, or static values
- **Date Parsing**: Configurable Java-style date formats
- **File Archiving**: Automatic post-import file movement
- **Dataset Tracking**: Every import creates a dataset record with run_uuid

#### Admin Interface
- **Import Configs**: Full CRUD for import job configurations
- **Reference Data**: Manage datasources and dataset types
- **Run Jobs**: Execute imports with real-time output streaming
- **Monitoring**: View logs, datasets, and statistics with charts
- **Inbox Configs**: Gmail inbox processing rule management
- **Report Manager**: SQL-based email report configuration
- **Scheduler**: Database-driven cron job management
- **Event System**: Pub/sub event queue and subscriber management

#### Email Services
- **Gmail Integration**: OAuth2-based Gmail API client
- **Inbox Processor**: Download email attachments based on pattern rules
- **Report Generator**: SQL query results as HTML emails with attachments

#### Pub/Sub System
- Event queue with database-backed persistence
- File watcher for event triggers
- Subscriber notification system
- ETL integration (import_complete, report_sent, email_received events)

#### Testing
- 310+ pytest-based tests for admin interface
- 121 ETL integration tests
- 17 ETL regression tests
- Transaction-based test isolation

#### Developer Experience
- Custom CSS theme (Tangerine orange)
- Codemaps for architecture documentation
- Slash commands for common operations
- Code style guide with ruff linting

### Database Tables

#### Configuration
- `dba.timportconfig` - Import job configurations
- `dba.tdatasource` - Data source reference
- `dba.tdatasettype` - Dataset type reference
- `dba.timportstrategy` - Import strategies

#### Email Services
- `dba.tinboxconfig` - Gmail inbox processing rules
- `dba.treportmanager` - Report configurations
- `dba.tscheduler` - Cron job definitions

#### Pub/Sub
- `dba.tpubsub_events` - Event queue
- `dba.tpubsub_subscribers` - Event subscribers

#### Tracking
- `dba.tdataset` - Dataset metadata
- `dba.tlogentry` - ETL execution logs

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| 1.0.0 | 2026-01-16 | Initial release with full ETL pipeline |

---

## How to Update This File

When making changes:

1. Add entries under `[Unreleased]` section
2. Use these categories:
   - **Added** - New features
   - **Changed** - Changes to existing functionality
   - **Deprecated** - Features to be removed
   - **Removed** - Removed features
   - **Fixed** - Bug fixes
   - **Security** - Security fixes

3. Format entries as:
   ```markdown
   - **Feature Name**: Brief description of the change
   ```

4. When releasing, move `[Unreleased]` items to a new version section
