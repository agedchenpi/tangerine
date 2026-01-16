---
name: database-operations
description: PostgreSQL schema patterns for Tangerine - table design, naming conventions, migrations. CRITICAL GUARDRAIL.
---

# Database Operations Guidelines

⚠️ **GUARDRAIL SKILL** - Follow these patterns strictly to prevent data loss.

## Schema Location

```
schema/
├── init.sh              # Initialization script
├── dba/                 # Pipeline schema (ETL configuration)
│   ├── schema.sql       # Schema creation
│   ├── tables/          # Table definitions
│   ├── procedures/      # Stored procedures (UPSERT)
│   ├── views/           # Views
│   └── data/            # Reference data inserts
└── feeds/               # Raw data schema (imported data)
```

## Naming Conventions

| Object | Prefix | Example |
|--------|--------|---------|
| Table | t | `timportconfig`, `tdataset` |
| Procedure | p | `pimportconfigi`, `pimportconfigu` |
| Function | f | `fgetlabel`, `fformatdate` |
| View | v | `vimportstatus`, `vdatasetdetail` |
| Index | idx_ | `idx_dataset_date`, `idx_config_name` |
| Foreign Key | fk_ | `fk_dataset_source`, `fk_config_type` |
| Check Constraint | chk_ | `chk_positive_amount`, `chk_valid_status` |

## Table Template

```sql
-- ============================================================================
-- Table: dba.ttablename
-- Purpose: Brief description of what this table stores
-- ============================================================================

CREATE TABLE IF NOT EXISTS dba.ttablename (
    -- Primary key
    tablename_id SERIAL PRIMARY KEY,

    -- Business columns
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Foreign keys
    related_id INTEGER NOT NULL,

    -- Status/flags
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit columns
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) NOT NULL DEFAULT CURRENT_USER,
    last_modified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT fk_tablename_related
        FOREIGN KEY (related_id)
        REFERENCES dba.trelated(related_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tablename_name
    ON dba.ttablename(name);

CREATE INDEX IF NOT EXISTS idx_tablename_active
    ON dba.ttablename(is_active)
    WHERE is_active = TRUE;

-- Comments
COMMENT ON TABLE dba.ttablename IS 'Description of table purpose';
COMMENT ON COLUMN dba.ttablename.name IS 'Description of column';
```

## Key Tables Reference

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `timportconfig` | Import job configurations | config_id, config_name, file_pattern, target_table |
| `tdataset` | Dataset tracking | datasetid, label, datasetdate, datastatusid |
| `tdatasource` | Data source reference | datasourceid, sourcename |
| `tdatasettype` | Dataset type reference | datasettypeid, typename |
| `tlogentry` | ETL execution logs | run_uuid, message, stepruntime |
| `tinboxconfig` | Gmail inbox rules | inbox_config_id, subject_pattern, target_directory |
| `treportmanager` | Report configurations | report_id, recipients, body_template |
| `tscheduler` | Cron job definitions | scheduler_id, job_type, cron_* fields |
| `tpubsub_events` | Event queue | event_id, event_type, status |
| `tpubsub_subscribers` | Event subscribers | subscriber_id, handler_type |

## Data Types

| Use Case | Type | Example |
|----------|------|---------|
| Auto-increment ID | `SERIAL` | `tablename_id SERIAL PRIMARY KEY` |
| Foreign key | `INTEGER` | `related_id INTEGER NOT NULL` |
| Short text (names) | `VARCHAR(100)` | `name VARCHAR(100) NOT NULL` |
| Long text | `TEXT` | `description TEXT` |
| Boolean flags | `BOOLEAN` | `is_active BOOLEAN DEFAULT TRUE` |
| Timestamps | `TIMESTAMP` | `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` |
| Dates only | `DATE` | `datasetdate DATE NOT NULL` |
| JSON data | `JSONB` | `config_data JSONB` |
| Money/decimals | `NUMERIC(12,2)` | `amount NUMERIC(12,2)` |

## Stored Procedure Pattern

For UPSERT operations (INSERT or UPDATE):

```sql
-- ============================================================================
-- Procedure: dba.ptablenamei (INSERT/UPDATE)
-- ============================================================================

CREATE OR REPLACE PROCEDURE dba.ptablenamei(
    p_id INTEGER,
    p_name VARCHAR(100),
    p_description TEXT,
    p_is_active BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_id IS NULL OR p_id = 0 THEN
        -- INSERT
        INSERT INTO dba.ttablename (name, description, is_active)
        VALUES (p_name, p_description, p_is_active);
    ELSE
        -- UPDATE
        UPDATE dba.ttablename
        SET name = p_name,
            description = p_description,
            is_active = p_is_active,
            last_modified_at = CURRENT_TIMESTAMP
        WHERE tablename_id = p_id;
    END IF;
END;
$$;
```

## ⚠️ CRITICAL: NEVER Do These

### 1. DELETE Without WHERE

```sql
-- DANGEROUS - deletes ALL rows
DELETE FROM dba.ttablename;

-- SAFE - deletes specific row
DELETE FROM dba.ttablename WHERE tablename_id = 123;
```

### 2. DROP Without IF EXISTS

```sql
-- DANGEROUS - fails if table doesn't exist
DROP TABLE dba.ttablename;

-- SAFE - idempotent
DROP TABLE IF EXISTS dba.ttablename;
```

### 3. UPDATE Without WHERE

```sql
-- DANGEROUS - updates ALL rows
UPDATE dba.ttablename SET status = 'inactive';

-- SAFE - updates specific row
UPDATE dba.ttablename SET status = 'inactive' WHERE tablename_id = 123;
```

### 4. TRUNCATE on Production Tables

```sql
-- DANGEROUS - cannot be rolled back easily
TRUNCATE dba.timportconfig;

-- If you must clear data, use DELETE with explicit condition
DELETE FROM dba.timportconfig WHERE is_active = FALSE;
```

### 5. Direct Schema Changes Without Backup

Always backup before ALTER TABLE:

```sql
-- Create backup first
CREATE TABLE dba.ttablename_backup AS SELECT * FROM dba.ttablename;

-- Then make changes
ALTER TABLE dba.ttablename ADD COLUMN new_column VARCHAR(50);
```

## Migration Workflow

1. **Create backup** of affected tables
2. **Write migration script** with IF EXISTS/IF NOT EXISTS guards
3. **Test on dev** database first
4. **Review script** with another person
5. **Execute during low-traffic** window
6. **Verify data integrity** after migration

### Safe Migration Template

```sql
-- Migration: Add new_column to ttablename
-- Date: 2026-01-16
-- Author: your_name

-- Step 1: Check current state
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'dba' AND table_name = 'ttablename';

-- Step 2: Add column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'dba'
        AND table_name = 'ttablename'
        AND column_name = 'new_column'
    ) THEN
        ALTER TABLE dba.ttablename ADD COLUMN new_column VARCHAR(50);
    END IF;
END $$;

-- Step 3: Verify
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'dba' AND table_name = 'ttablename'
ORDER BY ordinal_position;
```

## Testing Schema Changes

```bash
# Reset database completely (DEV ONLY)
docker compose down --volumes
docker compose up --build -d

# Connect to database
docker compose exec db psql -U tangerine_admin -d tangerine_db

# List tables
\dt dba.*

# Describe table
\d dba.ttablename

# Check indexes
\di dba.*
```

## Common Queries

### Check Table Exists

```sql
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'dba' AND table_name = 'ttablename'
);
```

### Check Column Exists

```sql
SELECT EXISTS (
    SELECT FROM information_schema.columns
    WHERE table_schema = 'dba'
    AND table_name = 'ttablename'
    AND column_name = 'column_name'
);
```

### List Foreign Keys

```sql
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table,
    ccu.column_name AS foreign_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_schema = 'dba';
```
