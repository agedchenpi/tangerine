# Pub/Sub Event System Codemap

## Purpose

Event-driven architecture for triggering actions when files arrive, imports complete, or reports are sent. Enables loosely-coupled automation between ETL components.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Event Sources                                │
├─────────────────────────────────────────────────────────────────┤
│  FileWatcher        → 'file_received' events                    │
│  GenericImportJob   → 'import_complete' events                  │
│  ReportGenerator    → 'report_sent' events                      │
│  InboxProcessor     → 'email_received' events                   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 dba.tpubsub_events (Queue)                       │
│  event_id, event_type, event_source, event_data, status         │
│  priority, created_at, processed_at, completed_at               │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               PubSubListener (pubsub/listener.py)                │
│  - DatabasePoller: Polls for pending events                      │
│  - FileWatcher: Monitors directories for new files               │
│  - JobHandler: Dispatches to appropriate handler                 │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│               dba.tpubsub_subscribers (Handlers)                 │
│  subscriber_name, event_type, event_filter                       │
│  job_type, config_id, script_path                                │
└─────────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `pubsub/listener.py` | Main daemon entry point |
| `pubsub/watchers/file_watcher.py` | Directory monitoring |
| `pubsub/watchers/db_poller.py` | Event queue polling |
| `pubsub/handlers/job_handler.py` | Event dispatch logic |
| `admin/services/pubsub_service.py` | Event/subscriber CRUD |
| `admin/pages/8_Event_System.py` | Admin UI page |

## Event Types

| Event Type | Source | Trigger |
|------------|--------|---------|
| `file_received` | FileWatcher | New file in watched directory |
| `email_received` | InboxProcessor | Email attachment downloaded |
| `import_complete` | GenericImportJob | Import finished successfully |
| `report_sent` | ReportGenerator | Report email sent |
| `custom` | Manual/Script | User-defined events |

## Event Lifecycle

```
pending → processing → completed
                    ↘ failed (with retry_count)
```

Status transitions:
1. Event created with status `pending`
2. Listener picks up event, sets status `processing`, sets `processed_at`
3. Handler executes
4. On success: status `completed`, sets `completed_at`
5. On failure: status `failed`, sets `error_message`, increments `retry_count`

## Subscriber Configuration

```python
# dba.tpubsub_subscribers fields
subscriber_name: str      # Unique identifier
event_type: str           # Event to subscribe to
event_filter: Dict        # Optional JSON filter (e.g., {"source": "sales*"})
job_type: str             # import, inbox_processor, report, custom
config_id: int            # FK to config table for job_type
script_path: str          # For custom handlers
is_active: bool           # Enable/disable
```

Job types and their config tables:
- `import` → `dba.timportconfig.config_id`
- `inbox_processor` → `dba.tinboxconfig.inbox_config_id`
- `report` → `dba.treportmanager.report_id`
- `custom` → Uses `script_path` instead

## PubSubListener Daemon

```python
# Main components
class PubSubListener:
    def __init__(self, poll_interval=5, watch_directories=['/app/data/source']):
        self.file_watcher = FileWatcher(...)  # Directory monitoring
        self.db_poller = DatabasePoller(...)  # Event queue polling
        self.job_handler = JobHandler()       # Event dispatch

    def start(self):
        self.file_watcher.start()  # Background thread
        self.db_poller.start()     # Background thread

    def stop(self):
        # Graceful shutdown
```

Run as Docker service:
```yaml
# docker-compose.yml
pubsub:
  build:
    context: .
    dockerfile: Dockerfile.pubsub
  command: python pubsub/listener.py
  volumes:
    - ./.data/etl:/app/data
```

## Creating Events (Service Layer)

```python
from admin.services.pubsub_service import create_event

# Create an event
event_id = create_event(
    event_type='import_complete',
    event_source='generic_import:42',
    event_data={
        'config_id': 42,
        'records_loaded': 1500,
        'run_uuid': 'abc123'
    },
    priority=5  # 1-10, default 5
)
```

## Event Filters

Subscribers can filter events by JSON conditions in `event_filter`:

```json
{
    "event_data.config_name": "sales_*",
    "event_data.records_loaded": {"$gt": 0}
}
```

## Admin UI (8_Event_System.py)

Four tabs:
1. **Event Queue**: View pending/processing events, cancel, retry
2. **Subscribers**: CRUD for event subscribers
3. **Event Log**: Historical event tracking
4. **Service Status**: Monitor pubsub daemon health

## Testing Events

```bash
# Start listener manually
docker compose exec pubsub python pubsub/listener.py --poll-interval 5

# Check status
docker compose logs -f pubsub

# Insert test event
docker compose exec tangerine python -c "
from admin.services.pubsub_service import create_event
create_event('test_event', 'manual', {'test': True})
"
```

## Integration with ETL Jobs

Events are emitted at job completion:

```python
# In generic_import.py
from admin.services.pubsub_service import create_event

# After successful load
create_event(
    event_type='import_complete',
    event_source=f'generic_import:{config_id}',
    event_data={
        'config_id': config_id,
        'config_name': config.config_name,
        'records_loaded': records_loaded,
        'run_uuid': run_uuid,
        'dataset_id': dataset_id
    }
)
```

This allows subscribers to trigger follow-up actions automatically.
