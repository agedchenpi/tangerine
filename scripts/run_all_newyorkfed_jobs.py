#!/usr/bin/env python3
"""
Run all NewYorkFed Markets API ETL jobs via the collector pattern.

This script executes all NewYorkFed import jobs in sequence using
newyorkfed_collector, loading data from the Federal Reserve Bank of
New York Markets API into the Tangerine database.

Usage:
    python scripts/run_all_newyorkfed_jobs.py [--dry-run]

Examples:
    # Run all jobs (loads to database)
    python scripts/run_all_newyorkfed_jobs.py

    # Test all jobs without loading
    python scripts/run_all_newyorkfed_jobs.py --dry-run
"""

import argparse
import subprocess
import sys
from typing import List, Tuple


# Config IDs and labels for all NewYorkFed endpoints
JOBS = [
    (1,  "Reference Rates (Latest)"),
    (3,  "SOMA Holdings"),
    (4,  "Repo Operations"),
    (5,  "Reverse Repo Operations"),
    (6,  "Agency MBS"),
    (7,  "FX Swaps"),
    (8,  "Securities Lending"),
    (9,  "Guide Sheets"),
    (10, "PD Statistics"),
    (11, "Market Share"),
    (12, "Treasury Operations"),
]


def run_all_jobs(dry_run: bool = False) -> Tuple[int, int]:
    """
    Run all NewYorkFed ETL jobs via the collector.

    Args:
        dry_run: If True, run in dry-run mode (no database writes)

    Returns:
        Tuple of (successful_jobs, failed_jobs) counts
    """
    print("=" * 70)
    print(f"Running {len(JOBS)} NewYorkFed ETL Jobs")
    print(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    print("=" * 70)
    print()

    successful = 0
    failed = 0
    results = []

    for config_id, job_name in JOBS:
        print(f"Running: {job_name} (config-id {config_id})...", end=" ", flush=True)

        cmd = [
            sys.executable,
            "etl/collectors/newyorkfed_collector.py",
            "--config-id", str(config_id),
        ]
        if dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"SUCCESS")
                results.append((job_name, "SUCCESS", config_id))
                successful += 1
            else:
                print(f"FAILED")
                if result.stderr:
                    print(f"  stderr: {result.stderr.strip()[:200]}")
                results.append((job_name, "FAILED", config_id))
                failed += 1
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT")
            results.append((job_name, "TIMEOUT", config_id))
            failed += 1
        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append((job_name, "ERROR", config_id))
            failed += 1

    # Print summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"{'Job':<35} {'Status':<15} {'Config ID'}")
    print("-" * 70)
    for job_name, status, config_id in results:
        print(f"{job_name:<35} {status:<15} {config_id:>9}")
    print("-" * 70)
    print(f"Total: {successful} successful, {failed} failed")
    print("=" * 70)

    return successful, failed


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run all NewYorkFed Markets API ETL jobs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (fetch and transform but do not load to database)"
    )
    args = parser.parse_args()

    successful, failed = run_all_jobs(dry_run=args.dry_run)

    # Exit with non-zero status if any jobs failed
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
