"""Import Configuration Management Page"""

import streamlit as st
import pandas as pd
from components.forms import render_import_config_form
from components.notifications import show_success, show_error, show_info, show_warning
from services.import_config_service import (
    list_configs,
    get_config,
    create_config,
    update_config,
    delete_config,
    toggle_active,
    get_config_stats
)
from utils.db_helpers import format_sql_error
from utils.formatters import format_timestamp, format_boolean, truncate_text


st.title("📋 Import Configuration Management")
st.markdown("Create, view, edit, and delete import configurations for the ETL pipeline.")

# Display statistics
stats = get_config_stats()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Configurations", stats['total'])
with col2:
    st.metric("Active", stats['active'])
with col3:
    st.metric("Inactive", stats['inactive'])

st.divider()

# Create tabs for different operations
tab1, tab2, tab3, tab4 = st.tabs(["📋 View All", "➕ Create New", "✏️ Edit", "🗑️ Delete"])

# TAB 1: View All Configurations
with tab1:
    st.subheader("All Import Configurations")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_active = st.selectbox(
            "Status",
            options=["All", "Active Only", "Inactive Only"],
            key="filter_status"
        )
    with col2:
        filter_file_type = st.selectbox(
            "File Type",
            options=["All", "CSV", "XLS", "XLSX", "JSON", "XML"],
            key="filter_file_type"
        )
    with col3:
        if st.button("🔄 Refresh", key="refresh_list"):
            st.rerun()

    # Fetch configurations with filters
    active_only = None
    if filter_active == "Active Only":
        active_only = True
    elif filter_active == "Inactive Only":
        active_only = False

    file_type_filter = None if filter_file_type == "All" else filter_file_type

    try:
        configs = list_configs(
            active_only=active_only if active_only is not None else False,
            file_type=file_type_filter
        )

        # Apply active filter manually if needed (since list_configs only has active_only=True)
        if filter_active == "Inactive Only":
            configs = [c for c in list_configs() if not c.get('is_active', False)]
        elif filter_active == "Active Only":
            configs = [c for c in configs if c.get('is_active', False)]

        if configs:
            # Convert to DataFrame for better display
            df = pd.DataFrame(configs)

            # Select and reorder columns for display
            display_columns = [
                'config_id',
                'config_name',
                'datasource',
                'datasettype',
                'file_type',
                'target_table',
                'strategy_name',
                'is_active',
                'last_modified_at'
            ]

            # Filter to only existing columns
            display_columns = [col for col in display_columns if col in df.columns]
            df_display = df[display_columns].copy()

            # Format columns
            if 'is_active' in df_display.columns:
                df_display['is_active'] = df_display['is_active'].apply(lambda x: '✅ Active' if x else '❌ Inactive')

            if 'last_modified_at' in df_display.columns:
                df_display['last_modified_at'] = df_display['last_modified_at'].apply(
                    lambda x: format_timestamp(x) if pd.notna(x) else 'N/A'
                )

            # Rename columns for display
            df_display.columns = [col.replace('_', ' ').title() for col in df_display.columns]

            # Display table
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                height=400
            )

            st.caption(f"Showing {len(configs)} configuration(s)")

            # Expandable section for detailed view
            with st.expander("🔍 View Configuration Details"):
                selected_id = st.number_input(
                    "Enter Config ID to view details",
                    min_value=1,
                    step=1,
                    key="detail_view_id"
                )

                if st.button("Load Details", key="load_details"):
                    config = get_config(selected_id)
                    if config:
                        st.json(config)
                    else:
                        show_error(f"Configuration with ID {selected_id} not found")

        else:
            show_info("No configurations found matching the selected filters.")

    except Exception as e:
        show_error(f"Error loading configurations: {format_sql_error(e)}")


# TAB 2: Create New Configuration
with tab2:
    form_data = render_import_config_form(is_edit=False)

    if form_data:
        try:
            new_id = create_config(form_data)
            show_success(f"✅ Configuration '{form_data['config_name']}' created successfully! (ID: {new_id})")
            st.toast("Configuration created!", icon="✅")

            # Provide next steps
            st.info(f"""
            **Next Steps:**
            1. Verify the target table `{form_data['target_table']}` exists
            2. Place files matching pattern `{form_data['file_pattern']}` in `{form_data['source_directory']}`
            3. Run the import: `docker compose exec tangerine python etl/jobs/generic_import.py --config-id {new_id}`
            """)

        except Exception as e:
            show_error(f"Failed to create configuration: {format_sql_error(e)}")


# TAB 3: Edit Configuration
with tab3:
    st.subheader("✏️ Edit Existing Configuration")

    # Show success message if exists in session state
    if 'update_success_message' in st.session_state:
        show_success(st.session_state.update_success_message)
        st.toast("Configuration updated!", icon="✅")
        del st.session_state.update_success_message

    # Select configuration to edit
    try:
        all_configs = list_configs()

        if all_configs:
            config_options = {f"{c['config_id']} - {c['config_name']}": c['config_id'] for c in all_configs}

            selected_config_str = st.selectbox(
                "Select Configuration to Edit",
                options=list(config_options.keys()),
                key="edit_select"
            )

            selected_config_id = config_options[selected_config_str]

            # Load selected config
            config_to_edit = get_config(selected_config_id)

            if config_to_edit:
                st.divider()

                # Show current status
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Config ID", config_to_edit['config_id'])
                with col2:
                    st.metric("File Type", config_to_edit['file_type'])
                with col3:
                    status = "✅ Active" if config_to_edit.get('is_active') else "❌ Inactive"
                    st.metric("Status", status)

                # Quick toggle active status
                st.markdown("#### Quick Actions")
                col1, col2 = st.columns(2)

                with col1:
                    if config_to_edit.get('is_active'):
                        if st.button("🔴 Deactivate Configuration", key="deactivate"):
                            try:
                                toggle_active(selected_config_id, False)
                                st.session_state.update_success_message = "✅ Configuration deactivated successfully"
                                st.rerun()
                            except Exception as e:
                                show_error(f"Error: {format_sql_error(e)}")
                    else:
                        if st.button("🟢 Activate Configuration", key="activate"):
                            try:
                                toggle_active(selected_config_id, True)
                                st.session_state.update_success_message = "✅ Configuration activated successfully"
                                st.rerun()
                            except Exception as e:
                                show_error(f"Error: {format_sql_error(e)}")

                st.divider()

                # Render edit form
                form_data = render_import_config_form(config_data=config_to_edit, is_edit=True)

                if form_data:
                    try:
                        # Check if config name changed and if new name already exists
                        from services.import_config_service import config_name_exists

                        if form_data['config_name'] != config_to_edit['config_name']:
                            if config_name_exists(form_data['config_name'], exclude_id=selected_config_id):
                                show_error(f"Configuration name '{form_data['config_name']}' already exists. Please use a different name.")
                                st.stop()

                        # Perform update
                        update_config(selected_config_id, form_data)

                        # Store success message in session state
                        st.session_state.update_success_message = f"✅ Configuration '{form_data['config_name']}' updated successfully!"
                        st.rerun()
                    except Exception as e:
                        show_error(f"Failed to update configuration: {format_sql_error(e)}")

        else:
            show_info("No configurations available. Create one in the 'Create New' tab.")

    except Exception as e:
        show_error(f"Error loading configurations: {format_sql_error(e)}")


# TAB 4: Delete Configuration
with tab4:
    st.subheader("🗑️ Delete Configuration")

    show_warning("⚠️ **Warning:** Deleting a configuration is permanent and cannot be undone. Consider deactivating instead.")

    try:
        all_configs = list_configs()

        if all_configs:
            config_options = {
                f"{c['config_id']} - {c['config_name']} ({'Active' if c.get('is_active') else 'Inactive'})": c['config_id']
                for c in all_configs
            }

            selected_config_str = st.selectbox(
                "Select Configuration to Delete",
                options=list(config_options.keys()),
                key="delete_select"
            )

            selected_config_id = config_options[selected_config_str]

            # Load selected config
            config_to_delete = get_config(selected_config_id)

            if config_to_delete:
                st.divider()

                # Show configuration details
                st.markdown("#### Configuration Details")
                col1, col2 = st.columns(2)

                with col1:
                    st.text_input("Config Name", value=config_to_delete['config_name'], disabled=True)
                    st.text_input("Data Source", value=config_to_delete['datasource'], disabled=True)
                    st.text_input("File Type", value=config_to_delete['file_type'], disabled=True)

                with col2:
                    st.text_input("Dataset Type", value=config_to_delete['datasettype'], disabled=True)
                    st.text_input("Target Table", value=config_to_delete['target_table'], disabled=True)
                    st.text_input("Status", value="Active" if config_to_delete.get('is_active') else "Inactive", disabled=True)

                st.divider()

                # Confirmation checkbox
                confirm = st.checkbox(
                    f"I confirm I want to permanently delete configuration '{config_to_delete['config_name']}'",
                    key="delete_confirm"
                )

                if confirm:
                    if st.button("🗑️ Delete Configuration Permanently", type="primary", key="delete_button"):
                        try:
                            delete_config(selected_config_id)
                            show_success(f"Configuration '{config_to_delete['config_name']}' deleted successfully")
                            st.rerun()
                        except Exception as e:
                            show_error(f"Failed to delete configuration: {format_sql_error(e)}")

        else:
            show_info("No configurations available to delete.")

    except Exception as e:
        show_error(f"Error loading configurations: {format_sql_error(e)}")


# Footer
st.divider()
st.caption("💡 **Tip:** Use the 'View All' tab to browse configurations, 'Create New' to add configurations, 'Edit' to modify existing ones, and 'Delete' to remove configurations permanently.")
