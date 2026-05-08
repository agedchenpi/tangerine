"""The Far Side Gallery — browse scraped daily comics with filtering."""

from datetime import date
from pathlib import Path

import streamlit as st

from components.notifications import show_error, show_info, show_success
from services.farside_service import (
    get_comic_count, get_comics, get_date_range, scrape_date, scrape_range,
)
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

    # ── Scrape controls ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Scrape Comics")

    with st.expander("Single Date", expanded=False):
        scrape_single = st.text_input(
            "Date to scrape", value=str(date.today()),
            key="fs_scrape_single", help="YYYY-MM-DD — pulls or re-pulls comics for this date",
        )
        if st.button("Scrape Date", key="fs_btn_scrape_single", use_container_width=True):
            with st.spinner(f"Scraping {scrape_single}..."):
                result = scrape_date(scrape_single.strip())
            if result["success"]:
                show_success(result["message"])
                st.rerun()
            else:
                show_error(result["message"])

    with st.expander("Date Range (Backfill)", expanded=False):
        scrape_start = st.text_input(
            "Start date", key="fs_scrape_start", help="YYYY-MM-DD",
        )
        scrape_end = st.text_input(
            "End date", value=str(date.today()),
            key="fs_scrape_end", help="YYYY-MM-DD",
        )
        sleep_secs = st.number_input(
            "Delay between dates (seconds)", value=2.0, min_value=0.5,
            max_value=10.0, step=0.5, key="fs_sleep",
        )
        if st.button("Start Backfill", key="fs_btn_backfill", use_container_width=True):
            start_val = (scrape_start or "").strip()
            end_val = (scrape_end or "").strip()
            if not start_val:
                show_error("Start date is required.")
            else:
                progress_bar = st.progress(0, text="Starting backfill...")
                status_text = st.empty()

                def _progress(idx, total, ds, res):
                    pct = idx / total
                    label = f"{idx}/{total} — {ds}"
                    if res.get("skipped"):
                        label += " (skipped)"
                    elif res.get("success"):
                        label += f" — {res.get('comics_added', 0)} comics"
                    else:
                        label += " — FAILED"
                    progress_bar.progress(pct, text=label)

                result = scrape_range(start_val, end_val, sleep_secs, _progress)
                progress_bar.empty()

                msg = (f"Done: {result['scraped']} scraped, "
                       f"{result['skipped']} skipped, {result['failed']} failed "
                       f"(out of {result['total']} dates)")
                if result["success"]:
                    show_success(msg)
                else:
                    show_error(msg)
                st.rerun()

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
