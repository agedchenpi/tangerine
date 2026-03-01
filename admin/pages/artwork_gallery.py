"""Artwork Gallery — browse and view IIIF artworks with provenance."""

import streamlit as st
from pathlib import Path

from services.artwork_service import get_artworks, get_provenance, get_artwork_topics, get_rights_values
from utils.ui_helpers import load_custom_css, add_page_header

load_custom_css()
add_page_header("Artwork Gallery", icon="🖼️")

IMAGE_DIR = Path("/app/data/images/iiif")

# ── Sidebar filters ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")

    source_options = ["All", "Freer Gallery", "Getty Museum"]
    selected_source = st.selectbox("Source", source_options, key="gallery_source")
    source_filter = None if selected_source == "All" else selected_source

    try:
        rights_values = get_rights_values()
    except Exception:
        rights_values = []
    rights_options = ["All"] + rights_values
    selected_rights = st.selectbox("Rights", rights_options, key="gallery_rights")
    rights_filter = None if selected_rights == "All" else selected_rights

    try:
        all_topics = get_artwork_topics()
    except Exception:
        all_topics = []
    topic_filter = st.selectbox(
        "Topic",
        ["All"] + all_topics,
        key="gallery_topic",
        help="Filter to artworks that include this topic"
    )
    topic_value = None if topic_filter == "All" else topic_filter

# ── Load data ────────────────────────────────────────────────────────────────
try:
    artworks = get_artworks(source=source_filter, rights=rights_filter, topic=topic_value)
except Exception as e:
    st.error(f"Error loading artworks: {e}")
    st.stop()

count = len(artworks)
st.caption(f"{count} artwork{'s' if count != 1 else ''} found")

if not artworks:
    st.info("No artworks match the current filters.")
    st.stop()

# ── Gallery grid ─────────────────────────────────────────────────────────────
COLS = 3

for row_start in range(0, len(artworks), COLS):
    row_artworks = artworks[row_start : row_start + COLS]
    cols = st.columns(COLS)

    for col, record in zip(cols, row_artworks):
        with col:
            # Thumbnail image
            img_path = IMAGE_DIR / record["local_filename"] if record.get("local_filename") else None
            if img_path and img_path.exists():
                st.image(str(img_path), use_column_width=True)
            elif record.get("image_url"):
                st.image(record["image_url"], use_column_width=True)
            else:
                st.markdown(
                    "<div style='height:160px;background:#f0f0f0;display:flex;"
                    "align-items:center;justify-content:center;border-radius:4px;"
                    "color:#999;font-size:13px'>No image</div>",
                    unsafe_allow_html=True,
                )

            # Title + accession
            st.markdown(f"**{record['title']}**")
            if record.get("accession_number"):
                st.caption(record["accession_number"])

            # Source badge
            mid = record.get("manifest_id", "")
            source_label = "Freer Gallery" if mid.startswith("FS-") else "Getty Museum"
            st.caption(f"📍 {source_label}")

            # Detail expander
            with st.expander("View Details"):
                details = {
                    "Medium": record.get("medium"),
                    "Date": record.get("date_text"),
                    "Period": record.get("period"),
                    "Origin": record.get("origin"),
                    "Type": record.get("artwork_type"),
                    "Artist": record.get("artist"),
                    "Collection": record.get("collection"),
                    "Credit": record.get("credit_line"),
                    "Rights": record.get("metadata_usage"),
                }
                for label, value in details.items():
                    if value:
                        st.markdown(f"**{label}:** {value}")

                # Topics
                topics = record.get("topics") or []
                if topics:
                    st.markdown("**Topics:**")
                    st.markdown(" ".join(f"`{t}`" for t in topics))

                # Provenance
                try:
                    prov = get_provenance(record["record_id"])
                except Exception:
                    prov = []

                if prov:
                    st.markdown("**Provenance:**")
                    import pandas as pd
                    df = pd.DataFrame([
                        {
                            "#": p["sequence_order"],
                            "Holder": p["holder_name"],
                            "Dates": p.get("holder_dates") or "",
                            "Location": p.get("location") or "",
                            "Notes": p.get("acquisition_notes") or "",
                        }
                        for p in prov
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)
