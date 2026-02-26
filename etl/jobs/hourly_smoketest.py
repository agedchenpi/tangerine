"""
Hourly Cron Scheduler Smoketest.

Canary job that runs every hour to verify the cron scheduler and dataset
creation pipeline are working end-to-end. Creates a dataset record via
dba.f_dataset_iu and confirms the full ETL lifecycle completes.

Tests: DB connectivity, f_dataset_iu, ETL logging, dataset status transitions.

Usage:
    python etl/jobs/hourly_smoketest.py
"""

import sys
import uuid
from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob


class HourlySmoketestJob(BaseETLJob):
    """
    Hourly smoketest verifying cron scheduler and dataset creation pipeline.

    Lifecycle:
        1. extract() - Returns a single synthetic record
        2. transform() - Pass-through (no transformation needed)
        3. load() - No-op (dataset record creation is the test)
    """

    def __init__(self):
        run_uuid = str(uuid.uuid4())
        today = date.today()
        super().__init__(
            run_date=today,
            dataset_type='Smoketest',
            data_source='Smoketest',
            run_uuid=run_uuid,
            username='etl_user',
            dataset_label='HourlySmoketest'
        )

    def extract(self) -> List[Dict[str, Any]]:
        return [{"smoketest": True, "timestamp": datetime.now().isoformat()}]

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return data

    def load(self, data: List[Dict[str, Any]]):
        self.records_loaded = len(data)


def main():
    job = HourlySmoketestJob()
    print(f"Run UUID: {job.run_uuid}")
    success = job.run()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
