"""Reference Data Management Page - Datasources, Dataset Types, and Strategies"""

import streamlit as st
import pandas as pd
import io
import csv
from datetime import datetime, date
from components.forms import render_datasource_form, render_datasettype_form
from components.notifications import show_success, show_error, show_info, show_warning
from services.reference_data_service import (
    list_datasources,
    get_datasource,
    create_datasource,
    update_datasource,
    delete_datasource,
    datasource_name_exists,
    list_datasettypes,
    get_datasettype,
    create_datasettype,
    update_datasettype,
    delete_datasettype,
    datasettype_name_exists,
    list_strategies,
    get_reference_stats,
    get_datasource_usage,
    get_datasettype_usage,
    get_datasource_usage_count,
    get_datasettype_usage_count
)
from services.holiday_service import (
    get_all_holidays,
    get_holiday_by_date,
    create_holiday,
    update_holiday,
    delete_holiday,
    holiday_exists,
    bulk_create_holidays,
    get_holiday_stats
)
from components.dependency_checker import render_usage_badge, get_usage_warning_message
from utils.db_helpers import format_sql_error
from utils.formatters import format_timestamp

st.title("📚 Reference Data Management")
st.markdown("Manage data sources, dataset types, and view import strategies.")

# Display statistics
stats = get_reference_stats()
holiday_stats = get_holiday_stats()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Data Sources", stats['datasources'])
with col2:
    st.metric("Dataset Types", stats['datasettypes'])
with col3:
    st.metric("Import Strategies", stats['strategies'])
with col4:
    st.metric("Holidays", holiday_stats['total'])

st.divider()

# Create tabs for different reference tables
tab1, tab2, tab3, tab4 = st.tabs(["🗂️ Data Sources", "📊 Dataset Types", "📅 Holidays", "⚙️ Import Strategies"])

# ============================================================================
# TAB 1: DATA SOURCES
# ============================================================================
with tab1:
    st.subheader("Data Source Management")
    st.markdown("Data sources represent the origin of your data (e.g., API, File Server, Database).")

    # Sub-tabs for different operations
    ds_tab1, ds_tab2, ds_tab3, ds_tab4 = st.tabs(["📋 View All", "➕ Add New", "✏️ Edit", "🗑️ Delete"])

    # VIEW ALL DATA SOURCES
    with ds_tab1:
        try:
            datasources = list_datasources()

            if datasources:
                df = pd.DataFrame(datasources)

                # Add usage count column
                df['usage_count'] = df['sourcename'].apply(get_datasource_usage_count)

                # Format timestamps
                if 'createddate' in df.columns:
                    df['createddate'] = df['createddate'].apply(
                        lambda x: format_timestamp(x) if pd.notna(x) else 'N/A'
                    )

                # Format usage count for display
                df['used_by'] = df['usage_count'].apply(
                    lambda x: f"Used by {x} config(s)" if x > 0 else "Not used"
                )

                # Select columns to display
                display_columns = ['datasourceid', 'sourcename', 'description', 'used_by', 'createddate', 'createdby']
                display_columns = [col for col in display_columns if col in df.columns]

                st.dataframe(
                    df[display_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'datasourceid': st.column_config.NumberColumn('ID', width="small"),
                        'sourcename': st.column_config.TextColumn('Source Name', width="medium"),
                        'description': st.column_config.TextColumn('Description', width="large"),
                        'used_by': st.column_config.TextColumn('Usage', width="small"),
                        'createddate': st.column_config.TextColumn('Created', width="medium"),
                        'createdby': st.column_config.TextColumn('Created By', width="small")
                    }
                )

                st.caption(f"Showing {len(datasources)} data source(s)")
            else:
                show_info("No data sources found. Add one in the 'Add New' tab.")

        except Exception as e:
            show_error(f"Error loading data sources: {format_sql_error(e)}")

    # ADD NEW DATA SOURCE
    with ds_tab2:
        form_data = render_datasource_form(is_edit=False)

        if form_data:
            try:
                # Check if name already exists
                if datasource_name_exists(form_data['sourcename']):
                    show_error(f"Data source '{form_data['sourcename']}' already exists. Please use a different name.")
                else:
                    new_id = create_datasource(
                        form_data['sourcename'],
                        form_data.get('description')
                    )
                    show_success(f"✅ Data source '{form_data['sourcename']}' created successfully! (ID: {new_id})")
                    st.toast("Data source created!", icon="✅")
                    st.rerun()

            except Exception as e:
                show_error(f"Failed to create data source: {format_sql_error(e)}")

    # EDIT DATA SOURCE
    with ds_tab3:
        st.markdown("#### Select Data Source to Edit")

        # Show success message if exists in session state
        if 'datasource_update_success' in st.session_state:
            show_success(st.session_state.datasource_update_success)
            del st.session_state.datasource_update_success

        try:
            all_datasources = list_datasources()

            if all_datasources:
                ds_options = {f"{ds['datasourceid']} - {ds['sourcename']}": ds['datasourceid'] for ds in all_datasources}

                selected_ds_str = st.selectbox(
                    "Select Data Source",
                    options=list(ds_options.keys()),
                    key="edit_ds_select"
                )

                selected_ds_id = ds_options[selected_ds_str]
                ds_to_edit = get_datasource(selected_ds_id)

                if ds_to_edit:
                    st.divider()

                    # Show current info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("ID", ds_to_edit['datasourceid'])
                    with col2:
                        st.metric("Created", format_timestamp(ds_to_edit.get('createddate')))

                    st.divider()

                    # Render edit form
                    form_data = render_datasource_form(datasource_data=ds_to_edit, is_edit=True)

                    if form_data:
                        try:
                            # Check if new name conflicts
                            if form_data['sourcename'] != ds_to_edit['sourcename']:
                                if datasource_name_exists(form_data['sourcename'], exclude_id=selected_ds_id):
                                    show_error(f"Data source '{form_data['sourcename']}' already exists. Please use a different name.")
                                    st.stop()

                            update_datasource(
                                selected_ds_id,
                                form_data['sourcename'],
                                form_data.get('description')
                            )
                            st.session_state.datasource_update_success = f"✅ Data source '{form_data['sourcename']}' updated successfully!"
                            st.rerun()

                        except Exception as e:
                            show_error(f"Failed to update data source: {format_sql_error(e)}")

            else:
                show_info("No data sources available to edit.")

        except Exception as e:
            show_error(f"Error loading data sources: {format_sql_error(e)}")

    # DELETE DATA SOURCE
    with ds_tab4:
        st.markdown("#### Delete Data Source")
        show_warning("⚠️ **Warning:** Deletion is permanent. Data sources referenced by import configurations cannot be deleted.")

        try:
            all_datasources = list_datasources()

            if all_datasources:
                ds_options = {f"{ds['datasourceid']} - {ds['sourcename']}": ds['datasourceid'] for ds in all_datasources}

                selected_ds_str = st.selectbox(
                    "Select Data Source to Delete",
                    options=list(ds_options.keys()),
                    key="delete_ds_select"
                )

                selected_ds_id = ds_options[selected_ds_str]
                ds_to_delete = get_datasource(selected_ds_id)

                if ds_to_delete:
                    st.divider()

                    # Show details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Source Name", value=ds_to_delete['sourcename'], disabled=True)
                    with col2:
                        st.text_input("Created By", value=ds_to_delete.get('createdby', 'N/A'), disabled=True)

                    st.text_area("Description", value=ds_to_delete.get('description', 'N/A'), disabled=True, height=100)

                    # Check for references before allowing delete
                    referencing_configs = get_datasource_usage(ds_to_delete['sourcename'])

                    st.divider()

                    if referencing_configs:
                        # Show blocking message with specific config names
                        show_error(get_usage_warning_message(
                            "data source",
                            ds_to_delete['sourcename'],
                            referencing_configs
                        ))
                        st.info("Update or delete the referencing configurations before deleting this data source.")
                    else:
                        confirm = st.checkbox(
                            f"I confirm I want to permanently delete data source '{ds_to_delete['sourcename']}'",
                            key="delete_ds_confirm"
                        )

                        if confirm:
                            if st.button("🗑️ Delete Data Source Permanently", type="primary", key="delete_ds_button"):
                                try:
                                    delete_datasource(selected_ds_id)
                                    show_success(f"Data source '{ds_to_delete['sourcename']}' deleted successfully")
                                    st.rerun()
                                except Exception as e:
                                    show_error(f"Failed to delete data source: {format_sql_error(e)}")

            else:
                show_info("No data sources available to delete.")

        except Exception as e:
            show_error(f"Error loading data sources: {format_sql_error(e)}")


# ============================================================================
# TAB 2: DATASET TYPES
# ============================================================================
with tab2:
    st.subheader("Dataset Type Management")
    st.markdown("Dataset types categorize your data (e.g., Raw, Transformed, Imported).")

    # Sub-tabs for different operations
    dt_tab1, dt_tab2, dt_tab3, dt_tab4 = st.tabs(["📋 View All", "➕ Add New", "✏️ Edit", "🗑️ Delete"])

    # VIEW ALL DATASET TYPES
    with dt_tab1:
        try:
            datasettypes = list_datasettypes()

            if datasettypes:
                df = pd.DataFrame(datasettypes)

                # Add usage count column
                df['usage_count'] = df['typename'].apply(get_datasettype_usage_count)

                # Format timestamps
                if 'createddate' in df.columns:
                    df['createddate'] = df['createddate'].apply(
                        lambda x: format_timestamp(x) if pd.notna(x) else 'N/A'
                    )

                # Format usage count for display
                df['used_by'] = df['usage_count'].apply(
                    lambda x: f"Used by {x} config(s)" if x > 0 else "Not used"
                )

                # Select columns to display
                display_columns = ['datasettypeid', 'typename', 'description', 'used_by', 'createddate', 'createdby']
                display_columns = [col for col in display_columns if col in df.columns]

                st.dataframe(
                    df[display_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'datasettypeid': st.column_config.NumberColumn('ID', width="small"),
                        'typename': st.column_config.TextColumn('Type Name', width="medium"),
                        'description': st.column_config.TextColumn('Description', width="large"),
                        'used_by': st.column_config.TextColumn('Usage', width="small"),
                        'createddate': st.column_config.TextColumn('Created', width="medium"),
                        'createdby': st.column_config.TextColumn('Created By', width="small")
                    }
                )

                st.caption(f"Showing {len(datasettypes)} dataset type(s)")
            else:
                show_info("No dataset types found. Add one in the 'Add New' tab.")

        except Exception as e:
            show_error(f"Error loading dataset types: {format_sql_error(e)}")

    # ADD NEW DATASET TYPE
    with dt_tab2:
        form_data = render_datasettype_form(is_edit=False)

        if form_data:
            try:
                # Check if name already exists
                if datasettype_name_exists(form_data['typename']):
                    show_error(f"Dataset type '{form_data['typename']}' already exists. Please use a different name.")
                else:
                    new_id = create_datasettype(
                        form_data['typename'],
                        form_data.get('description')
                    )
                    show_success(f"✅ Dataset type '{form_data['typename']}' created successfully! (ID: {new_id})")
                    st.toast("Dataset type created!", icon="✅")
                    st.rerun()

            except Exception as e:
                show_error(f"Failed to create dataset type: {format_sql_error(e)}")

    # EDIT DATASET TYPE
    with dt_tab3:
        st.markdown("#### Select Dataset Type to Edit")

        # Show success message if exists in session state
        if 'datasettype_update_success' in st.session_state:
            show_success(st.session_state.datasettype_update_success)
            del st.session_state.datasettype_update_success

        try:
            all_datasettypes = list_datasettypes()

            if all_datasettypes:
                dt_options = {f"{dt['datasettypeid']} - {dt['typename']}": dt['datasettypeid'] for dt in all_datasettypes}

                selected_dt_str = st.selectbox(
                    "Select Dataset Type",
                    options=list(dt_options.keys()),
                    key="edit_dt_select"
                )

                selected_dt_id = dt_options[selected_dt_str]
                dt_to_edit = get_datasettype(selected_dt_id)

                if dt_to_edit:
                    st.divider()

                    # Show current info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("ID", dt_to_edit['datasettypeid'])
                    with col2:
                        st.metric("Created", format_timestamp(dt_to_edit.get('createddate')))

                    st.divider()

                    # Render edit form
                    form_data = render_datasettype_form(datasettype_data=dt_to_edit, is_edit=True)

                    if form_data:
                        try:
                            # Check if new name conflicts
                            if form_data['typename'] != dt_to_edit['typename']:
                                if datasettype_name_exists(form_data['typename'], exclude_id=selected_dt_id):
                                    show_error(f"Dataset type '{form_data['typename']}' already exists. Please use a different name.")
                                    st.stop()

                            update_datasettype(
                                selected_dt_id,
                                form_data['typename'],
                                form_data.get('description')
                            )
                            st.session_state.datasettype_update_success = f"✅ Dataset type '{form_data['typename']}' updated successfully!"
                            st.rerun()

                        except Exception as e:
                            show_error(f"Failed to update dataset type: {format_sql_error(e)}")

            else:
                show_info("No dataset types available to edit.")

        except Exception as e:
            show_error(f"Error loading dataset types: {format_sql_error(e)}")

    # DELETE DATASET TYPE
    with dt_tab4:
        st.markdown("#### Delete Dataset Type")
        show_warning("⚠️ **Warning:** Deletion is permanent. Dataset types referenced by import configurations cannot be deleted.")

        try:
            all_datasettypes = list_datasettypes()

            if all_datasettypes:
                dt_options = {f"{dt['datasettypeid']} - {dt['typename']}": dt['datasettypeid'] for dt in all_datasettypes}

                selected_dt_str = st.selectbox(
                    "Select Dataset Type to Delete",
                    options=list(dt_options.keys()),
                    key="delete_dt_select"
                )

                selected_dt_id = dt_options[selected_dt_str]
                dt_to_delete = get_datasettype(selected_dt_id)

                if dt_to_delete:
                    st.divider()

                    # Show details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Type Name", value=dt_to_delete['typename'], disabled=True)
                    with col2:
                        st.text_input("Created By", value=dt_to_delete.get('createdby', 'N/A'), disabled=True)

                    st.text_area("Description", value=dt_to_delete.get('description', 'N/A'), disabled=True, height=100)

                    # Check for references before allowing delete
                    referencing_configs = get_datasettype_usage(dt_to_delete['typename'])

                    st.divider()

                    if referencing_configs:
                        # Show blocking message with specific config names
                        show_error(get_usage_warning_message(
                            "dataset type",
                            dt_to_delete['typename'],
                            referencing_configs
                        ))
                        st.info("Update or delete the referencing configurations before deleting this dataset type.")
                    else:
                        confirm = st.checkbox(
                            f"I confirm I want to permanently delete dataset type '{dt_to_delete['typename']}'",
                            key="delete_dt_confirm"
                        )

                        if confirm:
                            if st.button("🗑️ Delete Dataset Type Permanently", type="primary", key="delete_dt_button"):
                                try:
                                    delete_datasettype(selected_dt_id)
                                    show_success(f"Dataset type '{dt_to_delete['typename']}' deleted successfully")
                                    st.rerun()
                                except Exception as e:
                                    show_error(f"Failed to delete dataset type: {format_sql_error(e)}")

            else:
                show_info("No dataset types available to delete.")

        except Exception as e:
            show_error(f"Error loading dataset types: {format_sql_error(e)}")


# ============================================================================
# TAB 3: HOLIDAYS
# ============================================================================
with tab3:
    st.subheader("Holiday Management")
    st.markdown("Manage holidays used for business day calculations in ETL processes.")

    # Sub-tabs for different operations
    hol_tab1, hol_tab2, hol_tab3, hol_tab4, hol_tab5 = st.tabs(["📋 View All", "➕ Add Single", "📁 Bulk Upload", "✏️ Edit", "🗑️ Delete"])

    # VIEW ALL HOLIDAYS
    with hol_tab1:
        try:
            holidays = get_all_holidays()

            if holidays:
                df = pd.DataFrame(holidays)

                # Format dates
                if 'holiday_date' in df.columns:
                    df['holiday_date'] = pd.to_datetime(df['holiday_date']).dt.strftime('%Y-%m-%d')

                if 'createddate' in df.columns:
                    df['createddate'] = df['createddate'].apply(
                        lambda x: format_timestamp(x) if pd.notna(x) else 'N/A'
                    )

                # Select columns to display
                display_columns = ['holiday_date', 'holiday_name', 'createddate', 'createdby']
                display_columns = [col for col in display_columns if col in df.columns]

                st.dataframe(
                    df[display_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'holiday_date': st.column_config.DateColumn('Date', format="YYYY-MM-DD", width="medium"),
                        'holiday_name': st.column_config.TextColumn('Holiday Name', width="large"),
                        'createddate': st.column_config.TextColumn('Created', width="medium"),
                        'createdby': st.column_config.TextColumn('Created By', width="small")
                    }
                )

                st.caption(f"Showing {len(holidays)} holiday(s)")

                # Download as CSV
                csv_buffer = io.StringIO()
                df[['holiday_date', 'holiday_name']].to_csv(csv_buffer, index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"holidays_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                show_info("No holidays found. Add holidays in the 'Add Single' or 'Bulk Upload' tabs.")

        except Exception as e:
            show_error(f"Error loading holidays: {format_sql_error(e)}")

    # ADD SINGLE HOLIDAY
    with hol_tab2:
        st.markdown("#### Add a Single Holiday")

        with st.form("add_holiday_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                holiday_date = st.date_input(
                    "Holiday Date",
                    value=None,
                    help="Select the date of the holiday"
                )
            with col2:
                holiday_name = st.text_input(
                    "Holiday Name (Optional)",
                    max_chars=100,
                    help="E.g., 'New Year's Day', 'Independence Day'"
                )

            if st.form_submit_button("➕ Add Holiday", type="primary"):
                if not holiday_date:
                    show_error("Please select a holiday date")
                elif holiday_exists(holiday_date):
                    show_error(f"Holiday on {holiday_date} already exists")
                else:
                    try:
                        create_holiday(holiday_date, holiday_name if holiday_name else None)
                        show_success(f"✅ Holiday on {holiday_date} added successfully!")
                        st.toast("Holiday added!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        show_error(f"Failed to add holiday: {format_sql_error(e)}")

    # BULK UPLOAD
    with hol_tab3:
        st.markdown("#### Bulk Upload Holidays from CSV")

        show_info("📋 **CSV Format:** Upload a CSV file with columns `holiday_date` (YYYY-MM-DD) and optional `holiday_name`")

        with st.expander("📖 CSV Template & Example", expanded=False):
            st.markdown("""
            **Required columns:**
            - `holiday_date` - Date in YYYY-MM-DD format (required)
            - `holiday_name` - Description of the holiday (optional)

            **Example CSV:**
            ```
            holiday_date,holiday_name
            2026-01-01,New Year's Day
            2026-07-04,Independence Day
            2026-12-25,Christmas Day
            ```
            """)

            # Provide template download
            template_data = "holiday_date,holiday_name\n2026-01-01,New Year's Day\n2026-07-04,Independence Day\n"
            st.download_button(
                label="📥 Download CSV Template",
                data=template_data,
                file_name="holiday_template.csv",
                mime="text/csv"
            )

        uploaded_file = st.file_uploader(
            "Upload CSV File",
            type=['csv'],
            help="Upload a CSV file containing holiday dates"
        )

        if uploaded_file is not None:
            try:
                # Read CSV
                csv_data = uploaded_file.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(csv_data))

                holidays_to_import = []
                for row in csv_reader:
                    if 'holiday_date' in row and row['holiday_date']:
                        holidays_to_import.append({
                            'holiday_date': row['holiday_date'],
                            'holiday_name': row.get('holiday_name', '')
                        })

                if holidays_to_import:
                    st.info(f"📊 Preview: {len(holidays_to_import)} holidays found in CSV")

                    # Show preview
                    preview_df = pd.DataFrame(holidays_to_import[:10])
                    st.dataframe(preview_df, use_container_width=True)

                    if len(holidays_to_import) > 10:
                        st.caption(f"Showing first 10 of {len(holidays_to_import)} rows...")

                    if st.button("📁 Import All Holidays", type="primary"):
                        success_count, errors = bulk_create_holidays(holidays_to_import)

                        if success_count > 0:
                            show_success(f"✅ Successfully imported {success_count} holiday(s)!")

                        if errors:
                            show_warning(f"⚠️ {len(errors)} error(s) occurred:")
                            for error in errors[:5]:  # Show first 5 errors
                                st.caption(f"• {error}")
                            if len(errors) > 5:
                                st.caption(f"... and {len(errors) - 5} more errors")

                        if success_count > 0:
                            st.rerun()
                else:
                    show_error("No valid holiday data found in CSV")

            except Exception as e:
                show_error(f"Error processing CSV: {format_sql_error(e)}")

    # EDIT HOLIDAY
    with hol_tab4:
        st.markdown("#### Edit Holiday")

        # Show success message if exists
        if 'holiday_update_success' in st.session_state:
            show_success(st.session_state.holiday_update_success)
            del st.session_state.holiday_update_success

        try:
            all_holidays = get_all_holidays()

            if all_holidays:
                # Create options for selectbox
                holiday_options = {
                    f"{h['holiday_date']} - {h.get('holiday_name', 'Unnamed')}": h['holiday_date']
                    for h in all_holidays
                }

                selected_holiday_str = st.selectbox(
                    "Select Holiday to Edit",
                    options=list(holiday_options.keys()),
                    key="edit_holiday_select"
                )

                selected_date = holiday_options[selected_holiday_str]
                holiday_to_edit = get_holiday_by_date(selected_date)

                if holiday_to_edit:
                    st.divider()

                    # Show current info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Holiday Date", holiday_to_edit['holiday_date'])
                    with col2:
                        st.metric("Created", format_timestamp(holiday_to_edit.get('createddate')))

                    st.divider()

                    # Edit form
                    with st.form("edit_holiday_form"):
                        st.text_input("Date (Cannot be changed)", value=str(holiday_to_edit['holiday_date']), disabled=True)

                        new_holiday_name = st.text_input(
                            "Holiday Name",
                            value=holiday_to_edit.get('holiday_name', ''),
                            max_chars=100
                        )

                        if st.form_submit_button("💾 Update Holiday", type="primary"):
                            try:
                                update_holiday(holiday_to_edit['holiday_date'], new_holiday_name if new_holiday_name else None)
                                st.session_state.holiday_update_success = f"✅ Holiday on {holiday_to_edit['holiday_date']} updated successfully!"
                                st.rerun()
                            except Exception as e:
                                show_error(f"Failed to update holiday: {format_sql_error(e)}")
            else:
                show_info("No holidays available to edit.")

        except Exception as e:
            show_error(f"Error loading holidays: {format_sql_error(e)}")

    # DELETE HOLIDAY
    with hol_tab5:
        st.markdown("#### Delete Holiday")
        show_warning("⚠️ **Warning:** Deletion is permanent and may affect business day calculations.")

        try:
            all_holidays = get_all_holidays()

            if all_holidays:
                holiday_options = {
                    f"{h['holiday_date']} - {h.get('holiday_name', 'Unnamed')}": h['holiday_date']
                    for h in all_holidays
                }

                selected_holiday_str = st.selectbox(
                    "Select Holiday to Delete",
                    options=list(holiday_options.keys()),
                    key="delete_holiday_select"
                )

                selected_date = holiday_options[selected_holiday_str]
                holiday_to_delete = get_holiday_by_date(selected_date)

                if holiday_to_delete:
                    st.divider()

                    # Show details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Date", value=str(holiday_to_delete['holiday_date']), disabled=True)
                    with col2:
                        st.text_input("Holiday Name", value=holiday_to_delete.get('holiday_name', 'Unnamed'), disabled=True)

                    st.divider()

                    confirm = st.checkbox(
                        f"I confirm I want to permanently delete holiday on {holiday_to_delete['holiday_date']}",
                        key="delete_holiday_confirm"
                    )

                    if confirm:
                        if st.button("🗑️ Delete Holiday Permanently", type="primary", key="delete_holiday_button"):
                            try:
                                delete_holiday(holiday_to_delete['holiday_date'])
                                show_success(f"Holiday on {holiday_to_delete['holiday_date']} deleted successfully")
                                st.rerun()
                            except Exception as e:
                                show_error(f"Failed to delete holiday: {format_sql_error(e)}")
            else:
                show_info("No holidays available to delete.")

        except Exception as e:
            show_error(f"Error loading holidays: {format_sql_error(e)}")


# ============================================================================
# TAB 4: IMPORT STRATEGIES (READ-ONLY)
# ============================================================================
with tab4:
    st.subheader("Import Strategies (Read-Only)")
    st.markdown("Import strategies define how the system handles column mismatches during data imports.")

    show_info("ℹ️ Import strategies are predefined and cannot be modified through the UI.")

    try:
        strategies = list_strategies()

        if strategies:
            for strategy in strategies:
                with st.expander(f"**{strategy['importstrategyid']}. {strategy['name']}**", expanded=True):
                    st.markdown(f"**Description:** {strategy.get('description', 'No description available')}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Strategy ID", strategy['importstrategyid'])
                    with col2:
                        st.metric("Created", format_timestamp(strategy.get('createddate')))

                    if strategy.get('createdby'):
                        st.caption(f"Created by: {strategy['createdby']}")

            st.caption(f"Showing {len(strategies)} import strategy(ies)")
        else:
            show_warning("No import strategies found in the database.")

    except Exception as e:
        show_error(f"Error loading import strategies: {format_sql_error(e)}")


# Footer
st.divider()
st.caption("💡 **Tip:** Use this page to manage the reference data used by import configurations. Data sources and dataset types can be freely added, edited, or deleted (unless referenced by active configurations).")
