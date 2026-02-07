#!/usr/bin/env python3
"""
Run all NewYorkFed Markets API ETL jobs.

This script executes all 9 NewYorkFed import jobs in sequence,
loading data from the Federal Reserve Bank of New York Markets API
into the Tangerine database.

Usage:
    python scripts/run_all_newyorkfed_jobs.py [--dry-run]

Examples:
    # Run all jobs (loads to database)
    python scripts/run_all_newyorkfed_jobs.py

    # Test all jobs without loading
    python scripts/run_all_newyorkfed_jobs.py --dry-run
"""

import argparse
import sys
from datetime import date
from typing import List, Tuple

from etl.jobs.run_newyorkfed_reference_rates import NewYorkFedReferenceRatesJob
from etl.jobs.run_newyorkfed_soma_holdings import NewYorkFedSOMAHoldingsJob
from etl.jobs.run_newyorkfed_repo import NewYorkFedRepoOperationsJob
from etl.jobs.run_newyorkfed_securities_lending import NewYorkFedSecuritiesLendingJob
from etl.jobs.run_newyorkfed_treasury import NewYorkFedTreasuryJob
from etl.jobs.run_newyorkfed_agency_mbs import NewYorkFedAgencyMBSJob
from etl.jobs.run_newyorkfed_fx_swaps import NewYorkFedFXSwapsJob
from etl.jobs.run_newyorkfed_guide_sheets import NewYorkFedGuideSheetsJob
from etl.jobs.run_newyorkfed_counterparties import NewYorkFedCounterpartiesJob


def run_all_jobs(dry_run: bool = False) -> Tuple[int, int]:
    """
    Run all NewYorkFed ETL jobs.

    Args:
        dry_run: If True, run in dry-run mode (no database writes)

    Returns:
        Tuple of (successful_jobs, failed_jobs) counts
    """
    run_date = date.today()

    # Define all jobs to run
    jobs = [
        ("Reference Rates", NewYorkFedReferenceRatesJob(run_date=run_date, dry_run=dry_run)),
        ("SOMA Holdings", NewYorkFedSOMAHoldingsJob(run_date=run_date, dry_run=dry_run)),
        ("Repo Operations", NewYorkFedRepoOperationsJob(run_date=run_date, dry_run=dry_run)),
        ("Securities Lending", NewYorkFedSecuritiesLendingJob(run_date=run_date, dry_run=dry_run)),
        ("Treasury Operations", NewYorkFedTreasuryJob(run_date=run_date, dry_run=dry_run)),
        ("Agency MBS", NewYorkFedAgencyMBSJob(run_date=run_date, dry_run=dry_run)),
        ("FX Swaps", NewYorkFedFXSwapsJob(run_date=run_date, dry_run=dry_run)),
        ("Guide Sheets", NewYorkFedGuideSheetsJob(run_date=run_date, dry_run=dry_run)),
        ("FX Counterparties", NewYorkFedCounterpartiesJob(run_date=run_date, dry_run=dry_run)),
    ]

    print("=" * 70)
    print(f"Running {len(jobs)} NewYorkFed ETL Jobs")
    print(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    print(f"Date: {run_date}")
    print("=" * 70)
    print()

    successful = 0
    failed = 0
    results = []

    for job_name, job in jobs:
        print(f"Running: {job_name}...", end=" ", flush=True)
        try:
            success = job.run()
            if success:
                records = job.records_loaded if hasattr(job, 'records_loaded') else 0
                print(f"✅ SUCCESS ({records} records)")
                results.append((job_name, "✅ SUCCESS", records))
                successful += 1
            else:
                print("❌ FAILED")
                results.append((job_name, "❌ FAILED", 0))
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append((job_name, f"❌ ERROR", 0))
            failed += 1

    # Print summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"{'Job':<25} {'Status':<15} {'Records'}")
    print("-" * 70)
    for job_name, status, records in results:
        print(f"{job_name:<25} {status:<15} {records:>7}")
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
