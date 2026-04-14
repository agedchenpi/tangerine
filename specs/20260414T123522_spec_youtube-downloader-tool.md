# Plan: YouTube Downloader Tool

## Context
Adding a new "YouTube Downloader" page to the Tools group in the Tangerine admin interface. Given a YouTube URL, the user can download either an MP4 video or MP3 audio file at a chosen quality level, with live progress tracking and a browser download button.

**Library choice: `yt-dlp`** — the only viable Python library in 2025/2026. `pytube` and `youtube-dl` are unmaintained/broken against YouTube's current anti-bot measures. `yt-dlp` has 157k stars, ships extractor fixes within days of YouTube changes, and has a clean Python API. License: The Unlicense (public domain).

**FFmpeg**: Already installed in `Dockerfile.streamlit` (used by music visualizer) — no Dockerfile changes needed.

## Files to Create / Modify

| File | Action |
|------|--------|
| `requirements/admin.txt` | Add `yt-dlp>=2025.1.0` |
| `admin/services/youtube_downloader_service.py` | New service — yt-dlp calls, no UI |
| `admin/pages/youtube_downloader.py` | New page — Streamlit UI |
| `admin/app.py` | Register page in Tools group |

## Implementation

### 1. `requirements/admin.txt`
Add under the Music Visualizer section:
```
# YouTube Downloader
yt-dlp>=2025.1.0   # YouTube/video download engine (ffmpeg already present)
```

### 2. `admin/services/youtube_downloader_service.py`

Two functions:

**`get_video_info(url) → dict`**
- Uses `yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True})`
- `ydl.extract_info(url, download=False)`
- Returns: `title`, `duration` (seconds), `uploader`, `thumbnail` (URL), `id`

**`download_media(url, mode, quality, progress_hook) → (bytes, filename)`**
- `mode`: `"mp4"` or `"mp3"`
- `quality`: `"1080"` / `"720"` / `"480"` for MP4; `"320"` / `"128"` for MP3
- Downloads into a `tempfile.TemporaryDirectory`
- Uses `outtmpl: %(id)s.%(ext)s` (safe server-side filename)
- Returns raw bytes + sanitized human filename for the download button
- MP4 format string: `bestvideo[height<=Q][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=Q]+bestaudio/best[height<=Q]` with `merge_output_format: mp4`
- MP3: `format: bestaudio/best` + `FFmpegExtractAudio` postprocessor with `preferredcodec: mp3`
- `noplaylist: True` always (no accidental playlist downloads)
- `retries: 3`

### 3. `admin/pages/youtube_downloader.py`

**UI layout:**

```
[Page header: "YouTube Downloader" 📥]

[URL text input — full width, paste area]

[Load Info button]
  → on click: fetch metadata, show thumbnail + title + duration + uploader
    (cached in session state so it doesn't refetch on every rerun)

[Two columns:]
  Left: Format radio   →  MP4 (Video) | MP3 (Audio)
  Right: Quality select → changes based on format
    MP4: 1080p / 720p / 480p
    MP3: 320 kbps / 128 kbps

[Download button — primary]
  → st.spinner wrapping download_media()
  → Progress bar + status text updated via progress_hook
  → On completion: st.download_button with file bytes

[Error display via show_error()]
```

**Session state keys:**
- `_yt_info`: cached metadata dict (cleared when URL changes)
- `_yt_url`: last loaded URL (for cache invalidation)
- `_yt_result`: `{bytes, filename, mime}` after successful download

**Progress hook pattern** (runs in same thread as yt-dlp, safe to update Streamlit elements):
```python
def _make_hook(progress_bar, status_text):
    def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            dl = d.get('downloaded_bytes', 0)
            if total > 0:
                progress_bar.progress(min(dl / total, 0.95))
            status_text.text(f"{d.get('_percent_str','').strip()} at {d.get('_speed_str','?')} | ETA {d.get('_eta_str','?')}")
        elif d['status'] == 'finished':
            status_text.text("Finalizing with FFmpeg...")
    return hook
```

### 4. `admin/app.py`
In the Tools page group (currently Media Editor + Music Visualizer), add:
```python
st.Page("pages/youtube_downloader.py", title="YouTube Downloader", icon="📥"),
```

## Verification

1. Rebuild Docker image: `docker compose build admin && docker compose up -d admin`
2. Navigate to Tools → YouTube Downloader
3. Paste a YouTube URL → click Load Info → verify thumbnail/title/duration appear
4. Select MP4 720p → Download → verify progress bar advances → download button appears → file plays
5. Select MP3 320k → Download → verify .mp3 saves and plays
6. Test with a YouTube Short URL
7. Test error case: paste an invalid URL → verify `show_error` displays cleanly
