#!/usr/bin/env python3
"""
Run all NewYorkFed Markets API ETL jobs.

This script executes all NewYorkFed import jobs in sequence using
individual scripts, loading data from the Federal Reserve Bank of
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


# Individual scripts and labels for all NewYorkFed endpoints
JOBS = [
    ("etl/jobs/run_newyorkfed_reference_rates.py",  "Reference Rates (Latest)"),
    ("etl/jobs/run_newyorkfed_soma_holdings.py",     "SOMA Holdings"),
    ("etl/jobs/run_newyorkfed_repo.py",              "Repo Operations"),
    ("etl/jobs/run_newyorkfed_reverserepo.py",       "Reverse Repo Operations"),
    ("etl/jobs/run_newyorkfed_agency_mbs.py",        "Agency MBS"),
    ("etl/jobs/run_newyorkfed_fx_swaps.py",          "FX Swaps"),
    ("etl/jobs/run_newyorkfed_securities_lending.py", "Securities Lending"),
    ("etl/jobs/run_newyorkfed_guide_sheets.py",      "Guide Sheets"),
    ("etl/jobs/run_newyorkfed_pd_statistics.py",     "PD Statistics"),
    ("etl/jobs/run_newyorkfed_market_share.py",      "Market Share"),
    ("etl/jobs/run_newyorkfed_treasury.py",          "Treasury Operations"),
]


def run_all_jobs(dry_run: bool = False) -> Tuple[int, int]:
    """
    Run all NewYorkFed ETL jobs via individual scripts.

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

    for script_path, job_name in JOBS:
        print(f"Running: {job_name}...", end=" ", flush=True)

        cmd = [sys.executable, script_path]
        if dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"SUCCESS")
                results.append((job_name, "SUCCESS", script_path))
                successful += 1
            else:
                print(f"FAILED")
                if result.stderr:
                    print(f"  stderr: {result.stderr.strip()[:200]}")
                results.append((job_name, "FAILED", script_path))
                failed += 1
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT")
            results.append((job_name, "TIMEOUT", script_path))
            failed += 1
        except Exception as e:
            print(f"ERROR: {str(e)}")
            results.append((job_name, "ERROR", script_path))
            failed += 1

    # Print summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"{'Job':<35} {'Status':<15} {'Script'}")
    print("-" * 70)
    for job_name, status, script_path in results:
        print(f"{job_name:<35} {status:<15} {script_path}")
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
