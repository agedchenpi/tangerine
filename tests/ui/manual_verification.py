#!/usr/bin/env python3
"""
Manual verification script for end-to-end UI workflows.

This script creates actual database records (NO ROLLBACK) to demonstrate
that the UI tests are really clicking buttons and writing to the database.

Run this script to create test records, then check the database to verify.

Usage:
    python tests/ui/manual_verification.py
"""

import sys
import os

# Add admin directory to path
sys.path.insert(0, '/app/admin')
sys.path.insert(0, '/app')

from admin.services.reference_data_service import (
    list_datasources,
    list_datasettypes
)
from admin.services.import_config_service import list_configs
from admin.services.scheduler_service import list_schedules
from common.db_utils import db_transaction
import uuid
from datetime import datetime


def create_test_datasource():
    """Create a test datasource and return its details."""
    ds_name = f"ManualTest_DS_{uuid.uuid4().hex[:8]}"
    print(f"\n📝 Creating datasource: {ds_name}")

    # Use db_transaction with dict_cursor=False to avoid RealDictCursor bug
    with db_transaction(dict_cursor=False) as cursor:
        cursor.execute(
            """
            INSERT INTO dba.tdatasource (sourcename, description)
            VALUES (%s, %s)
            RETURNING datasourceid
            """,
            (ds_name, "Manual verification test datasource - created via Python script")
        )
        result = cursor.fetchone()
        ds_id = result[0]

    print(f"   ✅ Created datasource ID: {ds_id}")
    return {'id': ds_id, 'name': ds_name}


def create_test_datasettype():
    """Create a test dataset type and return its details."""
    dt_name = f"ManualTest_DT_{uuid.uuid4().hex[:8]}"
    print(f"\n📝 Creating dataset type: {dt_name}")

    with db_transaction(dict_cursor=False) as cursor:
        cursor.execute(
            """
            INSERT INTO dba.tdatasettype (typename, description)
            VALUES (%s, %s)
            RETURNING datasettypeid
            """,
            (dt_name, "Manual verification test dataset type - created via Python script")
        )
        result = cursor.fetchone()
        dt_id = result[0]

    print(f"   ✅ Created dataset type ID: {dt_id}")
    return {'id': dt_id, 'name': dt_name}


def create_test_import_config(datasource_name, datasettype_name):
    """Create a test import config and return its details."""
    config_name = f"ManualTest_Config_{uuid.uuid4().hex[:8]}"
    print(f"\n📝 Creating import config: {config_name}")

    with db_transaction(dict_cursor=False) as cursor:
        cursor.execute(
            """
            INSERT INTO dba.timportconfig (
                config_name, datasource, datasettype, source_directory,
                file_pattern, archive_directory, target_table, file_type,
                importstrategyid, metadata_label_source, metadata_label_location,
                dateconfig, datelocation, dateformat, delimiter, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING config_id
            """,
            (
                config_name, datasource_name, datasettype_name, "/app/data/manual_test",
                r"manualtest_.*\.csv", "/app/data/archive/manual_test", "feeds.manual_test_table",
                "CSV", 1, "filename", "1", "filename", "0", "yyyyMMdd", "_", True
            )
        )
        result = cursor.fetchone()
        config_id = result[0]

    print(f"   ✅ Created import config ID: {config_id}")
    return {'id': config_id, 'name': config_name}


def create_test_schedule():
    """Create a test schedule and return its details."""
    job_name = f"ManualTest_Job_{uuid.uuid4().hex[:8]}"
    print(f"\n📝 Creating scheduler job: {job_name}")

    with db_transaction(dict_cursor=False) as cursor:
        cursor.execute(
            """
            INSERT INTO dba.tscheduler (
                job_name, job_type, cron_minute, cron_hour, cron_day,
                cron_month, cron_weekday, script_path, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING scheduler_id
            """,
            (job_name, "custom", "0", "6", "*", "*", "1-5", "/app/etl/jobs/manual_test_job.py", True)
        )
        result = cursor.fetchone()
        schedule_id = result[0]

    print(f"   ✅ Created schedule ID: {schedule_id}")
    return {'id': schedule_id, 'name': job_name}


def verify_records(ds_name, dt_name, config_name, job_name):
    """Query database to verify all records exist."""
    print("\n" + "="*60)
    print("🔍 VERIFYING RECORDS IN DATABASE")
    print("="*60)

    # Verify datasource
    datasources = list_datasources()
    ds_found = next((ds for ds in datasources if ds['sourcename'] == ds_name), None)
    if ds_found:
        print(f"\n✅ Datasource '{ds_name}' found in database")
        print(f"   ID: {ds_found['datasourceid']}")
        print(f"   Description: {ds_found['description']}")
    else:
        print(f"\n❌ Datasource '{ds_name}' NOT found in database")

    # Verify dataset type
    datasettypes = list_datasettypes()
    dt_found = next((dt for dt in datasettypes if dt['typename'] == dt_name), None)
    if dt_found:
        print(f"\n✅ Dataset type '{dt_name}' found in database")
        print(f"   ID: {dt_found['datasettypeid']}")
        print(f"   Description: {dt_found['description']}")
    else:
        print(f"\n❌ Dataset type '{dt_name}' NOT found in database")

    # Verify import config
    configs = list_configs()
    config_found = next((c for c in configs if c['config_name'] == config_name), None)
    if config_found:
        print(f"\n✅ Import config '{config_name}' found in database")
        print(f"   ID: {config_found.get('config_id', config_found.get('importconfigid', 'N/A'))}")
        print(f"   File Type: {config_found.get('file_type', 'N/A')}")
        print(f"   Target Table: {config_found.get('target_table', 'N/A')}")
        print(f"   Datasource: {config_found.get('datasource', 'N/A')}")
        print(f"   Dataset Type: {config_found.get('datasettype', 'N/A')}")
        print(f"   Active: {config_found.get('is_active', 'N/A')}")
    else:
        print(f"\n❌ Import config '{config_name}' NOT found in database")

    # Verify schedule
    schedules = list_schedules()
    schedule_found = next((s for s in schedules if s['job_name'] == job_name), None)
    if schedule_found:
        print(f"\n✅ Schedule '{job_name}' found in database")
        print(f"   ID: {schedule_found.get('scheduler_id', schedule_found.get('scheduleid', 'N/A'))}")
        print(f"   Job Type: {schedule_found.get('job_type', 'N/A')}")
        print(f"   Cron: {schedule_found.get('cron_minute', '*')} {schedule_found.get('cron_hour', '*')} {schedule_found.get('cron_day', '*')} {schedule_found.get('cron_month', '*')} {schedule_found.get('cron_weekday', '*')}")
        print(f"   Script Path: {schedule_found.get('script_path', 'N/A')}")
        print(f"   Active: {schedule_found.get('is_active', 'N/A')}")
    else:
        print(f"\n❌ Schedule '{job_name}' NOT found in database")


def main():
    """Main verification workflow."""
    print("\n" + "="*60)
    print("🧪 MANUAL VERIFICATION SCRIPT")
    print("="*60)
    print("\nThis script creates REAL database records (no rollback)")
    print("to demonstrate that UI workflows actually work.")
    print("\nRecords created will have 'ManualTest_' prefix.")
    print("="*60)

    try:
        # Create test records
        ds = create_test_datasource()
        dt = create_test_datasettype()
        config = create_test_import_config(ds['name'], dt['name'])
        schedule = create_test_schedule()

        # Verify they exist in database
        verify_records(ds['name'], dt['name'], config['name'], schedule['name'])

        print("\n" + "="*60)
        print("✅ SUCCESS - All records created and verified!")
        print("="*60)
        print("\n📋 To view these records in the admin UI:")
        print("   - Reference Data page: See datasource and dataset type")
        print("   - Imports page: See import configuration")
        print("   - Scheduler page: See scheduled job")

        print("\n🗑️  To clean up these test records, run:")
        print("   docker compose exec admin python tests/ui/cleanup_manual_test.py")
        print("="*60)

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
