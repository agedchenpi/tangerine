# Plan: Update README.md with Diagrams and Docker Commands

## Task
Enhance README.md with:
1. Visual diagrams of Streamlit page architecture
2. Docker volume and image management commands
3. Better organized command reference section

---

## Changes to Make

### 1. Add Streamlit Architecture Diagram (New Section)

Insert after "Architecture Overview" section with ASCII diagrams showing:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      STREAMLIT ADMIN ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         app.py (Entry Point)                      │   │
│  │                    st.navigation() + Sidebar Menu                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│         ┌──────────────────────────┼──────────────────────────┐         │
│         ▼                          ▼                          ▼         │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐   │
│  │ CONFIGURATION│           │ OPERATIONS  │           │   SYSTEM    │   │
│  ├─────────────┤           ├─────────────┤           ├─────────────┤   │
│  │ imports.py  │           │ run_jobs.py │           │event_system │   │
│  │ inbox_rules │           │ monitoring  │           │    .py      │   │
│  │ reference_  │           │ reports.py  │           └─────────────┘   │
│  │   data.py   │           └─────────────┘                              │
│  │ scheduler   │                                                        │
│  └─────────────┘                                                        │
│         │                          │                          │         │
│         └──────────────────────────┼──────────────────────────┘         │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      SERVICE LAYER (admin/services/)              │   │
│  │  import_config_service │ job_execution_service │ pubsub_service  │   │
│  │  inbox_config_service  │ monitoring_service    │ scheduler_service│  │
│  │  reference_data_service│ report_manager_service│                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    COMPONENTS (admin/components/)                 │   │
│  │  notifications.py │ forms.py │ validators.py │ dependency_checker│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      common/db_utils.py                           │   │
│  │                   Connection Pool + db_transaction()              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│                            ┌─────────────┐                              │
│                            │ PostgreSQL  │                              │
│                            │    (db)     │                              │
│                            └─────────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Add Page Dependency Diagram

Show how pages depend on each other and reference data:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PAGE DEPENDENCY GRAPH                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐                                                    │
│  │ Reference Data  │ ◄─── Master data (must exist first)                │
│  │ (datasources,   │                                                    │
│  │  datasettypes,  │                                                    │
│  │  strategies)    │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                              │
│           ├────────────────┬────────────────┬────────────────┐          │
│           ▼                ▼                ▼                ▼          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  ┌──────────┐     │
│  │   Imports   │   │ Inbox Rules │   │  Scheduler  │  │ Reports  │     │
│  │  (configs)  │   │  (patterns) │   │   (cron)    │  │(templates)│    │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘  └────┬─────┘     │
│         │                 │                 │               │           │
│         └────────┬────────┴────────┬────────┘               │           │
│                  ▼                 ▼                        ▼           │
│         ┌─────────────┐   ┌─────────────────┐      ┌─────────────┐     │
│         │  Run Jobs   │   │  Event System   │      │  Run Report │     │
│         │ (execution) │   │ (pub/sub queue) │      │   (send)    │     │
│         └──────┬──────┘   └────────┬────────┘      └──────┬──────┘     │
│                │                   │                      │             │
│                └───────────────────┼──────────────────────┘             │
│                                    ▼                                     │
│                           ┌─────────────┐                               │
│                           │ Monitoring  │                               │
│                           │(logs, stats)│                               │
│                           └─────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Add Docker Services & Volumes Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DOCKER SERVICES & VOLUMES                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  HOST MACHINE                          DOCKER CONTAINERS                 │
│  ─────────────                         ──────────────────                │
│                                                                          │
│  ./.data/etl/ ◄───────────────────────► /app/data (tangerine, admin)    │
│    ├── source/     (bidirectional)        ├── source/                   │
│    ├── archive/                           ├── archive/                  │
│    └── inbox/                             └── inbox/                    │
│                                                                          │
│  ./secrets/ ─────────────────────────► /app/secrets (read-only)         │
│    ├── credentials.json                                                  │
│    └── token.json                                                        │
│                                                                          │
│  ./schema/ ──────────────────────────► /app/schema (db init)            │
│                                                                          │
│  NAMED VOLUMES (Docker-managed):                                         │
│  ───────────────────────────────                                         │
│  db_data ◄───────────────────────────► /var/lib/postgresql (db)         │
│  etl_logs ◄──────────────────────────► /app/logs (tangerine, admin)     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4. Add Docker Command Reference Section

New section "Docker Management Commands" with categories:

#### Service Management
```bash
# Start/Stop/Restart
docker compose up -d                    # Start all services (detached)
docker compose down                     # Stop all services
docker compose restart admin            # Restart single service
docker compose stop tangerine           # Stop without removing

# View status
docker compose ps                       # List running services
docker compose ps -a                    # Include stopped services
```

#### Image Management
```bash
# Build/Rebuild
docker compose build                    # Build all images
docker compose build --no-cache admin   # Force rebuild (no cache)
docker compose up --build -d            # Build and start

# Clean up images
docker image ls                         # List all images
docker image prune                      # Remove unused images
docker image rm tangerine-admin         # Remove specific image
```

#### Volume Management
```bash
# List volumes
docker volume ls                        # List all volumes
docker volume inspect tangerine_db_data # Inspect volume details

# Backup/Restore database
docker compose exec db pg_dump -U tangerine_admin tangerine_db > backup.sql
docker compose exec -T db psql -U tangerine_admin tangerine_db < backup.sql

# Reset volumes (DESTRUCTIVE)
docker compose down --volumes           # Remove all data
docker volume rm tangerine_db_data      # Remove specific volume
```

#### Log Management
```bash
# View logs
docker compose logs -f admin            # Follow admin logs
docker compose logs --tail=100 tangerine # Last 100 lines
docker compose logs --since=1h          # Logs from last hour

# Log files (inside container)
docker compose exec admin ls /app/logs
docker compose exec admin tail -f /app/logs/etl.log
```

#### Container Access
```bash
# Shell access
docker compose exec tangerine bash      # Shell into ETL container
docker compose exec db psql -U tangerine_admin -d tangerine_db  # DB shell
docker compose exec admin python        # Python REPL in admin

# Run one-off commands
docker compose run --rm tangerine python -c "print('test')"
```

### 5. Update Existing Sections

- Move scattered Docker commands to new unified section
- Remove duplicate command examples
- Add cross-references to new sections

---

## Files to Modify

| File | Action |
|------|--------|
| `/opt/tangerine/README.md` | Update with diagrams and commands |

---

## Verification

1. All ASCII diagrams render correctly in markdown preview
2. Docker commands are accurate and tested
3. No duplicate sections or commands
4. Links and cross-references work
5. Table of contents (if exists) updated
