"""YouTube Downloader — download MP4 video or MP3 audio from a YouTube URL."""

import streamlit as st

from components.notifications import show_error, show_info, show_success
from services.youtube_downloader_service import download_media, get_video_info
from utils.ui_helpers import add_page_header, load_custom_css

load_custom_css()
add_page_header("YouTube Downloader", icon="📥", subtitle="Save video or audio from YouTube")


def _fmt_duration(seconds: int) -> str:
    if not seconds:
        return "—"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _make_progress_hook(progress_bar, status_text):
    """Return a yt-dlp progress hook that updates Streamlit UI elements."""
    stream_idx = [0]  # track which stream we're on (video then audio)

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            dl = d.get("downloaded_bytes", 0)
            if total > 0:
                # Cap at 0.9 so the bar doesn't sit at 100% during FFmpeg merge
                progress_bar.progress(min(dl / total, 0.90))
            pct = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "?")
            eta = d.get("_eta_str", "?")
            status_text.text(f"Downloading… {pct}  |  {speed}  |  ETA {eta}")
        elif d["status"] == "finished":
            stream_idx[0] += 1
            status_text.text("Finalizing with FFmpeg…")
            progress_bar.progress(0.95)

    return hook


# ── URL input ─────────────────────────────────────────────────────────────────
url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=...",
    label_visibility="collapsed",
)

# Clear cached info when URL changes
if url != st.session_state.get("_yt_url"):
    st.session_state.pop("_yt_info", None)
    st.session_state.pop("_yt_result", None)
    st.session_state["_yt_url"] = url

# ── Load Info ─────────────────────────────────────────────────────────────────
col_btn, col_spacer = st.columns([1, 4])
with col_btn:
    load_clicked = st.button("Load Info", use_container_width=True)

if load_clicked and url:
    with st.spinner("Fetching metadata…"):
        try:
            st.session_state["_yt_info"] = get_video_info(url)
            st.session_state.pop("_yt_result", None)
        except Exception as exc:
            show_error(f"Could not load video info: {exc}")

info = st.session_state.get("_yt_info")

# ── Video preview card ────────────────────────────────────────────────────────
if info:
    st.divider()
    thumb_col, meta_col = st.columns([1, 2])
    with thumb_col:
        if info["thumbnail"]:
            st.image(info["thumbnail"], use_container_width=True)
    with meta_col:
        st.markdown(f"### {info['title']}")
        st.caption(
            f"🎬 {info['uploader']}  ·  ⏱ {_fmt_duration(info['duration'])}"
            + (f"  ·  👁 {info['view_count']:,}" if info.get("view_count") else "")
        )

# ── Format & quality settings ─────────────────────────────────────────────────
st.divider()
fmt_col, qual_col = st.columns(2)

with fmt_col:
    st.markdown("**Format**")
    mode = st.radio(
        "Format",
        ["MP4 (Video)", "MP3 (Audio)"],
        label_visibility="collapsed",
        horizontal=True,
    )

with qual_col:
    st.markdown("**Quality**")
    if mode == "MP4 (Video)":
        quality_label = st.selectbox(
            "Quality", ["1080p", "720p", "480p"], label_visibility="collapsed"
        )
        quality = quality_label.replace("p", "")
        dl_mode = "mp4"
        mime = "video/mp4"
    else:
        quality_label = st.selectbox(
            "Quality", ["320 kbps", "128 kbps"], label_visibility="collapsed"
        )
        quality = quality_label.split()[0]  # "320" or "128"
        dl_mode = "mp3"
        mime = "audio/mpeg"

# ── Download ──────────────────────────────────────────────────────────────────
st.divider()

if not url:
    show_info("Paste a YouTube URL above to get started.")
else:
    dl_col, spacer = st.columns([1, 3])
    with dl_col:
        download_clicked = st.button(
            f"⬇️ Download {quality_label}",
            type="primary",
            use_container_width=True,
            disabled=not url,
        )

    if download_clicked:
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        hook = _make_progress_hook(progress_bar, status_text)

        try:
            file_bytes, filename, file_mime = download_media(
                url, dl_mode, quality, progress_hook=hook
            )
            progress_bar.progress(1.0)
            status_text.empty()
            st.session_state["_yt_result"] = {
                "bytes": file_bytes,
                "filename": filename,
                "mime": file_mime,
            }
        except Exception as exc:
            progress_bar.empty()
            status_text.empty()
            show_error(f"Download failed: {exc}")

# Show download button if a result is ready
result = st.session_state.get("_yt_result")
if result:
    show_success("Ready to save!")
    st.download_button(
        label=f"💾 Save  {result['filename']}",
        data=result["bytes"],
        file_name=result["filename"],
        mime=result["mime"],
        use_container_width=False,
    )
