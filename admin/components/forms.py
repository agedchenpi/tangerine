"""Reusable form components for admin interface"""

import streamlit as st
from typing import Dict, Any, Optional, List, Tuple
from components.validators import (
    validate_config_name,
    validate_directory_path,
    validate_file_pattern,
    validate_table_name,
    validate_date_format,
    validate_required,
    validate_positive_integer,
    validate_max_length
)
from components.notifications import show_error, show_warning
from services.import_config_service import get_datasources, get_datasettypes, get_strategies
from utils.db_helpers import table_exists


def render_import_config_form(
    config_data: Optional[Dict[str, Any]] = None,
    is_edit: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Render the import configuration form.

    Args:
        config_data: Existing configuration data (for edit mode)
        is_edit: If True, renders edit form with pre-filled values

    Returns:
        Dictionary of form values if valid, None otherwise
    """
    st.subheader("📋 " + ("Edit" if is_edit else "Create") + " Import Configuration")

    # Load reference data
    datasources = get_datasources()
    datasettypes = get_datasettypes()
    strategies = get_strategies()

    if not datasources:
        show_error("No datasources found. Please create at least one datasource first.")
        st.info("💡 To add a new datasource, run: `INSERT INTO dba.tdatasource (sourcename, description) VALUES ('MySource', 'Description');`")
        return None

    if not datasettypes:
        show_error("No dataset types found. Please create at least one dataset type first.")
        st.info("💡 To add a new dataset type, run: `INSERT INTO dba.tdatasettype (typename, description) VALUES ('MyType', 'Description');`")
        return None

    # Create form with unique key based on mode
    form_key = "import_config_form_edit" if is_edit else "import_config_form_create"
    with st.form(key=form_key):
        # Section 1: Basic Information
        st.markdown("### Basic Information")

        # Info box for reference data
        if not is_edit:
            st.info("💡 **Need to add a new Data Source or Dataset Type?** Navigate to the **Reference Data** page (Phase 4 - coming soon), or add via SQL: `INSERT INTO dba.tdatasource (sourcename, description) VALUES ('MySource', 'Description');`")

        col1, col2 = st.columns(2)

        with col1:
            config_name = st.text_input(
                "Configuration Name *",
                value=config_data.get('config_name', '') if config_data else '',
                help="Unique name for this configuration (alphanumeric, underscore, hyphen only)"
            )

            datasource = st.selectbox(
                "Data Source *",
                options=datasources,
                index=datasources.index(config_data['datasource']) if config_data and config_data.get('datasource') in datasources else 0,
                help="Select the data source for this import"
            )

            file_type = st.selectbox(
                "File Type *",
                options=['CSV', 'XLS', 'XLSX', 'JSON', 'XML'],
                index=['CSV', 'XLS', 'XLSX', 'JSON', 'XML'].index(config_data['file_type']) if config_data and config_data.get('file_type') else 0,
                help="Type of files to import"
            )

        with col2:
            datasettype = st.selectbox(
                "Dataset Type *",
                options=datasettypes,
                index=datasettypes.index(config_data['datasettype']) if config_data and config_data.get('datasettype') in datasettypes else 0,
                help="Select the dataset type for this import"
            )

            strategy_options = [f"{s['importstrategyid']}. {s['name']}" for s in strategies]
            strategy_index = 0
            if config_data and config_data.get('importstrategyid'):
                try:
                    strategy_index = [s['importstrategyid'] for s in strategies].index(config_data['importstrategyid'])
                except ValueError:
                    pass

            importstrategy = st.selectbox(
                "Import Strategy *",
                options=strategy_options,
                index=strategy_index,
                help="How to handle column mismatches"
            )
            importstrategyid = int(importstrategy.split('.')[0])

            # Show strategy description
            selected_strategy = strategies[strategy_index]
            st.info(f"ℹ️ {selected_strategy.get('description', 'No description available')}")

        # Section 2: File Processing
        st.markdown("### File Processing")
        col1, col2 = st.columns(2)

        with col1:
            source_directory = st.text_input(
                "Source Directory *",
                value=config_data.get('source_directory', '/app/data/source') if config_data else '/app/data/source',
                help="Absolute path where input files are located (e.g., /app/data/source)"
            )

            file_pattern = st.text_input(
                "File Pattern (Regex) *",
                value=config_data.get('file_pattern', '.*\\.csv') if config_data else '.*\\.csv',
                help="Regex pattern to match files (e.g., .*MyPattern\\.csv)"
            )

        with col2:
            archive_directory = st.text_input(
                "Archive Directory *",
                value=config_data.get('archive_directory', '/app/data/archive') if config_data else '/app/data/archive',
                help="Absolute path where processed files are archived (e.g., /app/data/archive)"
            )

            target_table = st.text_input(
                "Target Table *",
                value=config_data.get('target_table', 'feeds.') if config_data else 'feeds.',
                help="Target table in schema.table format (e.g., feeds.my_import)"
            )

        # Section 3: Metadata Configuration
        st.markdown("### Metadata Extraction")
        col1, col2 = st.columns(2)

        with col1:
            metadata_label_source = st.selectbox(
                "Metadata Label Source *",
                options=['filename', 'file_content', 'static'],
                index=['filename', 'file_content', 'static'].index(config_data['metadata_label_source']) if config_data and config_data.get('metadata_label_source') else 0,
                help="Where to extract the metadata label from"
            )

            # Dynamic field based on metadata_label_source
            if metadata_label_source == 'filename':
                metadata_label_location = st.number_input(
                    "Label Position Index *",
                    min_value=0,
                    value=int(config_data.get('metadata_label_location', 1)) if config_data and config_data.get('metadata_label_location', '').isdigit() else 1,
                    help="Position in filename (0=first segment, 1=second, etc.) using delimiter"
                )
                metadata_label_location = str(metadata_label_location)
            elif metadata_label_source == 'file_content':
                metadata_label_location = st.text_input(
                    "Label Column Name *",
                    value=config_data.get('metadata_label_location', '') if config_data else '',
                    help="Name of column in file containing the label"
                )
            else:  # static
                metadata_label_location = st.text_input(
                    "Static Label Value *",
                    value=config_data.get('metadata_label_location', '') if config_data else '',
                    help="Enter the static label value to use for all records"
                )

        with col2:
            dateconfig = st.selectbox(
                "Date Source *",
                options=['filename', 'file_content', 'static'],
                index=['filename', 'file_content', 'static'].index(config_data['dateconfig']) if config_data and config_data.get('dateconfig') else 0,
                help="Where to extract the date from"
            )

            # Dynamic field based on dateconfig
            if dateconfig == 'filename':
                datelocation = st.number_input(
                    "Date Position Index *",
                    min_value=0,
                    value=int(config_data.get('datelocation', 0)) if config_data and config_data.get('datelocation', '').isdigit() else 0,
                    help="Position in filename (0=first segment, 1=second, etc.) using delimiter"
                )
                datelocation = str(datelocation)
            elif dateconfig == 'file_content':
                datelocation = st.text_input(
                    "Date Column Name *",
                    value=config_data.get('datelocation', '') if config_data else '',
                    help="Name of column in file containing the date"
                )
            else:  # static
                datelocation = st.text_input(
                    "Static Date Value *",
                    value=config_data.get('datelocation', '') if config_data else '',
                    help="Enter static date in the format specified below (e.g., 2026-01-04)"
                )

        # Section 4: Date & Parsing Configuration
        st.markdown("### Date & Parsing Configuration")
        col1, col2, col3 = st.columns(3)

        with col1:
            dateformat = st.text_input(
                "Date Format *",
                value=config_data.get('dateformat', 'yyyyMMddTHHmmss') if config_data else 'yyyyMMddTHHmmss',
                help="Date format pattern (e.g., yyyyMMddTHHmmss, yyyy-MM-dd)"
            )

        with col2:
            delimiter = st.text_input(
                "Filename Delimiter",
                value=config_data.get('delimiter', '_') if config_data else '_',
                help="Delimiter for parsing filenames (e.g., _ or -)"
            )

        with col3:
            is_blob = st.checkbox(
                "Store as Blob",
                value=config_data.get('is_blob', False) if config_data else False,
                help="For JSON/XML: store as blob instead of parsing (applies to JSON and XML only)"
            )

        # Section 5: Status
        st.markdown("### Status")
        is_active = st.checkbox(
            "Active",
            value=config_data.get('is_active', True) if config_data else True,
            help="Enable or disable this configuration"
        )

        # Submit button
        submitted = st.form_submit_button(
            "💾 " + ("Update Configuration" if is_edit else "Create Configuration"),
            use_container_width=True
        )

        if submitted:
            # Validate all fields
            errors = []

            # Required field validations
            if not is_edit:  # Only validate name on create (it's disabled on edit)
                is_valid, error = validate_config_name(config_name)
                if not is_valid:
                    errors.append(f"Config Name: {error}")

            is_valid, error = validate_directory_path(source_directory)
            if not is_valid:
                errors.append(f"Source Directory: {error}")

            is_valid, error = validate_directory_path(archive_directory)
            if not is_valid:
                errors.append(f"Archive Directory: {error}")

            if source_directory == archive_directory:
                errors.append("Source and Archive directories must be different")

            is_valid, error = validate_file_pattern(file_pattern)
            if not is_valid:
                errors.append(f"File Pattern: {error}")

            is_valid, error = validate_table_name(target_table)
            if not is_valid:
                errors.append(f"Target Table: {error}")

            is_valid, error = validate_date_format(dateformat)
            if not is_valid:
                errors.append(f"Date Format: {error}")
            elif error:  # Warning
                show_warning(f"Date Format: {error}")

            # Conditional validations
            if dateconfig == 'filename' and not delimiter:
                errors.append("Delimiter is required when Date Source is 'filename'")

            if metadata_label_source == 'filename' and not delimiter:
                errors.append("Delimiter is required when Metadata Label Source is 'filename'")

            if not metadata_label_location or (isinstance(metadata_label_location, str) and not metadata_label_location.strip()):
                if metadata_label_source == 'filename':
                    errors.append("Label Position Index is required when source is 'filename'")
                elif metadata_label_source == 'file_content':
                    errors.append("Label Column Name is required when source is 'file_content'")
                elif metadata_label_source == 'static':
                    errors.append("Static Label Value is required when source is 'static'")

            if not datelocation or (isinstance(datelocation, str) and not datelocation.strip()):
                if dateconfig == 'filename':
                    errors.append("Date Position Index is required when source is 'filename'")
                elif dateconfig == 'file_content':
                    errors.append("Date Column Name is required when source is 'file_content'")
                elif dateconfig == 'static':
                    errors.append("Static Date Value is required when source is 'static'")

            # Check if target table exists (warning only)
            if target_table and '.' in target_table:
                schema, table = target_table.split('.')
                if not table_exists(schema, table):
                    show_warning(f"Warning: Table {target_table} does not exist. It will need to be created before import.")

            # Display errors
            if errors:
                for error in errors:
                    show_error(error)
                return None

            # Return form data
            form_data = {
                'config_name': config_name,
                'datasource': datasource,
                'datasettype': datasettype,
                'source_directory': source_directory,
                'archive_directory': archive_directory,
                'file_pattern': file_pattern,
                'file_type': file_type,
                'metadata_label_source': metadata_label_source,
                'metadata_label_location': metadata_label_location if metadata_label_location else None,
                'dateconfig': dateconfig,
                'datelocation': datelocation if datelocation else None,
                'dateformat': dateformat if dateformat else None,
                'delimiter': delimiter if delimiter else None,
                'target_table': target_table,
                'importstrategyid': importstrategyid,
                'is_active': is_active,
                'is_blob': is_blob
            }

            return form_data

    return None


def render_datasource_form(
    datasource_data: Optional[Dict[str, Any]] = None,
    is_edit: bool = False
) -> Optional[Dict[str, str]]:
    """
    Render the datasource form.

    Args:
        datasource_data: Existing datasource data (for edit mode)
        is_edit: If True, renders edit form with pre-filled values

    Returns:
        Dictionary of form values if valid, None otherwise
    """
    # Create form with unique key based on mode
    form_key = "datasource_form_edit" if is_edit else "datasource_form_create"
    with st.form(key=form_key):
        st.markdown("#### " + ("Edit" if is_edit else "Add") + " Data Source")

        sourcename = st.text_input(
            "Source Name *",
            value=datasource_data.get('sourcename', '') if datasource_data else '',
            help="Unique name for this data source (max 50 characters)",
            max_chars=50
        )

        description = st.text_area(
            "Description",
            value=datasource_data.get('description', '') if datasource_data else '',
            help="Optional description of this data source",
            height=100
        )

        submitted = st.form_submit_button(
            "💾 " + ("Update" if is_edit else "Add") + " Data Source",
            use_container_width=True
        )

        if submitted:
            errors = []

            # Validate required fields
            is_valid, error = validate_required(sourcename, "Source Name")
            if not is_valid:
                errors.append(error)

            is_valid, error = validate_max_length(sourcename, 50, "Source Name")
            if not is_valid:
                errors.append(error)

            # Display errors
            if errors:
                for error in errors:
                    show_error(error)
                return None

            return {
                'sourcename': sourcename.strip(),
                'description': description.strip() if description else None
            }

    return None


def render_datasettype_form(
    datasettype_data: Optional[Dict[str, Any]] = None,
    is_edit: bool = False
) -> Optional[Dict[str, str]]:
    """
    Render the dataset type form.

    Args:
        datasettype_data: Existing dataset type data (for edit mode)
        is_edit: If True, renders edit form with pre-filled values

    Returns:
        Dictionary of form values if valid, None otherwise
    """
    # Create form with unique key based on mode
    form_key = "datasettype_form_edit" if is_edit else "datasettype_form_create"
    with st.form(key=form_key):
        st.markdown("#### " + ("Edit" if is_edit else "Add") + " Dataset Type")

        typename = st.text_input(
            "Type Name *",
            value=datasettype_data.get('typename', '') if datasettype_data else '',
            help="Unique name for this dataset type (max 50 characters)",
            max_chars=50
        )

        description = st.text_area(
            "Description",
            value=datasettype_data.get('description', '') if datasettype_data else '',
            help="Optional description of this dataset type",
            height=100
        )

        submitted = st.form_submit_button(
            "💾 " + ("Update" if is_edit else "Add") + " Dataset Type",
            use_container_width=True
        )

        if submitted:
            errors = []

            # Validate required fields
            is_valid, error = validate_required(typename, "Type Name")
            if not is_valid:
                errors.append(error)

            is_valid, error = validate_max_length(typename, 50, "Type Name")
            if not is_valid:
                errors.append(error)

            # Display errors
            if errors:
                for error in errors:
                    show_error(error)
                return None

            return {
                'typename': typename.strip(),
                'description': description.strip() if description else None
            }

    return None
