#!/bin/bash
set -e

# Start cron daemon
service cron start

# Generate and apply crontab from database scheduler config
python /app/etl/jobs/generate_crontab.py --apply --update-next-run || echo "Warning: crontab generation failed, will retry manually"

# Keep container running
exec tail -f /dev/null
