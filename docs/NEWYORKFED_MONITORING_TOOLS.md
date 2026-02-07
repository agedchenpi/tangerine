# NewYorkFed Monitoring and Testing Tools

**Created:** 2026-02-06
**Purpose:** Scripts for monitoring API availability, testing table retention, and generating status reports

---

## Available Scripts

### 1. API Availability Monitor

**File:** `scripts/monitor_newyorkfed_apis.py`

**Purpose:** Check all NewYorkFed API endpoints to determine which have data available

**Features:**
- Tests all 9 API endpoints
- Shows response times
- Identifies which APIs have data vs. empty arrays
- Tracks errors and connectivity issues

**Usage:**
```bash
# Human-readable output
python scripts/monitor_newyorkfed_apis.py

# JSON output
python scripts/monitor_newyorkfed_apis.py --json

# Save to file
python scripts/monitor_newyorkfed_apis.py --json --output report.json
```

**Output Example:**
```
NewYorkFed API Availability Report
================================================================================
Checked at: 2026-02-06 23:30:00 UTC

Summary:
  ✅ APIs with data:        6
  ⏳ APIs without data:     2
  ❌ APIs with errors:      0
  🚧 Not implemented:       1
  📊 Total endpoints:       9

Detailed Results:
--------------------------------------------------------------------------------

✅ Reference Rates
   Table: newyorkfed_reference_rates
   Endpoint: /api/rates/all/latest.json
   Status: Data available
   Records: 6
   Response time: 245ms
```

**Use Cases:**
- Daily monitoring to detect when APIs start/stop providing data
- Debugging API connectivity issues
- Alerting when previously empty APIs get data

---

### 2. Table Retention Test

**File:** `scripts/test_newyorkfed_table_retention.py`

**Purpose:** Verify that all NewYorkFed tables can properly accept and retain records

**Features:**
- Inserts test data into each table
- Verifies foreign key constraints work
- Verifies indexes are functional
- Verifies audit columns auto-populate
- Cleans up test data after verification

**Usage:**
```bash
# Run tests and cleanup
python scripts/test_newyorkfed_table_retention.py

# Keep test data for inspection
python scripts/test_newyorkfed_table_retention.py --keep-test-data
```

**Output Example:**
```
Testing NewYorkFed table data retention...
================================================================================

Testing: newyorkfed_agency_mbs
  ✅ SUCCESS: Inserted and verified 1 records

Testing: newyorkfed_fx_swaps
  ✅ SUCCESS: Inserted and verified 1 records

Testing: newyorkfed_counterparties
  ✅ SUCCESS: Inserted and verified 1 records

--------------------------------------------------------------------------------
Cleaning up test data...
  🧹 Cleaned up 1 test records from newyorkfed_agency_mbs
  🧹 Cleaned up 1 test records from newyorkfed_fx_swaps

================================================================================
NewYorkFed Table Retention Test Summary
================================================================================

✅ Successful:  9/9
⚠️  Partial:     0/9
❌ Errors:      0/9

🎉 All tables can properly retain records!
```

**Use Cases:**
- Verify table schemas are correct before production use
- Diagnose why a table might not be accepting records
- Confirm database migrations completed successfully

---

### 3. Comprehensive Status Report

**File:** `scripts/newyorkfed_api_status_report.py`

**Purpose:** Generate comprehensive reports showing API status, database records, and data freshness

**Features:**
- Queries all 9 API endpoints
- Queries all 9 database tables
- Compares API vs. database records
- Shows data freshness metrics
- Identifies discrepancies
- Multiple output formats (text, JSON, HTML)

**Usage:**
```bash
# Text report (human-readable)
python scripts/newyorkfed_api_status_report.py

# JSON report
python scripts/newyorkfed_api_status_report.py --format json

# HTML report
python scripts/newyorkfed_api_status_report.py --format html --output report.html
```

**Output Example (Text):**
```
================================================================================
NewYorkFed Feeds Status Report
================================================================================
Generated: 2026-02-06 23:35:00 UTC

Summary:
  ✅ Healthy (data in DB + API):      6
  ⏳ Waiting for data:                2
  📦 Stale (data in DB, not API):     0
  🔄 Needs sync (data in API not DB): 1
  ⚫ No data anywhere:                0
  🚧 Not implemented:                 0

Detailed Status:
--------------------------------------------------------------------------------

✅ Reference Rates
   Table: feeds.newyorkfed_reference_rates
   Status: active
   Database:
     Records: 36
     Date range: 2026-02-04 to 2026-02-06
     Last updated: 2026-02-06 10:30:45
     Size: 0.02 MB
   API:
     Records available: 6
     Status: ✅ Has data

⏳ Agency MBS
   Table: feeds.newyorkfed_agency_mbs
   Status: waiting
   Database:
     Records: 0
   API:
     Records available: 0
     Status: ⚫ No data
```

**Output Example (HTML):**
Generates a styled HTML page with:
- Summary cards showing key metrics
- Table with all feed details
- Color-coded health status
- Sortable columns
- Responsive design

**Use Cases:**
- Weekly status reports to stakeholders
- Dashboard monitoring (refresh HTML report)
- Debugging data pipeline issues
- Capacity planning (table sizes)

---

## Monitoring Workflow

### Daily Monitoring

```bash
# Check API availability
python scripts/monitor_newyorkfed_apis.py --json --output /tmp/api_status.json

# Parse results and alert if changes detected
# (e.g., if agency_mbs API starts returning data)
```

### Weekly Health Check

```bash
# Generate comprehensive status report
python scripts/newyorkfed_api_status_report.py --format html --output /var/www/reports/newyorkfed_status.html

# Email report to team or serve via web server
```

### Pre-Production Testing

```bash
# Verify all tables can retain data
python scripts/test_newyorkfed_table_retention.py

# Verify all jobs can run
python scripts/run_all_newyorkfed_jobs.py --dry-run
```

---

## Integration Ideas

### Airflow DAG

```python
from airflow import DAG
from airflow.operators.bash_operator import BashOperator

dag = DAG('newyorkfed_monitoring', schedule_interval='@daily')

monitor_apis = BashOperator(
    task_id='monitor_apis',
    bash_command='python /opt/tangerine/scripts/monitor_newyorkfed_apis.py --json',
    dag=dag
)

generate_report = BashOperator(
    task_id='generate_report',
    bash_command='python /opt/tangerine/scripts/newyorkfed_api_status_report.py --format html --output /reports/status.html',
    dag=dag
)

monitor_apis >> generate_report
```

### Cron Job

```bash
# Daily API monitoring at 8 AM
0 8 * * * cd /opt/tangerine && python scripts/monitor_newyorkfed_apis.py --json --output /var/log/newyorkfed_api_$(date +\%Y\%m\%d).json

# Weekly status report on Mondays at 9 AM
0 9 * * 1 cd /opt/tangerine && python scripts/newyorkfed_api_status_report.py --format html --output /var/www/html/newyorkfed_status.html
```

### Slack/Email Alerts

```python
import json
import subprocess

# Run API monitor
result = subprocess.run(
    ['python', 'scripts/monitor_newyorkfed_apis.py', '--json'],
    capture_output=True, text=True
)

data = json.loads(result.stdout)

# Alert if previously empty API now has data
for endpoint in data['endpoints']:
    if endpoint['name'] in ['Agency MBS', 'FX Swaps']:
        if endpoint['has_data']:
            send_slack_message(f"🎉 {endpoint['name']} API now has data!")
```

---

## Summary

These tools provide comprehensive monitoring and testing capabilities for the NewYorkFed feeds:

1. **API Monitor** - Real-time API availability and data presence
2. **Retention Test** - Verify database schemas accept records
3. **Status Report** - Comprehensive health dashboard

**All scripts are production-ready and can be scheduled for automated monitoring.**
