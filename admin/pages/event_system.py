"""Event System Management Page"""

import streamlit as st
import pandas as pd
import json
from typing import Optional, Dict, Any

from components.notifications import show_success, show_error, show_warning, show_info
from components.validators import validate_required, validate_config_name
from services.pubsub_service import (
    list_events, get_event, create_event, update_event_status,
    cancel_event, retry_event, get_event_stats, get_recent_event_counts,
    list_subscribers, get_subscriber, create_subscriber, update_subscriber,
    delete_subscriber, toggle_subscriber_active, subscriber_name_exists,
    get_subscriber_stats, get_import_configs, get_inbox_configs,
    get_report_configs, get_event_types, get_job_types
)
from utils.db_helpers import format_sql_error
from utils.ui_helpers import load_custom_css, add_page_header, render_stat_card
from components.dependency_checker import render_missing_config_link

load_custom_css()
add_page_header("Event System", icon="🔔")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Event Queue",
    "🔔 Subscribers",
    "📜 Event Log",
    "⚙️ Service Status"
])

# ============================================================================
# TAB 1: EVENT QUEUE
# ============================================================================
with tab1:
    st.subheader("Event Queue")

    # Statistics
    try:
        stats = get_event_stats()
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            render_stat_card("Pending", str(stats['pending']), icon="⏳", color="#FFC107")
        with col2:
            render_stat_card("Processing", str(stats['processing']), icon="⚙️", color="#17A2B8")
        with col3:
            render_stat_card("Completed", str(stats['completed']), icon="✅", color="#28A745")
        with col4:
            render_stat_card("Failed", str(stats['failed']), icon="❌", color="#DC3545")
        with col5:
            render_stat_card("Total", str(stats['total']), icon="📊", color="#6C757D")
    except Exception as e:
        show_error(f"Failed to load statistics: {format_sql_error(e)}")

    st.divider()

    # Filters
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "pending", "processing", "completed", "failed", "cancelled"],
            key="event_status_filter"
        )
    with col2:
        type_filter = st.selectbox(
            "Event Type",
            ["All"] + get_event_types(),
            key="event_type_filter"
        )

    # Event list
    try:
        events = list_events(
            status=None if status_filter == "All" else status_filter,
            event_type=None if type_filter == "All" else type_filter,
            limit=100
        )

        if events:
            df = pd.DataFrame(events)

            # Format columns
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'processed_at' in df.columns:
                df['processed_at'] = pd.to_datetime(df['processed_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

            # Status emoji
            status_map = {
                'pending': '⏳ pending',
                'processing': '🔄 processing',
                'completed': '✅ completed',
                'failed': '❌ failed',
                'cancelled': '🚫 cancelled'
            }
            if 'status' in df.columns:
                df['status'] = df['status'].map(lambda x: status_map.get(x, x))

            display_cols = ['event_id', 'event_type', 'event_source', 'status', 'priority', 'created_at']
            display_cols = [c for c in display_cols if c in df.columns]

            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

            # Event actions
            st.markdown("### Event Actions")
            col1, col2 = st.columns([1, 2])

            with col1:
                event_ids = [str(e['event_id']) for e in events]
                selected_event_id = st.selectbox("Select Event", event_ids, key="action_event_id")

            with col2:
                action_cols = st.columns(3)
                with action_cols[0]:
                    if st.button("🔁 Retry", key="retry_event_btn"):
                        try:
                            retry_event(int(selected_event_id))
                            show_success(f"Event {selected_event_id} queued for retry")
                            st.rerun()
                        except Exception as e:
                            show_error(f"Failed to retry: {format_sql_error(e)}")

                with action_cols[1]:
                    if st.button("🚫 Cancel", key="cancel_event_btn"):
                        try:
                            cancel_event(int(selected_event_id))
                            show_success(f"Event {selected_event_id} cancelled")
                            st.rerun()
                        except Exception as e:
                            show_error(f"Failed to cancel: {format_sql_error(e)}")

            # Event details expander
            with st.expander("📄 View Event Details"):
                if selected_event_id:
                    event = get_event(int(selected_event_id))
                    if event:
                        st.json(event.get('event_data', {}))
                        if event.get('error_message'):
                            st.error(f"Error: {event['error_message']}")

        else:
            show_info("No events found matching the filters.")

    except Exception as e:
        show_error(f"Failed to load events: {format_sql_error(e)}")

    # Create Event section
    st.divider()
    with st.expander("➕ Create Manual Event", expanded=False):
        with st.form(key="create_event_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_event_type = st.selectbox(
                    "Event Type",
                    get_event_types(),
                    key="new_event_type"
                )
                new_event_source = st.text_input(
                    "Event Source",
                    placeholder="e.g., /app/data/source/file.csv",
                    key="new_event_source"
                )

            with col2:
                new_priority = st.slider("Priority", 1, 10, 5, key="new_priority")
                new_event_data = st.text_area(
                    "Event Data (JSON)",
                    value="{}",
                    height=100,
                    key="new_event_data"
                )

            if st.form_submit_button("Create Event", use_container_width=True):
                try:
                    event_data = json.loads(new_event_data)
                    event_id = create_event(
                        event_type=new_event_type,
                        event_source=new_event_source,
                        event_data=event_data,
                        priority=new_priority
                    )
                    show_success(f"Event created with ID: {event_id}")
                    st.rerun()
                except json.JSONDecodeError:
                    show_error("Invalid JSON in Event Data")
                except Exception as e:
                    show_error(f"Failed to create event: {format_sql_error(e)}")


# ============================================================================
# TAB 2: SUBSCRIBERS
# ============================================================================
with tab2:
    st.subheader("Event Subscribers")

    # Session state for success messages
    if 'subscriber_success' in st.session_state:
        show_success(st.session_state.subscriber_success)
        del st.session_state.subscriber_success

    # Statistics
    try:
        sub_stats = get_subscriber_stats()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_stat_card("Total", str(sub_stats['total']), icon="📧", color="#17A2B8")
        with col2:
            render_stat_card("Active", str(sub_stats['active']), icon="✅", color="#28A745")
        with col3:
            render_stat_card("Inactive", str(sub_stats['inactive']), icon="⏸️", color="#6C757D")
        with col4:
            render_stat_card("Total Triggers", str(sub_stats['total_triggers']), icon="🔔", color="#FFC107")
    except Exception as e:
        show_error(f"Failed to load statistics: {format_sql_error(e)}")

    st.divider()

    # Subscriber subtabs
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📋 View All", "➕ Create New", "✏️ Edit/Delete"])

    with sub_tab1:
        col1, col2 = st.columns([3, 1])
        with col2:
            show_active = st.checkbox("Active only", value=False, key="sub_active_only")

        try:
            subscribers = list_subscribers(active_only=show_active)
            if subscribers:
                df = pd.DataFrame(subscribers)

                display_cols = ['subscriber_id', 'subscriber_name', 'event_type', 'job_type', 'config_name', 'is_active', 'trigger_count']
                display_cols = [c for c in display_cols if c in df.columns]

                if 'is_active' in df.columns:
                    df['is_active'] = df['is_active'].map({True: '✅ Active', False: '❌ Inactive'})

                st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
            else:
                show_info("No subscribers found. Create one to get started.")
        except Exception as e:
            show_error(f"Failed to load subscribers: {format_sql_error(e)}")

    with sub_tab2:
        with st.form(key="create_subscriber_form"):
            st.markdown("### New Subscriber")

            col1, col2 = st.columns(2)

            with col1:
                sub_name = st.text_input("Subscriber Name *", key="new_sub_name")
                sub_event_type = st.selectbox("Event Type *", get_event_types(), key="new_sub_event_type")
                sub_job_type = st.selectbox("Job Type *", get_job_types(), key="new_sub_job_type")

            with col2:
                sub_description = st.text_area("Description", height=68, key="new_sub_desc")

                # Dynamic config selection based on job type
                if sub_job_type == 'import':
                    configs = get_import_configs()
                    if not configs:
                        st.warning("No import configs available.")
                        render_missing_config_link('import', context="inline")
                        sub_config_id = None
                    else:
                        config_options = [{'config_id': None, 'config_name': '-- Select --'}] + configs
                        sub_config_id = st.selectbox(
                            "Import Config *",
                            options=[c['config_id'] for c in config_options],
                            format_func=lambda x: next((c['config_name'] for c in config_options if c['config_id'] == x), '-- Select --'),
                            key="new_sub_config_import"
                        )
                elif sub_job_type == 'inbox_processor':
                    configs = get_inbox_configs()
                    if not configs:
                        st.warning("No inbox configs available.")
                        render_missing_config_link('inbox_processor', context="inline")
                        sub_config_id = None
                    else:
                        config_options = [{'config_id': None, 'config_name': '-- Select --'}] + configs
                        sub_config_id = st.selectbox(
                            "Inbox Config *",
                            options=[c['config_id'] for c in config_options],
                            format_func=lambda x: next((c['config_name'] for c in config_options if c['config_id'] == x), '-- Select --'),
                            key="new_sub_config_inbox"
                        )
                elif sub_job_type == 'report':
                    configs = get_report_configs()
                    if not configs:
                        st.warning("No report configs available.")
                        render_missing_config_link('report', context="inline")
                        sub_config_id = None
                    else:
                        config_options = [{'config_id': None, 'config_name': '-- Select --'}] + configs
                        sub_config_id = st.selectbox(
                            "Report Config *",
                            options=[c['config_id'] for c in config_options],
                            format_func=lambda x: next((c['config_name'] for c in config_options if c['config_id'] == x), '-- Select --'),
                            key="new_sub_config_report"
                        )
                else:
                    sub_config_id = None

            st.markdown("### Event Filter (Optional)")
            col1, col2 = st.columns(2)
            with col1:
                file_pattern = st.text_input(
                    "File Pattern",
                    value="*",
                    help="Glob pattern for file_received events (e.g., *.csv)",
                    key="new_sub_file_pattern"
                )

            with col2:
                if sub_job_type == 'custom':
                    script_path = st.text_input(
                        "Script Path *",
                        placeholder="/app/etl/jobs/custom_script.py",
                        key="new_sub_script"
                    )
                else:
                    script_path = None

            sub_is_active = st.checkbox("Active", value=True, key="new_sub_active")

            if st.form_submit_button("Create Subscriber", use_container_width=True):
                errors = []

                is_valid, error = validate_required(sub_name, "Subscriber Name")
                if not is_valid:
                    errors.append(error)

                if sub_job_type in ('import', 'inbox_processor', 'report') and not sub_config_id:
                    errors.append(f"Configuration is required for {sub_job_type} job type")

                if sub_job_type == 'custom' and not script_path:
                    errors.append("Script path is required for custom job type")

                if subscriber_name_exists(sub_name):
                    errors.append(f"Subscriber name '{sub_name}' already exists")

                if errors:
                    for e in errors:
                        show_error(e)
                else:
                    try:
                        event_filter = {'file_pattern': file_pattern} if file_pattern else {}

                        new_id = create_subscriber({
                            'subscriber_name': sub_name,
                            'description': sub_description,
                            'event_type': sub_event_type,
                            'event_filter': event_filter,
                            'job_type': sub_job_type,
                            'config_id': sub_config_id,
                            'script_path': script_path,
                            'is_active': sub_is_active
                        })
                        st.session_state.subscriber_success = f"Subscriber created with ID: {new_id}"
                        st.rerun()
                    except Exception as e:
                        show_error(f"Failed to create subscriber: {format_sql_error(e)}")

    with sub_tab3:
        try:
            subscribers = list_subscribers()
            if subscribers:
                sub_options = {f"{s['subscriber_id']}: {s['subscriber_name']}": s['subscriber_id'] for s in subscribers}
                selected = st.selectbox("Select Subscriber", list(sub_options.keys()), key="edit_sub_select")
                selected_id = sub_options[selected]
                sub = get_subscriber(selected_id)

                if sub:
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if sub['is_active']:
                            if st.button("🔴 Deactivate", key="deactivate_sub"):
                                toggle_subscriber_active(selected_id, False)
                                st.session_state.subscriber_success = "Subscriber deactivated"
                                st.rerun()
                        else:
                            if st.button("🟢 Activate", key="activate_sub"):
                                toggle_subscriber_active(selected_id, True)
                                st.session_state.subscriber_success = "Subscriber activated"
                                st.rerun()

                    st.divider()

                    # Details view
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Name", value=sub['subscriber_name'], disabled=True)
                        st.text_input("Event Type", value=sub['event_type'], disabled=True)
                        st.text_input("Job Type", value=sub['job_type'], disabled=True)
                    with col2:
                        st.text_input("Config ID", value=str(sub.get('config_id', '')), disabled=True)
                        st.text_input("Trigger Count", value=str(sub.get('trigger_count', 0)), disabled=True)
                        last_triggered = sub.get('last_triggered_at')
                        st.text_input("Last Triggered", value=str(last_triggered) if last_triggered else "Never", disabled=True)

                    # Delete section
                    st.divider()
                    show_warning("Deleting a subscriber cannot be undone.")
                    confirm = st.checkbox("I confirm I want to delete this subscriber", key="delete_sub_confirm")

                    if confirm:
                        if st.button("🗑️ Delete Subscriber", type="primary"):
                            try:
                                delete_subscriber(selected_id)
                                st.session_state.subscriber_success = "Subscriber deleted"
                                st.rerun()
                            except Exception as e:
                                show_error(f"Failed to delete: {format_sql_error(e)}")
            else:
                show_info("No subscribers to edit.")
        except Exception as e:
            show_error(f"Failed to load subscribers: {format_sql_error(e)}")


# ============================================================================
# TAB 3: EVENT LOG
# ============================================================================
with tab3:
    st.subheader("Event Log")

    try:
        # Get recent events
        events = list_events(limit=50)

        if events:
            # Status timeline
            st.markdown("### Recent Events")

            for event in events[:20]:
                status = event['status']
                icon = {
                    'pending': '⏳',
                    'processing': '🔄',
                    'completed': '✅',
                    'failed': '❌',
                    'cancelled': '🚫'
                }.get(status, '❓')

                col1, col2, col3, col4 = st.columns([1, 2, 2, 4])
                with col1:
                    st.write(f"{icon}")
                with col2:
                    st.write(f"**{event['event_type']}**")
                with col3:
                    st.write(event.get('created_at', '').strftime('%m/%d %H:%M') if event.get('created_at') else '')
                with col4:
                    source = event.get('event_source', '')
                    st.write(source[:50] + '...' if len(source) > 50 else source)

            # Chart
            st.divider()
            st.markdown("### Events Per Day (Last 7 Days)")

            daily_counts = get_recent_event_counts(7)
            if daily_counts:
                df = pd.DataFrame(daily_counts)
                df['date'] = pd.to_datetime(df['date'])
                st.bar_chart(df.set_index('date')[['completed', 'failed']])
            else:
                show_info("No event data available for chart.")

        else:
            show_info("No events in the log yet.")

    except Exception as e:
        show_error(f"Failed to load event log: {format_sql_error(e)}")


# ============================================================================
# TAB 4: SERVICE STATUS
# ============================================================================
with tab4:
    st.subheader("Pub-Sub Service Status")

    st.markdown("""
    The pub-sub service runs as a separate Docker container that:
    - **Watches** `/app/data/source` for new files
    - **Polls** the database every 5 seconds for pending events
    - **Dispatches** events to matching subscribers
    """)

    st.divider()

    # Service check
    st.markdown("### Service Check")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Database Connection**")
        try:
            stats = get_event_stats()
            st.success("Database connected")
            st.write(f"Events in queue: {stats['pending']} pending, {stats['processing']} processing")
        except Exception as e:
            st.error(f"Database error: {e}")

    with col2:
        st.markdown("**Quick Actions**")
        if st.button("🔄 Refresh Stats"):
            st.rerun()

    st.divider()

    # Configuration reference
    with st.expander("📖 Configuration Reference"):
        st.markdown("""
        ### Environment Variables

        | Variable | Description | Default |
        |----------|-------------|---------|
        | `PUBSUB_POLL_INTERVAL` | Seconds between DB polls | 5 |
        | `PUBSUB_WATCH_DIR` | Directory to watch | /app/data/source |

        ### Docker Commands

        ```bash
        # Start pub-sub service
        docker compose up -d pubsub

        # View logs
        docker compose logs -f pubsub

        # Restart service
        docker compose restart pubsub

        # Stop service
        docker compose stop pubsub
        ```

        ### Event Types

        | Type | Description | Triggered By |
        |------|-------------|--------------|
        | `file_received` | New file detected | File watcher |
        | `email_received` | Email processed | Inbox processor |
        | `import_complete` | Import job finished | Import job |
        | `report_sent` | Report emailed | Report generator |
        | `custom` | Manual/custom event | API or manual |

        ### Job Types

        | Type | Config Required | Description |
        |------|-----------------|-------------|
        | `import` | Import config_id | Run generic import |
        | `inbox_processor` | Inbox config_id | Run inbox processor |
        | `report` | Report report_id | Run report generator |
        | `custom` | Script path | Run custom script |
        """)


# Footer
st.divider()
st.caption("💡 Tip: Create subscribers to automatically trigger jobs when files arrive or events occur.")
