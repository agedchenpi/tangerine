"""
Pub-Sub Event System for Tangerine ETL.

This service:
- Watches for file system events (new files in source directories)
- Polls the database for pending events
- Dispatches events to registered subscribers
- Triggers appropriate jobs based on event type
"""
