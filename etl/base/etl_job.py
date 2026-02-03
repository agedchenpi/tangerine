"""
Base ETL job class with standardized lifecycle and logging.

All ETL jobs should inherit from BaseETLJob to get:
- Automatic logging to database and files
- Dataset metadata tracking
- Error handling and retry logic
- Standardized lifecycle hooks
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Optional, Dict
import time
import uuid

from common.logging_utils import ETLLogger
from common.db_utils import db_transaction, fetch_dict
from common.config import get_config


class BaseETLJob(ABC):
    """
    Base class for all ETL jobs.

    Lifecycle:
        1. setup() - Initialize resources
        2. extract() - Extract data from source
        3. transform() - Transform extracted data
        4. load() - Load transformed data to database
        5. cleanup() - Clean up resources

    Usage:
        class MyETLJob(BaseETLJob):
            def extract(self):
                return api_client.get_data()

            def transform(self, data):
                return [process(record) for record in data]

            def load(self, data):
                bulk_insert('my_table', ['col1', 'col2'], data)

        job = MyETLJob(run_date=date.today(), dataset_type='MyData', data_source='MyAPI')
        job.run()
    """

    def __init__(
        self,
        run_date: date,
        dataset_type: str,
        data_source: str,
        username: Optional[str] = None,
        run_uuid: Optional[str] = None,
        dry_run: bool = False,
        dataset_label: Optional[str] = None
    ):
        """
        Initialize ETL job.

        Args:
            run_date: Date for this ETL run (usually today or data effective date)
            dataset_type: Type of dataset (must exist in dba.tdatasettype)
            data_source: Data source name (must exist in dba.tdatasource)
            username: User executing the job (defaults to 'etl_user')
            run_uuid: Optional run UUID (generates new if not provided)
            dry_run: If True, run extraction and transformation but don't load to DB
            dataset_label: Optional custom label for dataset (defaults to auto-generated)
        """
        self.run_date = run_date
        self.dataset_type = dataset_type
        self.data_source = data_source
        self.username = username or 'etl_user'
        self.run_uuid = run_uuid or str(uuid.uuid4())
        self.dry_run = dry_run
        self.dataset_label = dataset_label  # Custom label if provided

        self.dataset_id: Optional[int] = None
        self.start_time: Optional[float] = None
        self.logger = None
        self.config = get_config()

        # Statistics
        self.records_extracted = 0
        self.records_transformed = 0
        self.records_loaded = 0

    def run(self) -> bool:
        """
        Execute the full ETL pipeline.

        Returns:
            True if successful, False otherwise
        """
        self.start_time = time.time()
        processtype = self.__class__.__name__

        with ETLLogger(processtype, username=self.username, run_uuid=self.run_uuid) as logger:
            self.logger = logger

            try:
                logger.info(f"Starting ETL job: {processtype}", extra={
                    'stepcounter': 'start',
                    'metadata': {
                        'run_date': str(self.run_date),
                        'dataset_type': self.dataset_type,
                        'data_source': self.data_source,
                        'dry_run': self.dry_run
                    }
                })

                # Create dataset metadata record
                if not self.dry_run:
                    self._create_dataset_record()

                # Run lifecycle hooks
                self.setup()

                step_start = time.time()
                data = self.extract()
                step_runtime = time.time() - step_start
                self.records_extracted = len(data) if data else 0
                logger.info(f"Extraction complete: {self.records_extracted} records", extra={
                    'stepcounter': 'extract',
                    'stepruntime': step_runtime,
                    'metadata': {'records': self.records_extracted}
                })

                step_start = time.time()
                transformed = self.transform(data)
                step_runtime = time.time() - step_start
                self.records_transformed = len(transformed) if transformed else 0
                logger.info(f"Transformation complete: {self.records_transformed} records", extra={
                    'stepcounter': 'transform',
                    'stepruntime': step_runtime,
                    'metadata': {'records': self.records_transformed}
                })

                if not self.dry_run:
                    step_start = time.time()
                    self.load(transformed)
                    step_runtime = time.time() - step_start
                    logger.info(f"Load complete: {self.records_loaded} records", extra={
                        'stepcounter': 'load',
                        'stepruntime': step_runtime,
                        'metadata': {'records': self.records_loaded}
                    })

                    # Update dataset status to Active (completed and ready for use)
                    self._update_dataset_status('Active')
                else:
                    logger.info("Dry run mode - skipping load step", extra={
                        'stepcounter': 'load',
                        'metadata': {'dry_run': True}
                    })

                self.cleanup()

                total_runtime = time.time() - self.start_time
                logger.info(f"ETL job completed successfully", extra={
                    'stepcounter': 'complete',
                    'totalruntime': total_runtime,
                    'metadata': {
                        'extracted': self.records_extracted,
                        'transformed': self.records_transformed,
                        'loaded': self.records_loaded
                    }
                })

                return True

            except Exception as e:
                total_runtime = time.time() - self.start_time if self.start_time else 0
                logger.error(f"ETL job failed: {str(e)}", extra={
                    'stepcounter': 'error',
                    'totalruntime': total_runtime,
                    'metadata': {
                        'error_type': type(e).__name__,
                        'extracted': self.records_extracted,
                        'transformed': self.records_transformed,
                        'loaded': self.records_loaded
                    }
                }, exc_info=True)

                # Update dataset status to Failed
                if not self.dry_run and self.dataset_id:
                    self._update_dataset_status('Failed')

                raise

    def _create_dataset_record(self):
        """Create a record in dba.tdataset using f_dataset_iu function."""
        try:
            # Use custom label if provided, otherwise use default pattern
            label = self.dataset_label or f"{self.dataset_type}_{self.run_date}_{self.run_uuid[:8]}"

            # Call f_dataset_iu function to create dataset
            # Use dict_cursor=False to get tuple results for integer indexing
            with db_transaction(dict_cursor=False) as cursor:
                cursor.execute("""
                    SELECT dba.f_dataset_iu(
                        p_datasetid := NULL,
                        p_datasetdate := %s,
                        p_datasettype := %s,
                        p_datasource := %s,
                        p_label := %s,
                        p_statusname := %s,
                        p_createduser := %s
                    )
                """, (
                    self.run_date,
                    self.dataset_type,
                    self.data_source,
                    label,
                    'New',  # New datasets start with 'New' status
                    self.username
                ))
                self.dataset_id = cursor.fetchone()[0]

            self.logger.info(f"Created dataset record: {self.dataset_id}", extra={
                'stepcounter': 'setup',
                'metadata': {'dataset_id': self.dataset_id, 'label': label}
            })

        except Exception as e:
            self.logger.error(f"Failed to create dataset record: {e}", exc_info=True)
            raise

    def _update_dataset_status(self, status: str):
        """
        Update dataset status using f_dataset_iu function.

        Args:
            status: New status (e.g., 'Active', 'Inactive', 'Failed')
        """
        if not self.dataset_id:
            return

        try:
            # Use custom label if provided, otherwise use default pattern
            label = self.dataset_label or f"{self.dataset_type}_{self.run_date}_{self.run_uuid[:8]}"

            # Call f_dataset_iu to update status
            with db_transaction() as cursor:
                cursor.execute("""
                    SELECT dba.f_dataset_iu(
                        p_datasetid := %s,
                        p_datasetdate := %s,
                        p_datasettype := %s,
                        p_datasource := %s,
                        p_label := %s,
                        p_statusname := %s,
                        p_createduser := %s
                    )
                """, (
                    self.dataset_id,
                    self.run_date,
                    self.dataset_type,
                    self.data_source,
                    label,
                    status,
                    self.username
                ))

            self.logger.info(f"Updated dataset {self.dataset_id} status to '{status}'", extra={
                'metadata': {'dataset_id': self.dataset_id, 'status': status}
            })

        except Exception as e:
            self.logger.error(f"Failed to update dataset status: {e}", exc_info=True)

    # Abstract methods to be implemented by subclasses

    def setup(self):
        """
        Initialize resources (connections, temp files, etc.).

        Override this method to add custom setup logic.
        """
        pass

    @abstractmethod
    def extract(self) -> Any:
        """
        Extract data from source.

        Returns:
            Extracted data (list, dict, DataFrame, etc.)
        """
        pass

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """
        Transform extracted data.

        Args:
            data: Data from extract()

        Returns:
            Transformed data ready for loading
        """
        pass

    @abstractmethod
    def load(self, data: Any):
        """
        Load transformed data to database.

        Args:
            data: Data from transform()

        Should update self.records_loaded with number of records inserted.
        """
        pass

    def cleanup(self):
        """
        Clean up resources.

        Override this method to add custom cleanup logic.
        """
        pass
