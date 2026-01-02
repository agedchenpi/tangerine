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
The project follows a Vertical Slice Architecture (VSA) for modularity, with shared SQL schemas and utils to support AI agents in ETL workflows. Here's the directory layout:

```
tangerine/
├── Dockerfile
├── docker-compose.yml
├── schema/                     # Shared SQL definitions
│   ├── tables/
│   ├── views/
│   ├── procedures/
│   ├── functions/
│   ├── indexes/
│   ├── triggers/
│   ├── sequences/
│   ├── materialized_views/
│   ├── types/
│   └── extensions/
├── common/                    # Shared utils
│   ├── db_utils.py
│   └── shared_queries.sql
└── run_all.sh                 # Adapted for Docker
```


After cloning the repo, you'll find:
- **schema/**: Shared SQL definitions (e.g., tables/, views/, procedures/). Subdirectories may be empty initially; add placeholder files (e.g., README.md or empty.sql) to commit them if needed.
- **common/**: Shared utilities.
  - `db_utils.py`: Database connection helper using psycopg2 and environment variables.
  - `shared_queries.sql`: Placeholder for reusable SQL queries.
- **Dockerfile**: Builds the Python-based ETL container with dependencies like psycopg2.
- **docker-compose.yml**: Defines services for PostgreSQL (db) and the ETL app (tangerine), using environment variables for configuration.
- **run_all.sh**: Bash script to orchestrate Docker (build, start, run ETL processes, stop). Make executable with `chmod +x run_all.sh`.
- **.gitignore**: Excludes temporary files, Python bytecode, logs, and .env.
- **README.md**: This file.

Future directories:
- **features/**: For AI agent slices (e.g., agent1/main.py for specific ETL tasks with AI logic).

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

## Troubleshooting
- **Command not found (exit 127)**: Check CMD in Dockerfile points to an existing script.
- **Auth errors with Git**: Ensure SSH keys are set up correctly.
- **DB connection issues**: Verify .env vars match and Postgres service is up.
- **Volume/data errors on upgrade**: Run `docker compose down --volumes` to reset.
- **Obsolete warnings in Compose**: Ensure 'version' is removed from yml.
- **No schema subdirs in Git**: Add placeholders and commit.

