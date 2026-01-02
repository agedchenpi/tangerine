"""
Example ETL job demonstrating the complete framework.

This job shows how to:
- Inherit from BaseETLJob
- Use extractors, transformers, and loaders
- Handle logging and dataset tracking
- Process data from API to database
"""

from datetime import date, datetime
from typing import List, Dict, Any

from etl.base.etl_job import BaseETLJob
from etl.extractors.base_extractor import BaseExtractor
from etl.transformers.base_transformer import BaseTransformer
from etl.loaders.postgres_loader import PostgresLoader


class MockExtractor(BaseExtractor):
    """
    Mock extractor for demonstration purposes.

    In a real job, replace this with an actual API extractor.
    """

    def extract(self) -> List[Dict[str, Any]]:
        """Extract mock data."""
        # Simulate API data
        return [
            {
                'id': 1,
                'name': 'Product A',
                'price': '19.99',
                'quantity': '100',
                'status': 'active',
                'created_at': '2026-01-01T10:00:00Z'
            },
            {
                'id': 2,
                'name': 'Product B',
                'price': '29.99',
                'quantity': '50',
                'status': 'active',
                'created_at': '2026-01-01T11:00:00Z'
            },
            {
                'id': 3,
                'name': 'Product C',
                'price': '39.99',
                'quantity': '0',
                'status': 'inactive',
                'created_at': '2026-01-01T12:00:00Z'
            }
        ]


class ExampleTransformer(BaseTransformer):
    """
    Example transformer demonstrating common transformations.
    """

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform extracted data.

        Transformations:
        1. Field mapping (rename fields)
        2. Type conversions
        3. Filter inactive records
        4. Add audit fields
        """
        # Step 1: Map fields to match database schema
        field_map = {
            'id': 'product_id',
            'name': 'product_name',
            'price': 'unit_price',
            'quantity': 'stock_quantity',
            'status': 'product_status',
            'created_at': 'source_created_at'
        }
        data = self.apply_field_mapping(data, field_map)

        # Step 2: Convert types
        type_map = {
            'unit_price': float,
            'stock_quantity': int,
            'source_created_at': lambda x: datetime.fromisoformat(x.replace('Z', '+00:00'))
        }
        data = self.apply_type_conversion(data, type_map)

        # Step 3: Filter out inactive records
        data = self.filter_records(data, lambda r: r.get('product_status') == 'active')

        # Step 4: Add audit fields
        data = self.add_audit_fields(data, username='etl_user')

        return data


class ExampleETLJob(BaseETLJob):
    """
    Example ETL job that demonstrates the complete framework.

    This job:
    1. Extracts data from a mock API (replace with real API)
    2. Transforms the data (type conversion, filtering, field mapping)
    3. Loads into feeds.example_products table
    4. Logs to database and files
    5. Tracks dataset metadata

    Usage:
        job = ExampleETLJob(
            run_date=date.today(),
            dataset_type='Example',
            data_source='ExampleAPI'
        )
        job.run()
    """

    def __init__(
        self,
        run_date: date,
        dataset_type: str = 'Example',
        data_source: str = 'ExampleAPI',
        **kwargs
    ):
        """
        Initialize example ETL job.

        Args:
            run_date: Date for this run
            dataset_type: Dataset type (default: Example)
            data_source: Data source (default: ExampleAPI)
            **kwargs: Additional arguments passed to BaseETLJob
        """
        super().__init__(
            run_date=run_date,
            dataset_type=dataset_type,
            data_source=data_source,
            **kwargs
        )

        self.extractor = MockExtractor()
        self.transformer = ExampleTransformer()
        self.loader = PostgresLoader(schema='feeds')

    def setup(self):
        """Set up resources (create table if needed)."""
        # In a real job, you might create the target table here if it doesn't exist
        # For now, we'll assume feeds.example_products exists
        self.logger.info("Setup complete - ready to extract data")

    def extract(self) -> List[Dict[str, Any]]:
        """
        Extract data from source.

        Returns:
            Raw extracted data
        """
        self.logger.info("Starting extraction from mock API", extra={'stepcounter': 'extract_start'})

        data = self.extractor.extract()

        self.logger.info(
            f"Extraction complete - retrieved {len(data)} records",
            extra={'stepcounter': 'extract_complete', 'metadata': {'record_count': len(data)}}
        )

        return data

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform extracted data.

        Args:
            data: Raw data from extract()

        Returns:
            Transformed data ready for loading
        """
        self.logger.info(
            f"Starting transformation on {len(data)} records",
            extra={'stepcounter': 'transform_start'}
        )

        transformed = self.transformer.transform(data)

        self.logger.info(
            f"Transformation complete - {len(transformed)} records after filtering",
            extra={
                'stepcounter': 'transform_complete',
                'metadata': {
                    'input_records': len(data),
                    'output_records': len(transformed),
                    'filtered_records': len(data) - len(transformed)
                }
            }
        )

        return transformed

    def load(self, data: List[Dict[str, Any]]):
        """
        Load transformed data to database.

        Args:
            data: Transformed data from transform()
        """
        if not data:
            self.logger.warning("No data to load - skipping load step")
            self.records_loaded = 0
            return

        self.logger.info(
            f"Starting load of {len(data)} records to dataset {self.dataset_id}",
            extra={'stepcounter': 'load_start'}
        )

        # Note: This requires feeds.example_products table to exist
        # See schema/feeds/tables/example_products.sql
        try:
            self.records_loaded = self.loader.load(
                table='example_products',
                data=data,
                dataset_id=self.dataset_id  # Link records to this dataset
            )

            self.logger.info(
                f"Load complete - inserted {self.records_loaded} records into dataset {self.dataset_id}",
                extra={
                    'stepcounter': 'load_complete',
                    'metadata': {
                        'records_loaded': self.records_loaded,
                        'dataset_id': self.dataset_id
                    }
                }
            )
        except Exception as e:
            self.logger.error(f"Load failed: {e}", exc_info=True)
            raise

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleanup complete")


if __name__ == "__main__":
    """Run the example ETL job."""
    import os

    # Ensure environment is configured
    if not os.getenv('DB_URL'):
        print("ERROR: DB_URL environment variable not set")
        exit(1)

    # Create and run job
    job = ExampleETLJob(
        run_date=date.today(),
        dry_run=False  # Set to True to test without loading to DB
    )

    try:
        success = job.run()
        if success:
            print(f"\n✓ ETL job completed successfully")
            print(f"  - Extracted: {job.records_extracted} records")
            print(f"  - Transformed: {job.records_transformed} records")
            print(f"  - Loaded: {job.records_loaded} records")
            print(f"  - Run UUID: {job.run_uuid}")
            print(f"  - Dataset ID: {job.dataset_id}")
        else:
            print("\n✗ ETL job failed")
            exit(1)
    except Exception as e:
        print(f"\n✗ ETL job failed with error: {e}")
        exit(1)
