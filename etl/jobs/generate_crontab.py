"""
Crontab Generator - Generates and updates container crontab from scheduler config.

Reads active schedules from dba.tscheduler and generates crontab entries
for automatic execution of inbox processors, reports, imports, and custom scripts.

Usage:
    python etl/jobs/generate_crontab.py [--preview] [--apply]

Examples:
    # Preview crontab entries without applying
    python etl/jobs/generate_crontab.py --preview

    # Apply crontab to the container
    python etl/jobs/generate_crontab.py --apply

    # Both preview and apply
    python etl/jobs/generate_crontab.py --preview --apply
"""

import argparse
import subprocess
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from common.db_utils import fetch_dict, db_transaction

# Optional croniter for next run calculation
try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False


def generate_crontab_entries() -> List[str]:
    """
    Generate crontab entries from tscheduler table.

    Returns:
        List of crontab lines
    """
    query = """
        SELECT * FROM dba.tscheduler
        WHERE is_active = TRUE
        ORDER BY scheduler_id
    """
    schedules = fetch_dict(query) or []

    entries = [
        '# ============================================================',
        '# Tangerine ETL Scheduler - Auto-generated Crontab',
        '# ============================================================',
        f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '# WARNING: Do not edit manually - changes will be overwritten',
        '# Use the admin UI or dba.tscheduler table to manage schedules',
        '# ============================================================',
        '',
        '# Environment setup',
        'SHELL=/bin/bash',
        'PATH=/usr/local/bin:/usr/bin:/bin:/app',
        'PYTHONPATH=/app',
        '',
    ]

    if not schedules:
        entries.append('# No active schedules configured')
        return entries

    for schedule in schedules:
        cron_expr = ' '.join([
            schedule['cron_minute'],
            schedule['cron_hour'],
            schedule['cron_day'],
            schedule['cron_month'],
            schedule['cron_weekday']
        ])

        job_type = schedule['job_type']
        config_id = schedule.get('config_id')
        script_path = schedule.get('script_path')

        # Build command based on job type
        if job_type == 'inbox_processor':
            if config_id:
                cmd = f'cd /app && python etl/jobs/run_gmail_inbox_processor.py --config-id {config_id}'
            else:
                cmd = 'cd /app && python etl/jobs/run_gmail_inbox_processor.py'

        elif job_type == 'report':
            if config_id:
                cmd = f'cd /app && python etl/jobs/run_report_generator.py --report-id {config_id}'
            else:
                cmd = 'cd /app && python etl/jobs/run_report_generator.py'

        elif job_type == 'import':
            if config_id:
                cmd = f'cd /app && python etl/jobs/generic_import.py --config-id {config_id}'
            else:
                continue  # Import requires config_id

        elif job_type == 'custom':
            if script_path:
                # Validate script path exists (relative to /app)
                cmd = f'cd /app && python {script_path}'
            else:
                continue  # Custom requires script_path

        else:
            continue  # Unknown job type

        # Add logging redirection
        log_file = '/app/logs/cron.log'
        full_cmd = f'{cmd} >> {log_file} 2>&1'

        # Add entry with comment
        entries.append(f'# {schedule["job_name"]} (ID: {schedule["scheduler_id"]}, Type: {job_type})')

        # Calculate next run if croniter available
        if HAS_CRONITER:
            try:
                cron = croniter(cron_expr, datetime.now())
                next_run = cron.get_next(datetime)
                entries.append(f'# Next run: {next_run.strftime("%Y-%m-%d %H:%M:%S")}')
            except Exception:
                pass

        entries.append(f'{cron_expr} {full_cmd}')
        entries.append('')

    return entries


def apply_crontab(entries: List[str]) -> bool:
    """
    Apply crontab entries to the container.

    Args:
        entries: List of crontab lines

    Returns:
        True if successful, False otherwise
    """
    crontab_content = '\n'.join(entries) + '\n'

    # Write to temp file
    temp_file = '/tmp/tangerine_crontab'
    try:
        with open(temp_file, 'w') as f:
            f.write(crontab_content)

        # Install crontab
        result = subprocess.run(
            ['crontab', temp_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Error installing crontab: {result.stderr}")
            return False

        print("Crontab updated successfully")
        return True

    except Exception as e:
        print(f"Error applying crontab: {e}")
        return False

    finally:
        # Clean up temp file
        try:
            os.remove(temp_file)
        except Exception:
            pass


def update_next_run_times():
    """
    Update next_run_at timestamps for all active schedules.
    """
    if not HAS_CRONITER:
        print("croniter not installed, skipping next_run_at updates")
        return

    query = "SELECT scheduler_id, cron_minute, cron_hour, cron_day, cron_month, cron_weekday FROM dba.tscheduler WHERE is_active = TRUE"
    schedules = fetch_dict(query) or []

    for schedule in schedules:
        cron_expr = ' '.join([
            schedule['cron_minute'],
            schedule['cron_hour'],
            schedule['cron_day'],
            schedule['cron_month'],
            schedule['cron_weekday']
        ])

        try:
            cron = croniter(cron_expr, datetime.now())
            next_run = cron.get_next(datetime)

            with db_transaction() as cursor:
                cursor.execute(
                    "UPDATE dba.tscheduler SET next_run_at = %s WHERE scheduler_id = %s",
                    (next_run, schedule['scheduler_id'])
                )

        except Exception as e:
            print(f"Error calculating next run for schedule {schedule['scheduler_id']}: {e}")


def get_current_crontab() -> Optional[str]:
    """
    Get the current crontab content.

    Returns:
        Current crontab string, or None if no crontab set
    """
    try:
        result = subprocess.run(
            ['crontab', '-l'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout
        return None

    except Exception:
        return None


def main():
    """CLI entry point for crontab generator."""
    parser = argparse.ArgumentParser(
        description='Generate and manage crontab from scheduler configuration'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview crontab entries without applying'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply crontab to the container'
    )
    parser.add_argument(
        '--current',
        action='store_true',
        help='Show current crontab'
    )
    parser.add_argument(
        '--update-next-run',
        action='store_true',
        help='Update next_run_at timestamps in database'
    )

    args = parser.parse_args()

    # If no action specified, show help
    if not any([args.preview, args.apply, args.current, args.update_next_run]):
        parser.print_help()
        return 1

    # Show current crontab
    if args.current:
        current = get_current_crontab()
        if current:
            print("Current crontab:")
            print("-" * 60)
            print(current)
        else:
            print("No crontab currently set")
        print()

    # Generate and preview
    if args.preview or args.apply:
        entries = generate_crontab_entries()

        if args.preview:
            print("Generated crontab entries:")
            print("-" * 60)
            print('\n'.join(entries))
            print("-" * 60)
            print()

        if args.apply:
            success = apply_crontab(entries)
            if not success:
                return 1

    # Update next run times
    if args.update_next_run:
        update_next_run_times()
        print("Updated next_run_at timestamps")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
