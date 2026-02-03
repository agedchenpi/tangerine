#!/usr/bin/env python3
"""
Cleanup script for manual verification test records.

This script removes all ManualTest_* records created by manual_verification.py

Usage:
    python tests/ui/cleanup_manual_test.py
"""

import sys
import os

# Add admin directory to path
sys.path.insert(0, '/app/admin')
sys.path.insert(0, '/app')

from common.db_utils import db_transaction


def cleanup_manual_test_records():
    """Remove all ManualTest_* records from database."""
    print("\n" + "="*60)
    print("🗑️  CLEANING UP MANUAL TEST RECORDS")
    print("="*60)

    with db_transaction() as cursor:
        # Clean import configs first (foreign key dependencies)
        cursor.execute("""
            DELETE FROM dba.timportconfig
            WHERE config_name LIKE 'ManualTest_%%'
        """)
        config_count = cursor.rowcount
        print(f"\n🗑️  Deleted {config_count} import config(s)")

        # Clean schedules
        cursor.execute("""
            DELETE FROM dba.tscheduler
            WHERE job_name LIKE 'ManualTest_%%'
        """)
        schedule_count = cursor.rowcount
        print(f"🗑️  Deleted {schedule_count} schedule(s)")

        # Clean datasources
        cursor.execute("""
            DELETE FROM dba.tdatasource
            WHERE sourcename LIKE 'ManualTest_%%'
        """)
        ds_count = cursor.rowcount
        print(f"🗑️  Deleted {ds_count} datasource(s)")

        # Clean dataset types
        cursor.execute("""
            DELETE FROM dba.tdatasettype
            WHERE typename LIKE 'ManualTest_%%'
        """)
        dt_count = cursor.rowcount
        print(f"🗑️  Deleted {dt_count} dataset type(s)")

    print("\n" + "="*60)
    print("✅ Cleanup complete!")
    print("="*60)
    print(f"\nTotal records deleted: {config_count + schedule_count + ds_count + dt_count}")


def main():
    try:
        cleanup_manual_test_records()
        return 0
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
