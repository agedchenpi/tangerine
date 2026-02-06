#!/bin/bash
set -e  # Exit on error

# Environment vars from docker-compose
PSQL="psql -U $POSTGRES_USER -d $POSTGRES_DB"

# Create users if not exists (passwords from env)
$PSQL -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'etl_user') THEN CREATE ROLE etl_user LOGIN PASSWORD '$ETL_USER_PASSWORD'; END IF; END \$\$;"
$PSQL -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'admin') THEN CREATE ROLE admin LOGIN PASSWORD '$ADMIN_PASSWORD' SUPERUSER; END IF; END \$\$;"

# Create group roles if not exists
$PSQL -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN CREATE ROLE app_rw NOLOGIN; END IF; END \$\$;"
$PSQL -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_ro') THEN CREATE ROLE app_ro NOLOGIN; END IF; END \$\$;"

# Assign users to groups
$PSQL -c "GRANT app_rw TO etl_user;"

# Execute DBA schema files in order
$PSQL -f /app/schema/dba/schema.sql
$PSQL -f /app/schema/dba/tables/tdatasettype.sql
$PSQL -f /app/schema/dba/tables/tdatasource.sql
$PSQL -f /app/schema/dba/tables/tdatastatus.sql
$PSQL -f /app/schema/dba/tables/tdataset.sql
$PSQL -f /app/schema/dba/tables/tholidays.sql
$PSQL -f /app/schema/dba/tables/tcalendardays.sql
$PSQL -f /app/schema/dba/tables/tddllogs.sql
$PSQL -f /app/schema/dba/tables/tlogentry.sql
$PSQL -f /app/schema/dba/tables/timportstrategy.sql
$PSQL -f /app/schema/dba/tables/timportconfig.sql
$PSQL -f /app/schema/dba/tables/tregressiontest.sql
$PSQL -f /app/schema/dba/tables/tscheduler.sql
$PSQL -f /app/schema/dba/tables/tinboxconfig.sql
$PSQL -f /app/schema/dba/tables/treportmanager.sql
$PSQL -f /app/schema/dba/tables/tpubsub_events.sql
$PSQL -f /app/schema/dba/tables/tpubsub_subscribers.sql
$PSQL -f /app/schema/dba/functions/fenforcesingleactivedataset.sql
$PSQL -f /app/schema/dba/functions/f_dataset_iu.sql
$PSQL -f /app/schema/dba/functions/flogddlchanges.sql
$PSQL -f /app/schema/dba/procedures/pimportconfig_iu.sql
$PSQL -f /app/schema/dba/procedures/pscheduler_iu.sql
$PSQL -f /app/schema/dba/procedures/pinboxconfig_iu.sql
$PSQL -f /app/schema/dba/procedures/preportmanager_iu.sql
$PSQL -f /app/schema/dba/procedures/ppubsub_iu.sql
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
$PSQL -f /app/schema/dba/data/timportstrategy_inserts.sql
$PSQL -f /app/schema/dba/data/tholidays_inserts.sql
$PSQL -f /app/schema/dba/data/tcalendardays_population.sql
$PSQL -f /app/schema/dba/data/example_reference_data.sql
$PSQL -f /app/schema/dba/data/regression_test_configs.sql
$PSQL -f /app/schema/dba/data/newyorkfed_reference_data.sql
$PSQL -f /app/schema/dba/data/newyorkfed_scheduler_jobs.sql

# Execute DBA views (after data is loaded)
$PSQL -f /app/schema/dba/views/vdataset.sql
$PSQL -f /app/schema/dba/views/vregressiontest_summary.sql

# Execute feeds schema files in order
$PSQL -f /app/schema/feeds/schema.sql
$PSQL -f /app/schema/feeds/newyorkfed_reference_rates.sql
$PSQL -f /app/schema/feeds/newyorkfed_soma_holdings.sql
$PSQL -f /app/schema/feeds/newyorkfed_repo_operations.sql
$PSQL -f /app/schema/feeds/newyorkfed_agency_mbs.sql
$PSQL -f /app/schema/feeds/newyorkfed_fx_swaps.sql
$PSQL -f /app/schema/feeds/newyorkfed_guide_sheets.sql
$PSQL -f /app/schema/feeds/newyorkfed_pd_statistics.sql
$PSQL -f /app/schema/feeds/newyorkfed_market_share.sql
$PSQL -f /app/schema/feeds/newyorkfed_securities_lending.sql
$PSQL -f /app/schema/feeds/newyorkfed_treasury_operations.sql

# Optional: Execute shared_queries.sql last
$PSQL -f /app/schema/shared_queries.sql

# Grant broad read access to PUBLIC (after schema/tables exist)
$PSQL -c "GRANT USAGE ON SCHEMA dba TO PUBLIC;"
$PSQL -c "GRANT SELECT ON ALL TABLES IN SCHEMA dba TO PUBLIC;"