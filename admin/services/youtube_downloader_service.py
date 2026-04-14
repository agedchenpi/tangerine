"""Service layer for YouTube Downloader — yt-dlp calls, no UI imports."""

import os
import re
import tempfile
from typing import Callable


def get_video_info(url: str) -> dict:
    """Fetch video metadata without downloading.

    Returns dict with: id, title, duration, uploader, thumbnail.
    Raises on invalid URL or network error.
    """
    import yt_dlp

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "id": info.get("id", ""),
        "title": info.get("title", "Unknown"),
        "duration": info.get("duration") or 0,          # seconds
        "uploader": info.get("uploader") or info.get("channel") or "Unknown",
        "thumbnail": info.get("thumbnail", ""),
        "view_count": info.get("view_count"),
    }


def _safe_filename(title: str, ext: str) -> str:
    """Sanitize video title for use as a download filename."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title)
    safe = safe.strip(". ")[:200]
    return f"{safe}.{ext}"


def download_media(
    url: str,
    mode: str,
    quality: str,
    progress_hook: Callable | None = None,
) -> tuple[bytes, str, str]:
    """Download video or audio and return (file_bytes, filename, mime_type).

    Args:
        url:           YouTube URL
        mode:          "mp4" or "mp3"
        quality:       "1080" / "720" / "480" for mp4; "320" / "128" for mp3
        progress_hook: optional yt-dlp progress hook callable

    Returns:
        (bytes, filename, mime) ready for st.download_button
    """
    import yt_dlp

    hooks = [progress_hook] if progress_hook else []

    with tempfile.TemporaryDirectory() as tmp_dir:
        outtmpl = os.path.join(tmp_dir, "%(id)s.%(ext)s")

        if mode == "mp4":
            fmt = (
                f"bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]"
                f"/bestvideo[height<={quality}]+bestaudio"
                f"/best[height<={quality}]"
            )
            ydl_opts = {
                "format": fmt,
                "merge_output_format": "mp4",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 3,
                "progress_hooks": hooks,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            out_path = os.path.join(tmp_dir, f"{info['id']}.mp4")
            filename = _safe_filename(info.get("title", info["id"]), "mp4")
            mime = "video/mp4"

        else:  # mp3
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 3,
                "progress_hooks": hooks,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            # FFmpegExtractAudio renames the file to .mp3
            out_path = os.path.join(tmp_dir, f"{info['id']}.mp3")
            filename = _safe_filename(info.get("title", info["id"]), "mp3")
            mime = "audio/mpeg"

        with open(out_path, "rb") as f:
            data = f.read()

    return data, filename, mime
