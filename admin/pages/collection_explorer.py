"""Collection Explorer — discover museum artworks before importing."""

import pandas as pd
import streamlit as st

from services.collection_explorer_service import (
    GETTY_OBJECT_TYPES,
    _build_getty_sparql,
    discover_getty_manifests,
    discover_smithsonian_artworks,
    get_imported_manifest_ids,
)
from utils.ui_helpers import load_custom_css, add_page_header

load_custom_css()
add_page_header("Collection Explorer", icon="🔭")
st.caption("Discover available museum artworks before importing.")

tab_getty, tab_si = st.tabs(["Getty Museum", "Smithsonian Asian Art"])


# ── Getty tab ─────────────────────────────────────────────────────────────── #

with tab_getty:
    # Object Type
    selected_type_names = st.multiselect(
        "Object Type",
        options=list(GETTY_OBJECT_TYPES.keys()),
        default=["Paintings"],
        key="getty_object_types",
    )
    selected_type_aats = [GETTY_OBJECT_TYPES[t] for t in selected_type_names]

    # Date Range
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        date_from = st.number_input(
            "Date From (year, optional)",
            min_value=1,
            max_value=2100,
            step=1,
            value=None,
            key="getty_date_from",
            placeholder="e.g. 1400",
        )
    with date_col2:
        date_to = st.number_input(
            "Date To (year, optional)",
            min_value=1,
            max_value=2100,
            step=1,
            value=None,
            key="getty_date_to",
            placeholder="e.g. 1600",
        )

    # Culture
    culture = st.text_input(
        "Culture (optional)",
        value="",
        placeholder="e.g. China, Japan",
        key="getty_culture",
    )

    # Medium
    medium = st.text_input(
        "Medium (optional)",
        value="",
        placeholder="e.g. oil, watercolor",
        key="getty_medium",
    )

    # SPARQL expander
    if selected_type_aats:
        sparql_preview = _build_getty_sparql(
            selected_type_aats,
            int(date_from) if date_from is not None else None,
            int(date_to) if date_to is not None else None,
            culture,
            medium,
        )
    else:
        sparql_preview = "# Select at least one Object Type to generate a query."
    with st.expander("Generated SPARQL"):
        st.code(sparql_preview, language="sparql")

    # Discover button
    if st.button(
        "Discover",
        key="getty_discover",
        type="primary",
        disabled=not selected_type_aats,
    ):
        with st.spinner("Querying Getty SPARQL endpoint…"):
            try:
                manifests = discover_getty_manifests(
                    object_type_aats=selected_type_aats,
                    date_from=int(date_from) if date_from is not None else None,
                    date_to=int(date_to) if date_to is not None else None,
                    culture=culture,
                    medium=medium,
                )
                imported = get_imported_manifest_ids()
                st.session_state["getty_results"] = manifests
                st.session_state["getty_imported"] = imported
            except Exception as e:
                st.error(f"Discovery failed: {e}")

    if "getty_results" in st.session_state:
        manifests: list[dict] = st.session_state["getty_results"]
        imported: set[str] = st.session_state["getty_imported"]

        total = len(manifests)
        already = sum(1 for m in manifests if m["uuid"] in imported)
        new_count = total - already

        col1, col2, col3 = st.columns(3)
        col1.metric("Discovered", total)
        col2.metric("Already Imported", already)
        col3.metric("New", new_count)

        rows = []
        for m in manifests:
            status = "✅ Imported" if m["uuid"] in imported else "🆕 New"
            rows.append({
                "UUID":         m["uuid"],
                "Title":        m.get("title", ""),
                "Manifest URL": m["manifest_url"],
                "Status":       status,
            })

        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Manifest URL": st.column_config.LinkColumn("Manifest URL"),
            },
        )


# ── Smithsonian tab ───────────────────────────────────────────────────────── #

UNIT_OPTIONS = {
    "FSG":   "National Museum of Asian Art (Freer|Sackler)",
    "SAAM":  "Smithsonian American Art Museum",
    "CHNDM": "Cooper Hewitt Design Museum",
    "HMSG":  "Hirshhorn Museum and Sculpture Garden",
    "NPG":   "National Portrait Gallery",
    "NMAI":  "National Museum of the American Indian",
    "NMAH":  "National Museum of American History",
    "NMNH":  "National Museum of Natural History",
}

OBJECT_TYPES = ["Paintings", "Drawings", "Prints", "Sculpture", "Ceramics", "Photographs", "Textiles"]

with tab_si:
    # Museum Unit
    unit_codes = st.multiselect(
        "Museum Unit",
        options=list(UNIT_OPTIONS.keys()),
        default=["FSG"],
        format_func=lambda k: f"{k} — {UNIT_OPTIONS[k]}",
        key="si_units",
    )

    # Object Type — 4-column grid of checkboxes
    st.markdown("**Object Type**")
    cols = st.columns(4)
    selected_types = []
    for i, obj_type in enumerate(OBJECT_TYPES):
        default_checked = (obj_type == "Paintings")
        if cols[i % 4].checkbox(obj_type, value=default_checked, key=f"si_type_{obj_type}"):
            selected_types.append(obj_type)

    # Place / Region
    place = st.text_input("Place / Region (optional)", value="", key="si_place")

    # Extra keywords
    extra_keywords = st.text_input("Additional keywords (optional)", value="", key="si_extra")

    # Build query
    parts = []
    if unit_codes:
        parts.append("(" + " OR ".join(f"unit_code:{u}" for u in unit_codes) + ")")
    if selected_types:
        parts.append("(" + " OR ".join(f'object_type:"{t}"' for t in selected_types) + ")")
    if place:
        parts.append(f"place:{place}")
    if extra_keywords:
        parts.append(extra_keywords)
    query = " AND ".join(parts) if parts else "*"

    with st.expander("Generated query"):
        st.code(query, language="text")

    if st.button("Search", key="si_search", type="primary", disabled=not unit_codes):
        with st.spinner("Querying Smithsonian Open Access API…"):
            try:
                artworks = discover_smithsonian_artworks(query=query)
                imported = get_imported_manifest_ids()
                st.session_state["si_results"] = artworks
                st.session_state["si_imported"] = imported
            except Exception as e:
                st.error(f"Search failed: {e}")

    if "si_results" in st.session_state:
        artworks: list[dict] = st.session_state["si_results"]
        imported: set[str] = st.session_state["si_imported"]

        total = len(artworks)
        already = sum(1 for a in artworks if a["manifest_id"] and a["manifest_id"] in imported)
        new_count = total - already

        col1, col2, col3 = st.columns(3)
        col1.metric("Discovered", total)
        col2.metric("Already Imported", already)
        col3.metric("New", new_count)

        rows = []
        for a in artworks:
            status = "✅ Imported" if a["manifest_id"] and a["manifest_id"] in imported else "🆕 New"
            rows.append({
                "Manifest ID": a["manifest_id"],
                "Title":       a["title"],
                "Type":        a["object_type"],
                "Date":        a["date"],
                "Media":       a["media_count"],
                "Status":      status,
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
