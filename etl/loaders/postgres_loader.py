"""PostgreSQL data loader with bulk insert support."""

from typing import List, Dict, Any, Tuple
from common.db_utils import bulk_insert, db_transaction
from common.logging_utils import get_logger


class PostgresLoader:
    """
    Loader for PostgreSQL database with optimized bulk insert.

    Features:
    - Bulk insert using execute_values
    - Transaction management
    - Upsert support (INSERT ... ON CONFLICT)
    - Automatic schema handling
    """

    def __init__(self, schema: str = "feeds"):
        """
        Initialize loader.

        Args:
            schema: Database schema name (default: feeds)
        """
        self.schema = schema
        self.logger = get_logger(self.__class__.__name__)

    def load(
        self,
        table: str,
        data: List[Dict[str, Any]],
        dataset_id: int,
        columns: List[str] = None
    ) -> int:
        """
        Load data into table using bulk insert with datasetid.

        Args:
            table: Table name
            data: List of dictionaries to insert
            dataset_id: Dataset ID from dba.tdataset to link this data to
            columns: Column names (inferred from first record if not provided)

        Returns:
            Number of rows inserted
        """
        if not data:
            self.logger.warning(f"No data to load into {self.schema}.{table}")
            return 0

        # Add datasetid to each record
        data_with_dataset = [
            {**record, 'datasetid': dataset_id}
            for record in data
        ]

        # Infer columns from first record if not provided
        if columns is None:
            columns = list(data_with_dataset[0].keys())
        else:
            # Ensure datasetid is in columns
            if 'datasetid' not in columns:
                columns = ['datasetid'] + columns

        # Convert dicts to tuples in correct column order
        values = [
            tuple(record.get(col) for col in columns)
            for record in data_with_dataset
        ]

        rows_inserted = bulk_insert(
            table=table,
            columns=columns,
            values=values,
            schema=self.schema
        )

        self.logger.info(f"Loaded {rows_inserted} rows into {self.schema}.{table} (dataset_id={dataset_id})")
        return rows_inserted

    def upsert(
        self,
        table: str,
        data: List[Dict[str, Any]],
        conflict_columns: List[str],
        update_columns: List[str] = None
    ) -> int:
        """
        Upsert data (INSERT ... ON CONFLICT ... DO UPDATE).

        Args:
            table: Table name
            data: List of dictionaries to upsert
            conflict_columns: Columns that define uniqueness constraint
            update_columns: Columns to update on conflict (all except conflict if None)

        Returns:
            Number of rows affected
        """
        if not data:
            return 0

        columns = list(data[0].keys())

        # Determine update columns
        if update_columns is None:
            update_columns = [col for col in columns if col not in conflict_columns]

        # Build upsert query
        placeholders = ', '.join(['%s'] * len(columns))
        conflict_clause = ', '.join(conflict_columns)
        update_clause = ', '.join([
            f"{col} = EXCLUDED.{col}" for col in update_columns
        ])

        query = f"""
            INSERT INTO {self.schema}.{table} ({', '.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_clause})
            DO UPDATE SET {update_clause}
        """

        # Convert to tuples
        values = [tuple(record.get(col) for col in columns) for record in data]

        # Execute
        with db_transaction() as cursor:
            cursor.executemany(query, values)
            rows_affected = cursor.rowcount

        self.logger.info(f"Upserted {rows_affected} rows into {self.schema}.{table}")
        return rows_affected

    def truncate(self, table: str):
        """
        Truncate table.

        Args:
            table: Table name
        """
        with db_transaction() as cursor:
            cursor.execute(f"TRUNCATE TABLE {self.schema}.{table}")

        self.logger.info(f"Truncated table {self.schema}.{table}")
