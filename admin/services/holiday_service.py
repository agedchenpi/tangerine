"""
Service for managing holiday records in dba.tholidays.

Holidays are used for business day calculations throughout the ETL pipeline.
"""
from datetime import date, datetime
from common.db_utils import db_transaction


def get_all_holidays() -> list[dict]:
    """Return all holidays ordered by date descending."""
    with db_transaction() as cursor:
        cursor.execute("""
            SELECT holiday_date, holiday_name, createddate, createdby
            FROM dba.tholidays
            ORDER BY holiday_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def get_holiday_by_date(holiday_date: date) -> dict | None:
    """Return single holiday by date or None if not found."""
    with db_transaction() as cursor:
        cursor.execute(
            "SELECT holiday_date, holiday_name, createddate, createdby FROM dba.tholidays WHERE holiday_date = %s",
            (holiday_date,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def create_holiday(holiday_date: date, holiday_name: str = None) -> bool:
    """Create a holiday record. Returns True if created successfully."""
    with db_transaction() as cursor:
        cursor.execute("""
            INSERT INTO dba.tholidays (holiday_date, holiday_name)
            VALUES (%s, %s)
        """, (holiday_date, holiday_name))
        return cursor.rowcount > 0


def update_holiday(holiday_date: date, holiday_name: str = None) -> bool:
    """Update holiday name. Returns True if updated."""
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE dba.tholidays
            SET holiday_name = %s
            WHERE holiday_date = %s
        """, (holiday_name, holiday_date))
        return cursor.rowcount > 0


def delete_holiday(holiday_date: date) -> bool:
    """Delete a holiday. Returns True if deleted."""
    with db_transaction() as cursor:
        cursor.execute(
            "DELETE FROM dba.tholidays WHERE holiday_date = %s",
            (holiday_date,)
        )
        return cursor.rowcount > 0


def holiday_exists(holiday_date: date) -> bool:
    """Check if a holiday already exists for the given date."""
    with db_transaction() as cursor:
        cursor.execute(
            "SELECT 1 FROM dba.tholidays WHERE holiday_date = %s",
            (holiday_date,)
        )
        return cursor.fetchone() is not None


def bulk_create_holidays(holidays: list[dict]) -> tuple[int, list[str]]:
    """
    Bulk insert holidays from a list of dicts.

    Args:
        holidays: List of dicts with 'holiday_date' and optional 'holiday_name'

    Returns:
        Tuple of (success_count, error_messages)
    """
    success_count = 0
    errors = []

    with db_transaction() as cursor:
        for holiday in holidays:
            try:
                holiday_date = holiday.get('holiday_date')
                holiday_name = holiday.get('holiday_name')

                # Validate date
                if not holiday_date:
                    errors.append("Missing holiday_date")
                    continue

                # Convert string to date if needed
                if isinstance(holiday_date, str):
                    holiday_date = datetime.strptime(holiday_date, "%Y-%m-%d").date()

                # Skip if already exists
                if holiday_exists(holiday_date):
                    errors.append(f"Holiday on {holiday_date} already exists")
                    continue

                # Insert
                cursor.execute("""
                    INSERT INTO dba.tholidays (holiday_date, holiday_name)
                    VALUES (%s, %s)
                """, (holiday_date, holiday_name))

                success_count += 1

            except Exception as e:
                errors.append(f"Error importing {holiday.get('holiday_date', 'unknown')}: {str(e)}")

    return success_count, errors


def get_holiday_stats() -> dict:
    """Return statistics about holidays."""
    with db_transaction() as cursor:
        # Total holidays
        cursor.execute("SELECT COUNT(*) as total FROM dba.tholidays")
        total = cursor.fetchone()['total']

        # Upcoming holidays (future dates)
        cursor.execute("""
            SELECT COUNT(*) as upcoming
            FROM dba.tholidays
            WHERE holiday_date >= CURRENT_DATE
        """)
        upcoming = cursor.fetchone()['upcoming']

        # Past holidays
        cursor.execute("""
            SELECT COUNT(*) as past
            FROM dba.tholidays
            WHERE holiday_date < CURRENT_DATE
        """)
        past = cursor.fetchone()['past']

        return {
            'total': total,
            'upcoming': upcoming,
            'past': past
        }


def get_upcoming_holidays(limit: int = 10) -> list[dict]:
    """Return next N upcoming holidays."""
    with db_transaction() as cursor:
        cursor.execute("""
            SELECT holiday_date, holiday_name
            FROM dba.tholidays
            WHERE holiday_date >= CURRENT_DATE
            ORDER BY holiday_date ASC
            LIMIT %s
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
