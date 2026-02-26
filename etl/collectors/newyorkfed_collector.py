"""
NewYorkFed data collector.

Fetches data from the Federal Reserve Bank of New York Markets API,
applies source-specific transforms, saves JSON to the source directory,
then runs generic_import to load into the database.

Replaces all individual run_newyorkfed_*.py job scripts with a single
config-driven collector.

Usage:
    python etl/collectors/newyorkfed_collector.py --config-id 1
    python etl/collectors/newyorkfed_collector.py --config-id 1 --dry-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from common.db_utils import fetch_dict, db_transaction
from common.logging_utils import get_logger
from etl.clients.newyorkfed_client import NewYorkFedAPIClient

SOURCE_DIR = Path("/app/data/source/newyorkfed")

logger = get_logger('newyorkfed_collector')


# ---------------------------------------------------------------------------
# Shared infrastructure
# ---------------------------------------------------------------------------

def load_config(config_id: int) -> dict:
    """Load import config from timportconfig."""
    rows = fetch_dict(
        "SELECT config_id, config_name, api_base_url, api_endpoint_path, "
        "api_response_root_path, api_response_format, source_directory, file_pattern "
        "FROM dba.timportconfig WHERE config_id = %s AND is_active = TRUE",
        (config_id,)
    )
    if not rows:
        raise ValueError(f"Config ID {config_id} not found or inactive")
    return rows[0]


def save_json(data: list, config: dict) -> Path:
    """Save transformed data as JSON file in source directory."""
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)

    slug = config['config_name'].replace('NewYorkFed_', '').lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"newyorkfed_{slug}_{timestamp}.json"
    filepath = SOURCE_DIR / filename

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved {len(data)} records to {filepath}")
    return filepath


def ensure_source_directory(config_id: int):
    """Update timportconfig.source_directory if not already set."""
    rows = fetch_dict(
        "SELECT source_directory FROM dba.timportconfig WHERE config_id = %s",
        (config_id,)
    )
    if rows and (not rows[0]['source_directory'] or rows[0]['source_directory'].strip() == ''):
        with db_transaction() as cursor:
            cursor.execute(
                "UPDATE dba.timportconfig SET source_directory = %s WHERE config_id = %s",
                (str(SOURCE_DIR), config_id)
            )
        logger.info(f"Updated source_directory to {SOURCE_DIR} for config {config_id}")


def run_generic_import(config_id: int, dry_run: bool) -> bool:
    """Run the generic import for the saved JSON file."""
    from etl.jobs.generic_import import GenericImportJob, ConfigNotFoundError

    try:
        job = GenericImportJob(config_id=config_id, dry_run=dry_run)
    except ConfigNotFoundError as e:
        logger.error(f"Config not found: {e}")
        return False

    print(f"Run UUID: {job.run_uuid}")

    try:
        job.run()
        logger.info(
            f"Import completed: {job.records_loaded} records loaded "
            f"from {len(job.matched_files)} file(s)"
        )
        return True
    except Exception as e:
        logger.error(f"Generic import failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Fetch function (generic — works for all NYF endpoints)
# ---------------------------------------------------------------------------

def fetch_newyorkfed(config: dict) -> list:
    """Fetch data from NewYorkFed API using endpoint config from timportconfig."""
    endpoint_path = config.get('api_endpoint_path')
    if not endpoint_path:
        raise ValueError(f"No api_endpoint_path set for config '{config['config_name']}'")

    response_format = config.get('api_response_format') or 'json'
    response_root_path = config.get('api_response_root_path')
    base_url = config.get('api_base_url') or 'https://markets.newyorkfed.org'

    client = NewYorkFedAPIClient(base_url=base_url)
    try:
        logger.info(f"Fetching {endpoint_path} (root_path={response_root_path})")
        data = client.fetch_endpoint(
            endpoint_path=endpoint_path,
            response_format=response_format,
            response_root_path=response_root_path,
        )
        logger.info(f"Fetched {len(data)} records")
        return data
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Helper: parse YYYY-MM-DD date to ISO string (or None)
# ---------------------------------------------------------------------------

def _parse_date(value: str) -> str | None:
    """Parse YYYY-MM-DD string to ISO date string, or None if empty."""
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d')


def _parse_numeric(value, strip_commas: bool = False) -> float | None:
    """Parse a numeric value, optionally stripping commas."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if strip_commas:
        value = str(value).replace(',', '')
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None


def _audit_cols() -> dict:
    """Return standard audit columns."""
    return {
        'created_date': datetime.now().isoformat(),
        'created_by': 'etl_user',
    }


# ---------------------------------------------------------------------------
# Transform functions
# ---------------------------------------------------------------------------

def transform_reference_rates(data: list) -> list:
    """Transform reference rates (SOFR, EFFR, OBFR, TGCR, BGCR)."""
    transformed = []
    for record in data:
        effective_date = _parse_date(record.get('effectiveDate'))
        if not effective_date:
            logger.warning(f"Missing effectiveDate in record: {record}")
            continue

        transformed.append({
            'rate_type': record.get('type'),
            'effective_date': effective_date,
            'rate_percent': record.get('percentRate'),
            'volume_billions': record.get('volumeInBillions'),
            'percentile_1': record.get('percentile1'),
            'percentile_25': record.get('percentile25'),
            'percentile_75': record.get('percentile75'),
            'percentile_99': record.get('percentile99'),
            'target_range_from': record.get('targetRangeFrom'),
            'target_range_to': record.get('targetRangeTo'),
            **_audit_cols(),
        })

    logger.info(f"Transformed {len(transformed)} reference rate records")
    return transformed


def transform_soma_holdings(data: list) -> list:
    """Transform SOMA monthly Treasury holdings."""
    transformed = []
    for record in data:
        try:
            par_value = _parse_numeric(record.get('parValue', ''), strip_commas=True)
            current_face_value = _parse_numeric(record.get('currentFaceValue', ''), strip_commas=True)

            transformed.append({
                'as_of_date': _parse_date(record.get('asOfDate')),
                'security_type': record.get('securityType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'maturity_date': _parse_date(record.get('maturityDate')),
                'par_value': par_value,
                'current_face_value': current_face_value,
                **_audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform SOMA record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} SOMA holdings records")
    return transformed


def transform_repo_operations(data: list) -> list:
    """Transform repo / reverse repo operations."""
    transformed = []
    for record in data:
        try:
            operation_type_raw = record.get('operationType', '').lower().replace(' ', '')

            transformed.append({
                'operation_date': _parse_date(record.get('operationDate')),
                'operation_type': operation_type_raw,
                'operation_id': record.get('operationId'),
                'maturity_date': _parse_date(record.get('maturityDate')),
                'term_days': record.get('termCalenderDays'),  # API typo: "Calender"
                'operation_status': record.get('auctionStatus'),
                'amount_submitted': record.get('totalAmtSubmitted'),
                'amount_accepted': record.get('totalAmtAccepted'),
                'award_rate': None,
                **_audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform repo record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} repo operation records")
    return transformed


def transform_agency_mbs(data: list) -> list:
    """Transform Agency MBS operation announcements."""
    transformed = []
    for record in data:
        try:
            transformed.append({
                'operation_date': _parse_date(record.get('operationDate')),
                'operation_type': record.get('operationType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'settlement_date': _parse_date(record.get('settlementDate')),
                'maturity_date': _parse_date(record.get('maturityDate')),
                'operation_amount': record.get('operationAmount'),
                'total_accepted': record.get('totalAmtAccepted'),
                **_audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform Agency MBS record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} Agency MBS records")
    return transformed


def transform_fx_swaps(data: list) -> list:
    """Transform FX swap operations with term_days calculation."""
    transformed = []
    for record in data:
        try:
            swap_date_str = record.get('swapDate') or record.get('operationDate')
            swap_date = _parse_date(swap_date_str)
            maturity_date = _parse_date(record.get('maturityDate'))

            # Calculate term days if both dates available
            term_days = None
            if swap_date and maturity_date:
                sd = datetime.strptime(swap_date, '%Y-%m-%d')
                md = datetime.strptime(maturity_date, '%Y-%m-%d')
                term_days = (md - sd).days

            transformed.append({
                'swap_date': swap_date,
                'counterparty': record.get('counterparty'),
                'currency_code': record.get('currencyCode') or record.get('currency'),
                'maturity_date': maturity_date,
                'term_days': term_days,
                'usd_amount': record.get('usdAmount'),
                'foreign_currency_amount': record.get('foreignCurrencyAmount'),
                'exchange_rate': record.get('exchangeRate'),
                **_audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform FX swap record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} FX swap records")
    return transformed


def transform_counterparties(data: list) -> list:
    """Transform FX swap counterparties list."""
    transformed = []
    for record in data:
        counterparty_name = record.get('counterparty_name')
        if not counterparty_name:
            logger.warning(f"Skipping record with no counterparty name: {record}")
            continue

        transformed.append({
            'counterparty_name': counterparty_name,
            'counterparty_type': 'Central Bank',
            'is_active': True,
            **_audit_cols(),
        })

    logger.info(f"Transformed {len(transformed)} counterparty records")
    return transformed


def transform_securities_lending(data: list) -> list:
    """Transform securities lending operations with term_days calculation."""
    transformed = []
    for record in data:
        try:
            loan_date = _parse_date(record.get('loanDate'))
            return_date = _parse_date(record.get('returnDate'))

            # Calculate term days if both dates available
            term_days = None
            if loan_date and return_date:
                ld = datetime.strptime(loan_date, '%Y-%m-%d')
                rd = datetime.strptime(return_date, '%Y-%m-%d')
                term_days = (rd - ld).days

            transformed.append({
                'operation_date': _parse_date(record.get('operationDate')),
                'operation_type': record.get('operationType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'loan_date': loan_date,
                'return_date': return_date,
                'term_days': term_days,
                'par_amount': record.get('totalParAmtAccepted') or record.get('parAmount'),
                'fee_rate': record.get('feeRate'),
                'operation_status': record.get('operationStatus'),
                **_audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform securities lending record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} securities lending records")
    return transformed


def transform_guide_sheets(data: list) -> list:
    """Transform guide sheets with nested array extraction."""
    transformed = []

    if not data:
        logger.warning("No guide sheet data to transform")
        return transformed

    si_object = data[0]

    publication_date_str = si_object.get('reportWeeksFromDate')
    if not publication_date_str:
        logger.error("No reportWeeksFromDate found in SI object")
        return transformed

    publication_date = _parse_date(publication_date_str)
    guide_type = si_object.get('title', 'SI')

    details = si_object.get('details', [])
    for record in details:
        try:
            transformed.append({
                'publication_date': publication_date,
                'guide_type': guide_type,
                'security_type': record.get('secType'),
                'cusip': record.get('cusip'),
                'issue_date': _parse_date(record.get('issueDate')),
                'maturity_date': _parse_date(record.get('maturityDate')),
                'coupon_rate': record.get('percentCouponRate'),
                'settlement_price': record.get('settlementPrice'),
                'accrued_interest': record.get('accruedInterest'),
                **_audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform guide sheet record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} guide sheet records")
    return transformed


def transform_treasury_operations(data: list) -> list:
    """Transform Treasury securities operations."""
    transformed = []
    for record in data:
        try:
            transformed.append({
                'operation_date': _parse_date(record.get('operationDate')),
                'operation_type': record.get('operationType'),
                'cusip': record.get('cusip'),
                'security_description': record.get('securityDescription'),
                'issue_date': _parse_date(record.get('issueDate')),
                'maturity_date': _parse_date(record.get('maturityDate')),
                'coupon_rate': record.get('couponRate'),
                'security_term': record.get('securityTerm'),
                'operation_amount': record.get('operationAmount'),
                'total_submitted': record.get('totalAmtSubmitted'),
                'total_accepted': record.get('totalAmtAccepted'),
                'high_price': record.get('highPrice'),
                'low_price': record.get('lowPrice'),
                'stop_out_rate': record.get('stopOutRate'),
                **_audit_cols(),
            })
        except Exception as e:
            logger.error(f"Failed to transform Treasury record: {e}")
            continue

    logger.info(f"Transformed {len(transformed)} Treasury operation records")
    return transformed


def transform_passthrough(data: list) -> list:
    """No transform — pass data through as-is (PD Statistics, Market Share)."""
    logger.info(f"Passthrough: {len(data)} records (no transform)")
    return data


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

COLLECTORS = {
    'NewYorkFed_ReferenceRates_Latest':  {'fetch': fetch_newyorkfed, 'transform': transform_reference_rates},
    'NewYorkFed_ReferenceRates_Search':  {'fetch': fetch_newyorkfed, 'transform': transform_reference_rates},
    'NewYorkFed_SOMA_Holdings':          {'fetch': fetch_newyorkfed, 'transform': transform_soma_holdings},
    'NewYorkFed_Repo_Operations':        {'fetch': fetch_newyorkfed, 'transform': transform_repo_operations},
    'NewYorkFed_ReverseRepo_Operations': {'fetch': fetch_newyorkfed, 'transform': transform_repo_operations},
    'NewYorkFed_Agency_MBS':             {'fetch': fetch_newyorkfed, 'transform': transform_agency_mbs},
    'NewYorkFed_FX_Swaps':               {'fetch': fetch_newyorkfed, 'transform': transform_fx_swaps},
    'NewYorkFed_Counterparties':         {'fetch': fetch_newyorkfed, 'transform': transform_counterparties},
    'NewYorkFed_Securities_Lending':     {'fetch': fetch_newyorkfed, 'transform': transform_securities_lending},
    'NewYorkFed_Guide_Sheets':           {'fetch': fetch_newyorkfed, 'transform': transform_guide_sheets},
    'NewYorkFed_Treasury_Operations':    {'fetch': fetch_newyorkfed, 'transform': transform_treasury_operations},
    'NewYorkFed_PD_Statistics':          {'fetch': fetch_newyorkfed, 'transform': transform_passthrough},
    'NewYorkFed_Market_Share':           {'fetch': fetch_newyorkfed, 'transform': transform_passthrough},
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Fetch NewYorkFed API data, transform, and import via generic import'
    )
    parser.add_argument('--config-id', type=int, required=True, help='Config ID from dba.timportconfig')
    parser.add_argument('--dry-run', action='store_true', help='Fetch and save but do not load to database')
    args = parser.parse_args()

    if not os.getenv('DB_URL'):
        print("ERROR: DB_URL environment variable not set")
        return 1

    try:
        # 1. Load config
        config = load_config(args.config_id)
        config_name = config['config_name']
        logger.info(f"Loaded config: {config_name} (id={args.config_id})")

        # 2. Lookup collector
        collector = COLLECTORS.get(config_name)
        if not collector:
            logger.error(f"No collector registered for config '{config_name}'")
            print(f"ERROR: No collector registered for config '{config_name}'")
            print(f"Available collectors: {', '.join(COLLECTORS.keys())}")
            return 1

        # 3. Fetch data from API
        raw_data = collector['fetch'](config)
        if not raw_data:
            logger.warning("No data returned from API")
            print("No data returned from API")
            return 0

        # 4. Transform
        transformed = collector['transform'](raw_data)
        if not transformed:
            logger.warning("No records after transform")
            print("No records after transform")
            return 0

        # 5. Save JSON to source directory
        filepath = save_json(transformed, config)
        print(f"Saved {len(transformed)} records to {filepath}")

        # 6. Ensure source_directory is set in config
        ensure_source_directory(args.config_id)

        # 7. Run generic import
        success = run_generic_import(args.config_id, args.dry_run)
        if success:
            print(f"Import completed successfully for config {args.config_id}")
            return 0
        else:
            print(f"Import failed for config {args.config_id}")
            return 1

    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        print(f"ERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
