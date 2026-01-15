# Architecture Overview Codemap

## Purpose

Tangerine is an AI-integrated ETL pipeline for importing, transforming, and managing data files. Built with Vertical Slice Architecture (VSA) where each feature is self-contained with its own UI, logic, and data access.

## Technology Stack

- **Database**: PostgreSQL 18
- **Backend**: Python 3.11
- **Admin UI**: Streamlit
- **Containerization**: Docker Compose
- **Development**: Windows with Docker Desktop
- **Deployment**: Ubuntu 24.04 LTS

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit Admin Interface                     │
│  (admin/pages/*.py)                                              │
│  - Import Configs, Reference Data, Run Jobs, Monitoring          │
│  - Inbox Configs, Report Manager, Scheduler, Event System        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                              │
│  (admin/services/*.py)                                          │
│  - Business logic, validation, database operations              │
│  - Uses db_transaction() for all DB operations                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Common Utilities                            │
│  (common/*.py)                                                   │
│  - db_utils.py: Connection pooling, transactions                │
│  - gmail_client.py: OAuth2 Gmail API wrapper                    │
│  - logging_utils.py: ETL logging to database                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                          │
│  - dba schema: Configuration, logging, events                   │
│  - feeds schema: Raw data storage                               │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: File Import

```
1. File arrives in /app/data/source/
2. Pub/Sub listener detects file → creates 'file_received' event
3. OR: User triggers import via Run Jobs page
4. GenericImportJob reads config from dba.timportconfig
5. Extractor parses file (CSV/XLS/XLSX/JSON/XML)
6. Transformer normalizes columns, applies strategy
7. Loader inserts into feeds.{target_table}
8. File archived to /app/data/archive/
9. Event emitted: 'import_complete'
```

## Data Flow: Email Processing

```
1. Gmail client authenticates via OAuth2
2. Inbox processor scans for unread emails matching rules
3. Attachments downloaded to /app/data/source/inbox/
4. Email marked as read, label applied
5. Event emitted: 'email_received'
6. Subscriber triggers linked import config (if configured)
```

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `admin/` | Streamlit web interface |
| `admin/services/` | Business logic layer |
| `admin/pages/` | UI pages (auto-discovered) |
| `admin/components/` | Reusable UI components |
| `common/` | Shared utilities |
| `etl/` | ETL jobs and framework |
| `etl/jobs/` | Runnable ETL jobs |
| `pubsub/` | Event system daemon |
| `schema/` | Database DDL |
| `tests/` | pytest test suite |

## Docker Services

| Service | Container | Purpose |
|---------|-----------|---------|
| db | postgres:18 | Database |
| tangerine | Dockerfile | ETL jobs |
| admin | Dockerfile.streamlit | Admin UI |
| pubsub | Dockerfile.pubsub | Event daemon |

## Key Patterns

1. **Vertical Slice**: Each page owns its UI, service, and data access
2. **Service Layer**: Services handle business logic, pages handle display
3. **Transaction Context**: All DB ops use `with db_transaction() as cursor:`
4. **Parameterized Queries**: Never use f-strings for SQL
5. **Event-Driven**: ETL jobs emit events to pub/sub queue

## Integration Points

- **Gmail API**: OAuth2 via common/gmail_client.py
- **Database**: Connection pool via common/db_utils.py
- **File System**: Volume mount .data/etl ↔ /app/data
- **Pub/Sub**: Event queue in dba.tpubsub_events
