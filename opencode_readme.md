## Tangerine Codebase Summary

**Project Overview**: Tangerine is an AI-integrated ETL pipeline using Vertical Slice Architecture for modularity. It imports data from CSV/XLS/XLSX/JSON/XML files into PostgreSQL, with Streamlit admin interface, Gmail integration, and pub-sub event system.

**Key Technologies**:
- **Backend**: Python 3.11, PostgreSQL 18, Docker
- **Frontend**: Streamlit 1.39.0 with custom theming
- **Email**: Google API Python client with OAuth2
- **Testing**: pytest (310+ tests, 100% pass rate)

**Architecture**:
- **Vertical Slice**: Each feature self-contained (UI → Service → Data → Tests)
- **ETL Pipeline**: 5-phase process (Setup/Extract/Transform/Load/Cleanup)
- **Service Layer**: Standardized CRUD operations with transaction management
- **Event-Driven**: Pub-sub system for reactive workflows

**Main Components**:
- **admin/**: Streamlit UI with 8 pages (configs, jobs, monitoring, email services)
- **etl/**: Config-driven import jobs with multiple extractors and strategies
- **common/**: Shared utilities (DB pooling, logging, Gmail client)
- **schema/**: PostgreSQL schemas (dba for config, feeds for data)
- **tests/**: Comprehensive unit/integration testing
- **pubsub/**: Event system with watchers and handlers

**Database Schema**:
- **dba**: Pipeline config (timportconfig, tdataset, tlogentry, etc.)
- **feeds**: Dynamic business data tables linked to datasets

**ETL Features**:
- Multi-format support with specialized extractors
- Configurable metadata/date extraction (filename/content/static)
- Import strategies (add columns/ignore new/fail on mismatch)
- Audit logging with run_uuid tracking

**Admin Interface**:
- Full CRUD for configurations and reference data
- Real-time job execution with streaming output
- Monitoring dashboard with logs/datasets/statistics
- Email services management (inbox processing, reports, scheduling)

**Deployment**:
- Docker Compose with 4 services (db, tangerine, admin, pubsub)
- Volume mounts for bidirectional file sync
- Production-ready on Ubuntu with SSH/Git workflow

**Notable Patterns**:
- Type hints and Pydantic validation
- Context managers for resources
- Parameterized queries for security
- Session state management in Streamlit
- Comprehensive error handling and logging

The codebase is production-ready with excellent testing coverage, documentation, and scalable architecture supporting both traditional ETL and AI agent integration. No further exploration needed - this covers the complete project structure and functionality.