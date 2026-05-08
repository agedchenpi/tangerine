"""The Far Side Gallery — browse scraped daily comics with filtering."""

from datetime import date
from pathlib import Path

import streamlit as st

from components.notifications import show_info
from services.farside_service import get_comic_count, get_comics, get_date_range
from utils.ui_helpers import add_page_header, load_custom_css

load_custom_css()
add_page_header("The Far Side", icon="🐄", subtitle="Daily comics by Gary Larson")

IMAGE_DIR = Path("/app/data/images/farside")
COLS = 3
PAGE_SIZE = 30

# ── Sidebar filters ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")

    db_range = get_date_range()
    min_date = db_range["min_date"] or date(2020, 1, 1)
    max_date = db_range["max_date"] or date.today()

    st.markdown("**Date Range**")
    date_from = st.text_input("Start date", value=str(min_date),
                              key="fs_date_from", help="YYYY-MM-DD")
    date_to = st.text_input("End date", value=str(max_date),
                            key="fs_date_to", help="YYYY-MM-DD")

    # Validate date strings
    from datetime import datetime as _dt
    try:
        date_from = _dt.strptime(date_from.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        date_from = min_date
    try:
        date_to = _dt.strptime(date_to.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        date_to = max_date

    st.markdown("**Search**")
    search = st.text_input(
        "Search",
        placeholder="e.g. cow, scientist, bugs, dog",
        key="fs_search",
        label_visibility="collapsed",
        help="Searches comic captions and visible text (signs, labels, speech bubbles)",
    )
    search = search.strip() or None

# ── Pagination state ─────────────────────────────────────────────────────────
if "fs_page" not in st.session_state:
    st.session_state["fs_page"] = 0

# Reset page when filters change
filter_key = f"{date_from}|{date_to}|{search}"
if st.session_state.get("_fs_filter_key") != filter_key:
    st.session_state["_fs_filter_key"] = filter_key
    st.session_state["fs_page"] = 0

page = st.session_state["fs_page"]
offset = page * PAGE_SIZE

# ── Query ────────────────────────────────────────────────────────────────────
total = get_comic_count(
    date_from=str(date_from), date_to=str(date_to), search=search
)

if total == 0:
    show_info("No comics found. Run the Far Side scraper to populate the gallery.")
    st.stop()

comics = get_comics(
    date_from=str(date_from), date_to=str(date_to), search=search,
    limit=PAGE_SIZE, offset=offset,
)

total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
st.caption(f"{total} comics  ·  Page {page + 1} of {total_pages}")

# ── Gallery grid (grouped by date) ──────────────────────────────────────────
current_date = None

for comic in comics:
    comic_date = str(comic["comic_date"])

    # Date header when date changes
    if comic_date != current_date:
        current_date = comic_date
        st.markdown(f"### {comic_date}")
        col_idx = 0
        cols = st.columns(COLS)

    col = cols[col_idx % COLS]
    with col:
        # Try local file first, fall back to remote URL
        local_path = IMAGE_DIR / comic["local_filename"] if comic.get("local_filename") else None
        if local_path and local_path.exists():
            st.image(str(local_path), use_container_width=True)
        elif comic.get("image_url"):
            st.image(comic["image_url"], use_container_width=True)
        else:
            st.markdown(
                '<div style="background:#2a2a2a;height:200px;display:flex;'
                'align-items:center;justify-content:center;border-radius:8px;'
                'color:#888;">No image</div>',
                unsafe_allow_html=True,
            )

        # Caption below image
        caption_parts = []
        if comic.get("caption"):
            caption_parts.append(f"*{comic['caption']}*")
        if comic.get("alt_text"):
            caption_parts.append(f"_{comic['alt_text']}_")
        if caption_parts:
            st.caption(" ".join(caption_parts))

    col_idx += 1

# ── Pagination controls ──────────────────────────────────────────────────────
st.divider()
nav_prev, nav_info, nav_next = st.columns([1, 2, 1])
with nav_prev:
    if st.button("← Previous", disabled=page == 0, use_container_width=True):
        st.session_state["fs_page"] = page - 1
        st.rerun()
with nav_info:
    st.markdown(
        f"<div style='text-align:center;padding-top:0.4rem;'>"
        f"Page {page + 1} / {total_pages}</div>",
        unsafe_allow_html=True,
    )
with nav_next:
    if st.button("Next →", disabled=page >= total_pages - 1, use_container_width=True):
        st.session_state["fs_page"] = page + 1
        st.rerun()
