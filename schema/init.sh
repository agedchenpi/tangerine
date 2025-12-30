#!/bin/bash
set -e  # Exit on error

# Environment vars from docker-compose
PSQL="psql -U $POSTGRES_USER -d $POSTGRES_DB"

# Execute DBA schema files in order (add new ones here without renumbering)
$PSQL -f /app/schema/dba/schema.sql
$PSQL -f /app/schema/dba/tables/tdatasettype.sql
$PSQL -f /app/schema/dba/tables/tdatasource.sql
$PSQL -f /app/schema/dba/tables/tdatastatus.sql
$PSQL -f /app/schema/dba/tables/tdataset.sql
$PSQL -f /app/schema/dba/tables/tholidays.sql
$PSQL -f /app/schema/dba/tables/tcalendardays.sql
$PSQL -f /app/schema/dba/tables/tddllogs.sql
$PSQL -f /app/schema/dba/tables/tlogentry.sql
$PSQL -f /app/schema/dba/functions/fenforcesingleactivedataset.sql
$PSQL -f /app/schema/dba/functions/f_dataset_iu.sql
$PSQL -f /app/schema/dba/functions/flogddlchanges.sql
$PSQL -f /app/schema/dba/indexes/idx_tdataset_datasetdate.sql
$PSQL -f /app/schema/dba/indexes/idx_tdataset_isactive.sql
$PSQL -f /app/schema/dba/indexes/idx_tcalendardays_fulldate.sql
$PSQL -f /app/schema/dba/indexes/idx_tcalendardays_isbusday.sql
$PSQL -f /app/schema/dba/indexes/idx_tlogentry_timestamp.sql
$PSQL -f /app/schema/dba/indexes/idx_tlogentry_run_uuid.sql
$PSQL -f /app/schema/dba/triggers/ttriggerenforcesingleactivedataset.sql
$PSQL -f /app/schema/dba/triggers/logddl_event_trigger.sql
$PSQL -f /app/schema/dba/data/tdatasettype_inserts.sql
$PSQL -f /app/schema/dba/data/tdatastatus_inserts.sql
$PSQL -f /app/schema/dba/data/tholidays_inserts.sql
$PSQL -f /app/schema/dba/data/tcalendardays_population.sql

# Execute feeds schema files in order
$PSQL -f /app/schema/feeds/schema.sql
# Add more feeds files here as needed

# Optional: Execute shared_queries.sql last if it depends on everything
$PSQL -f /app/schema/shared_queries.sql