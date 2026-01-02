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
Edit `Dockerfile` to add pip packages:
```dockerfile
RUN pip install --no-cache-dir psycopg2-binary <new-package>
```

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