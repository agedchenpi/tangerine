"""Music Visualizer — generate MP4 videos with bar waveform animations from audio."""

import logging
import os
import subprocess
import tempfile
import time

import numpy as np
import streamlit as st

from utils.ui_helpers import load_custom_css, add_page_header
from components.notifications import show_success, show_error, show_warning, show_info

logger = logging.getLogger("music_visualizer")

load_custom_css()
add_page_header("Music Visualizer", icon="\U0001f3b5")

# ── Color presets ─────────────────────────────────────────────────────────────
COLOR_PRESETS = {
    "Cyan / Dark": {"bg": (10, 10, 30), "bar": (0, 255, 255), "glow": (0, 200, 255)},
    "Orange / Dark": {"bg": (15, 10, 5), "bar": (255, 140, 0), "glow": (255, 100, 0)},
    "Green / Dark": {"bg": (5, 15, 5), "bar": (0, 255, 100), "glow": (0, 200, 80)},
    "Purple / Dark": {"bg": (15, 5, 25), "bar": (180, 80, 255), "glow": (140, 40, 220)},
    "White / Black": {"bg": (0, 0, 0), "bar": (255, 255, 255), "glow": (200, 200, 200)},
}


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _compute_bar_colors(n_bars: int, bass_rgb: tuple, treble_rgb: tuple) -> np.ndarray:
    """Linearly interpolate between bass and treble colors across n_bars."""
    t = np.linspace(0, 1, n_bars).reshape(-1, 1)
    bass = np.array(bass_rgb, dtype=np.float64)
    treble = np.array(treble_rgb, dtype=np.float64)
    return np.clip(bass * (1 - t) + treble * t, 0, 255).astype(np.uint8)


# ── Audio analysis ────────────────────────────────────────────────────────────
def _analyze_audio(audio_path: str, fps: int, n_bars: int,
                   offset: float = 0.0, trim_duration: float | None = None):
    """Run STFT and beat tracking. Returns (sr, duration, spectrum, beat_mask, energy)."""
    import librosa

    y, sr = librosa.load(audio_path, sr=None, mono=True, offset=offset, duration=trim_duration)
    duration = len(y) / sr

    hop_length = max(1, sr // fps)
    S = np.abs(librosa.stft(y, n_fft=4096, hop_length=hop_length))

    # Log-spaced frequency bands
    n_freq = S.shape[0]
    band_edges = np.logspace(0, np.log10(n_freq), n_bars + 1, dtype=int)
    band_edges = np.clip(band_edges, 0, n_freq)
    # Ensure unique edges
    for i in range(1, len(band_edges)):
        if band_edges[i] <= band_edges[i - 1]:
            band_edges[i] = band_edges[i - 1] + 1
    band_edges = np.clip(band_edges, 0, n_freq)

    n_frames = S.shape[1]
    spectrum = np.zeros((n_frames, n_bars), dtype=np.float32)
    for b in range(n_bars):
        lo, hi = band_edges[b], band_edges[b + 1]
        if lo < hi and lo < n_freq:
            spectrum[:, b] = S[lo:min(hi, n_freq), :].mean(axis=0)

    # Normalize to 0-1
    mx = spectrum.max()
    if mx > 0:
        spectrum /= mx

    # EMA temporal smoothing — reduces frame-to-frame flicker
    for i in range(1, n_frames):
        spectrum[i] = 0.45 * spectrum[i] + 0.55 * spectrum[i - 1]

    # RMS energy per frame, normalized to 0-1
    frame_len = max(1, sr // fps)
    n_samples = n_frames * frame_len
    y_padded = np.pad(y, (0, max(0, n_samples - len(y))))[:n_samples]
    _frames = y_padded.reshape(n_frames, frame_len).astype(np.float32)
    raw_energy = np.sqrt((_frames ** 2).mean(axis=1))
    e_max = raw_energy.max()
    energy = raw_energy / e_max if e_max > 0 else raw_energy

    # Beat tracking
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    beat_mask = np.zeros(n_frames, dtype=np.float32)
    for bf in beat_frames:
        if bf < n_frames:
            beat_mask[bf] = 1.0
    # Decay beat pulses over a few frames
    for i in range(1, n_frames):
        beat_mask[i] = max(beat_mask[i], beat_mask[i - 1] * 0.85)

    return sr, duration, spectrum, beat_mask, energy


# ── Waveform / spectral energy preview ───────────────────────────────────────
def _render_audio_preview(y, sr, dur_info, trim_start: float, trim_end: float | None):
    """Return a matplotlib Figure with waveform + spectral energy plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import librosa

    total_dur = dur_info if dur_info else len(y) / sr

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 3), facecolor="#0a0a1e")
    fig.subplots_adjust(hspace=0.35)

    # Downsample to ~3000 points
    step = max(1, len(y) // 3000)
    t = np.linspace(0, total_dur, len(y[::step]))
    y_ds = y[::step]

    # ── Waveform ──────────────────────────────────────────────────────────────
    ax1.set_facecolor("#0a0a1e")
    ax1.plot(t, y_ds, color="#00c8ff", linewidth=0.5, alpha=0.9)

    # Shade trimmed-out regions
    if trim_start > 0:
        ax1.axvspan(0, trim_start, alpha=0.35, color="#ff4444", lw=0)
    if trim_end is not None and trim_end < total_dur:
        ax1.axvspan(trim_end, total_dur, alpha=0.35, color="#ff4444", lw=0)

    ax1.set_xlim(0, total_dur)
    ax1.set_ylabel("Amplitude", color="#aaaacc", fontsize=7)
    ax1.tick_params(colors="#aaaacc", labelsize=7)
    for spine in ax1.spines.values():
        spine.set_edgecolor("#222244")

    # ── Spectral energy (RMS) ─────────────────────────────────────────────────
    rms = librosa.feature.rms(y=y)[0]
    t_rms = np.linspace(0, total_dur, len(rms))

    ax2.set_facecolor("#0a0a1e")
    ax2.fill_between(t_rms, rms, color="#00c8ff", alpha=0.55)
    ax2.plot(t_rms, rms, color="#00c8ff", linewidth=0.6)

    if trim_start > 0:
        ax2.axvspan(0, trim_start, alpha=0.35, color="#ff4444", lw=0)
    if trim_end is not None and trim_end < total_dur:
        ax2.axvspan(trim_end, total_dur, alpha=0.35, color="#ff4444", lw=0)

    ax2.set_xlim(0, total_dur)
    ax2.set_ylabel("Energy", color="#aaaacc", fontsize=7)
    ax2.set_xlabel("Time (s)", color="#aaaacc", fontsize=7)
    ax2.tick_params(colors="#aaaacc", labelsize=7)
    for spine in ax2.spines.values():
        spine.set_edgecolor("#222244")

    return fig


# ── GIF preview ───────────────────────────────────────────────────────────────
def _render_gif_preview(audio_path: str, settings: dict) -> bytes:
    """Render 30 evenly-spaced frames at half resolution and return GIF bytes."""
    from PIL import Image
    import io

    preview_settings = {**settings, "width": settings["width"] // 2, "height": settings["height"] // 2}
    w, h = preview_settings["width"], preview_settings["height"]
    fps = settings["fps"]
    n_bars = settings["n_bars"]

    offset = settings.get("trim_start", 0.0)
    trim_end_raw = settings.get("trim_end")
    trim_dur = (trim_end_raw - offset) if trim_end_raw else None

    sr, duration, spectrum, beat_mask, energy = _analyze_audio(
        audio_path, fps, n_bars, offset=offset, trim_duration=trim_dur
    )

    n_frames = spectrum.shape[0]
    frame_indices = np.linspace(0, n_frames - 1, 30, dtype=int)

    bg_rgb = preview_settings["bg_rgb"]
    glow_rgb = preview_settings["glow_rgb"]
    if preview_settings["gradient"]:
        bar_colors = _compute_bar_colors(n_bars, preview_settings["bass_rgb"], preview_settings["treble_rgb"])
    else:
        bar_colors = np.tile(np.array(preview_settings["bar_rgb"], dtype=np.uint8), (n_bars, 1))

    title_overlay = _make_title_overlay(w, h, preview_settings)
    title_end_frame = None
    if title_overlay is not None:
        display_mode = preview_settings.get("title_display", "Always visible")
        if display_mode != "Always visible":
            title_dur = min(preview_settings.get("title_duration", 5), duration)
            title_end_frame = int(title_dur * fps)

    render_frame = _make_frame_factory(
        w, h, n_bars, spectrum, beat_mask,
        bg_rgb, bar_colors, glow_rgb,
        preview_settings["use_glow"], preview_settings["glow_sigma"], fps,
        energy=energy,
        title_overlay=title_overlay, title_end_frame=title_end_frame,
    )

    pil_frames = []
    for fi in frame_indices:
        raw = render_frame(fi)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
        pil_frames.append(Image.fromarray(arr).quantize(colors=128))

    buf = io.BytesIO()
    pil_frames[0].save(buf, format="GIF", save_all=True,
                       append_images=pil_frames[1:], loop=0, duration=120, optimize=True)
    return buf.getvalue()


# ── Frame rendering ──────────────────────────────────────────────────────────

def _make_title_overlay(width: int, height: int, settings: dict) -> np.ndarray | None:
    """Pre-render title text as an RGBA numpy array using pilmoji.

    pilmoji composites emoji PNGs over the Pillow image, bypassing the
    FreeType CBDT limitation that causes NotoColorEmoji to fail at non-native sizes.
    """
    if not settings.get("title_enabled"):
        return None

    lines = []
    if settings.get("track_name"):
        lines.append(settings["track_name"])
    if settings.get("artist"):
        lines.append(settings["artist"])
    if not lines:
        return None

    from PIL import Image, ImageDraw, ImageFont
    from pilmoji import Pilmoji

    font_size = settings.get("title_fontsize", 36)
    title_color_hex = settings.get("title_color", "#FFFFFF")
    title_rgb = _hex_to_rgb(title_color_hex)
    opacity = int(settings.get("title_opacity", 1.0) * 255)

    try:
        font_text = ImageFont.truetype(
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", font_size
        )
    except OSError:
        font_text = ImageFont.load_default()

    # Measure lines with Liberation Sans; add font_size per non-ASCII char as emoji padding
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    line_bboxes = [draw.textbbox((0, 0), ln, font=font_text) for ln in lines]
    line_heights = [bb[3] - bb[1] for bb in line_bboxes]
    line_widths = [
        (bb[2] - bb[0]) + sum(font_size for c in ln if ord(c) > 0x2000)
        for bb, ln in zip(line_bboxes, lines)
    ]
    total_h = sum(line_heights) + (len(lines) - 1) * 4
    max_w = max(line_widths)

    # Oversized canvas so pilmoji has room to composite emoji PNGs without edge clipping
    canvas_w = max_w + font_size * 6
    canvas_h = total_h + font_size * 2
    txt_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    with Pilmoji(txt_img) as pilmoji:
        y_cursor = 0
        for i, line in enumerate(lines):
            pilmoji.text((0, y_cursor), line, fill=(*title_rgb, opacity), font=font_text)
            y_cursor += line_heights[i] + 4

    # Crop to actual non-transparent content
    bbox = txt_img.getbbox()
    if bbox:
        txt_img = txt_img.crop(bbox)

    txt_arr = np.array(txt_img)  # (h, w, 4) RGBA
    th, tw = txt_arr.shape[:2]

    # Compute position, then clamp so the full overlay stays within the frame
    position = settings.get("title_position", "top-left")
    pad = 20
    if position == "top-left":
        px, py = pad, pad
    elif position == "top-right":
        px, py = width - tw - pad, pad
    elif position == "bottom-left":
        px, py = pad, height - th - pad
    else:  # bottom-right
        px, py = width - tw - pad, height - th - pad

    # Clamp: never let the overlay extend outside the video frame
    px = max(0, min(px, width - tw))
    py = max(0, min(py, height - th))

    y1, y2 = py, py + th
    x1, x2 = px, px + tw

    return {"rgba": txt_arr, "y1": y1, "y2": y2, "x1": x1, "x2": x2}


GLOW_STRENGTH = 1.8


def _make_frame_factory(
    width: int, height: int, n_bars: int,
    spectrum: np.ndarray, beat_mask: np.ndarray,
    bg_rgb: tuple, bar_colors: np.ndarray, glow_rgb: tuple,
    use_glow: bool, glow_sigma: float, fps: int,
    energy: np.ndarray,
    title_overlay: dict | None = None,
    title_end_frame: int | None = None,
):
    """Return a render_frame(fi) closure with pre-computed geometry.

    Composite order: bg + glow_halo + sharp_bars
    - bars are drawn into a float32 bar_layer (never blurred)
    - glow is computed from bar_layer at quarter-res, composited underneath bars
    - EMA-smoothed spectrum + power curve + energy scaling give smooth, full visuals
    - Beat flash accumulator lerps bars toward white over ~5 frames
    """
    import cv2

    gap = max(1, width // (n_bars * 8))
    total_gap = gap * (n_bars - 1)
    bar_w = max(1, (width - total_gap) // n_bars)
    x_starts = np.array([i * (bar_w + gap) for i in range(n_bars)], dtype=int)
    x_ends = x_starts + bar_w

    center_y = height // 2
    max_bar_h = int(height * 0.42)

    bg_float = np.full((height, width, 3), bg_rgb, dtype=np.float32)

    # Pre-allocated buffers — avoids ~25MB allocation every frame
    bar_layer = np.zeros((height, width, 3), dtype=np.float32)
    composite_f = np.empty((height, width, 3), dtype=np.float32)
    result_u8 = np.empty((height, width, 3), dtype=np.uint8)

    # Pre-compute glow kernel size from sigma (must be odd, ≥ 3)
    _ksize = max(3, int(glow_sigma * 2) | 1)

    # Pre-compute title alpha for bounding-box blend
    if title_overlay is not None:
        t_rgba = title_overlay["rgba"]
        ty1, ty2 = title_overlay["y1"], title_overlay["y2"]
        tx1, tx2 = title_overlay["x1"], title_overlay["x2"]
        t_alpha = t_rgba[:, :, 3:4].astype(np.float32) / 255.0
        t_rgb = t_rgba[:, :, :3].astype(np.float32)
    else:
        t_alpha = t_rgb = None
        ty1 = ty2 = tx1 = tx2 = 0

    # Pre-compute bar_colors as float for beat flash
    bar_colors_f = bar_colors.astype(np.float32)
    white = np.full_like(bar_colors_f, 255.0)

    # Mutable beat flash accumulator (list so closure can mutate it)
    flash = [0.0]

    def render_frame(fi: int) -> bytes:
        magnitudes = spectrum[fi]
        beat = beat_mask[fi]

        # ── Beat flash accumulator ────────────────────────────────
        if beat >= 1.0:
            flash[0] = min(flash[0] + 0.55, 1.0)
        flash[0] = max(flash[0] - 0.12, 0.0)
        flash_amt = flash[0] * 0.8

        # Lerp bar colors toward white by flash amount
        if flash_amt > 0:
            colors_f = bar_colors_f * (1.0 - flash_amt) + white * flash_amt
            colors = np.clip(colors_f, 0, 255).astype(np.uint8)
        else:
            colors = bar_colors

        # ── Power curve + energy-reactive bar heights ─────────────
        e_fi = float(energy[fi]) if fi < len(energy) else 0.5
        energy_scale = 0.4 + e_fi * 0.7
        bar_heights = (magnitudes ** 0.6 * energy_scale * max_bar_h).astype(int)

        # ── Draw bars into float32 bar_layer (never blurred) ──────
        bar_layer.fill(0.0)
        for b in range(n_bars):
            bh = bar_heights[b]
            if bh < 1:
                continue
            xs, xe = x_starts[b], x_ends[b]
            y_top = max(0, center_y - bh)
            y_bot = min(height, center_y + bh)
            bar_layer[y_top:center_y, xs:xe] = colors[b]
            bar_layer[center_y:y_bot, xs:xe] = colors[b]

        # ── Composite: bg + glow_halo + sharp bars ────────────────
        if use_glow and glow_sigma > 0:
            small = bar_layer[::4, ::4]
            blurred = cv2.GaussianBlur(small, (_ksize, _ksize), glow_sigma * 0.5)
            glow_layer = cv2.resize(blurred, (width, height), interpolation=cv2.INTER_LINEAR)
            np.add(bg_float, glow_layer * GLOW_STRENGTH, out=composite_f)
            np.add(composite_f, bar_layer, out=composite_f)
        else:
            np.add(bg_float, bar_layer, out=composite_f)
        np.clip(composite_f, 0, 255, out=composite_f)
        result = composite_f.astype(np.uint8)

        # ── Center line subtle brightening ────────────────────────
        result[center_y] = np.clip(result[center_y].astype(np.float32) + 46, 0, 255).astype(np.uint8)

        # ── Title overlay — bounding-box blend only ───────────────
        if t_alpha is not None:
            show_title = title_end_frame is None or fi <= title_end_frame
            if show_title:
                roi = result[ty1:ty2, tx1:tx2].astype(np.float32)
                blended = roi * (1 - t_alpha) + t_rgb * t_alpha
                result[ty1:ty2, tx1:tx2] = blended.astype(np.uint8)

        return result.tobytes()

    return render_frame


# ── Rendering pipeline ───────────────────────────────────────────────────────
def _render_video(
    audio_path: str, settings: dict, progress_status
) -> bytes | None:
    """Full render pipeline: analyze → render frames via ffmpeg pipe → encode.

    Uses direct ffmpeg subprocess instead of moviepy for:
    - Per-frame progress bar with ETA
    - veryfast preset (3-4x faster encoding)
    - Direct audio muxing (no AudioFileClip)
    """
    width = settings["width"]
    height = settings["height"]
    fps = settings["fps"]
    n_bars = settings["n_bars"]

    offset = settings.get("trim_start", 0.0)
    trim_end_raw = settings.get("trim_end")
    trim_dur = (trim_end_raw - offset) if trim_end_raw else None

    # 1. Analyze audio
    progress_status.update(label="Analyzing audio...", state="running")
    sr, duration, spectrum, beat_mask, energy = _analyze_audio(
        audio_path, fps, n_bars, offset=offset, trim_duration=trim_dur
    )

    # 2. Prepare colors
    bg_rgb = settings["bg_rgb"]
    glow_rgb = settings["glow_rgb"]
    if settings["gradient"]:
        bar_colors = _compute_bar_colors(n_bars, settings["bass_rgb"], settings["treble_rgb"])
    else:
        bar_colors = np.tile(np.array(settings["bar_rgb"], dtype=np.uint8), (n_bars, 1))

    # 3. Pre-render title overlay (Pillow, no ImageMagick)
    title_overlay = _make_title_overlay(width, height, settings)
    title_end_frame = None
    if title_overlay is not None:
        display_mode = settings.get("title_display", "Always visible")
        if display_mode != "Always visible":
            title_dur = min(settings.get("title_duration", 5), duration)
            title_end_frame = int(title_dur * fps)

    # 4. Build frame renderer
    progress_status.update(label="Building frame renderer...", state="running")
    render_frame = _make_frame_factory(
        width, height, n_bars, spectrum, beat_mask,
        bg_rgb, bar_colors, glow_rgb,
        settings["use_glow"], settings["glow_sigma"], fps,
        energy=energy,
        title_overlay=title_overlay, title_end_frame=title_end_frame,
    )

    # 5. Pipe frames to ffmpeg
    total_frames = spectrum.shape[0]
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_f:
        out_path = out_f.name

    # Build audio input args with optional trim
    audio_input_args = ["-i", audio_path]
    if offset > 0 or trim_end_raw:
        audio_input_args = [
            "-ss", str(offset),
            *(["-to", str(trim_end_raw)] if trim_end_raw else []),
            "-i", audio_path,
        ]

    crf = str(settings.get("crf", 18))

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        # Raw video input from stdin
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "pipe:0",
        # Audio input (with optional trim)
        *audio_input_args,
        # Video encoding — veryfast is 3-4x faster than medium, negligible quality diff
        "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
        "-tune", "animation",   # optimized for flat-color content (large solid bars)
        "-threads", "0",        # use all logical CPU cores for slice-parallel encoding
        "-pix_fmt", "yuv420p",
        # Audio encoding
        "-c:a", "aac", "-b:a", "192k",
        # Trim to shortest stream
        "-shortest",
        out_path,
    ]

    progress_status.update(label="Rendering frames...", state="running")
    progress_bar = st.progress(0)
    status_text = st.empty()

    proc = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        t_start = time.monotonic()
        for fi in range(total_frames):
            frame_bytes = render_frame(fi)
            proc.stdin.write(frame_bytes)

            # Update progress every 10 frames
            if fi % 10 == 0 or fi == total_frames - 1:
                pct = (fi + 1) / total_frames
                progress_bar.progress(pct)
                elapsed = time.monotonic() - t_start
                if fi > 0:
                    fps_actual = (fi + 1) / elapsed
                    eta = (total_frames - fi - 1) / fps_actual
                    status_text.text(
                        f"Frame {fi + 1}/{total_frames} | {fps_actual:.1f} fps | ETA {eta:.0f}s"
                    )

        proc.stdin.close()
        proc.stdin = None  # prevent communicate() from flushing closed stdin
        _, stderr = proc.communicate(timeout=120)

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed (rc={proc.returncode}): {stderr.decode(errors='replace')[-500:]}")

        with open(out_path, "rb") as f:
            result_bytes = f.read()

    except Exception:
        proc.kill()
        proc.wait()
        raise
    finally:
        progress_bar.empty()
        status_text.empty()
        try:
            os.unlink(out_path)
        except OSError:
            pass

    progress_status.update(label="Done!", state="complete")
    return result_bytes


# ── File upload ───────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload an audio file",
    type=["wav", "mp3", "flac", "ogg", "m4a"],
    help="Supported formats: WAV, MP3, FLAC, OGG, M4A",
)

if uploaded is None:
    show_info("Upload an audio file to get started.")
    st.stop()

# Cache upload bytes in session state; clear derived state on new file
if st.session_state.get("_mv_audio_name") != uploaded.name:
    st.session_state["_mv_audio_name"] = uploaded.name
    st.session_state["_mv_audio_bytes"] = uploaded.read()
    for _k in ("_mv_rendered_bytes", "_mv_preview_gif", "_mv_audio_y", "_mv_audio_sr",
                "mv_trim_start", "mv_trim_end"):
        st.session_state.pop(_k, None)

audio_bytes: bytes = st.session_state["_mv_audio_bytes"]

# ── Layout ────────────────────────────────────────────────────────────────────
col_preview, col_settings = st.columns([3, 2])

with col_preview:
    # Audio info
    suffix = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else "wav"

    # Write to temp for duration check
    with tempfile.NamedTemporaryFile(suffix=f".{suffix}", delete=False) as tmp_audio:
        tmp_audio.write(audio_bytes)
        tmp_audio_path = tmp_audio.name

    try:
        import librosa
        y_info, sr_info = librosa.load(tmp_audio_path, sr=None, mono=True, duration=0.1)
        # Get full duration without loading all samples
        dur_info = librosa.get_duration(path=tmp_audio_path)
        st.markdown(f"**Duration:** {dur_info:.1f}s  |  **Sample rate:** {sr_info:,} Hz  |  **Format:** {suffix.upper()}")

        if dur_info > 600:
            show_warning(
                f"This file is {dur_info / 60:.1f} minutes long. "
                "Rendering may take a very long time. Consider trimming the audio first."
            )
    except Exception as e:
        st.markdown(f"**Format:** {suffix.upper()}")
        logger.warning("Could not read audio info: %s", e)
        dur_info = None

    # ── Waveform / spectral energy preview ───────────────────────────────────
    if dur_info is not None:
        if "_mv_audio_y" not in st.session_state:
            import librosa as _librosa
            _y, _sr = _librosa.load(tmp_audio_path, sr=22050, mono=True)
            st.session_state["_mv_audio_y"] = _y
            st.session_state["_mv_audio_sr"] = _sr

        if "_mv_audio_y" in st.session_state:
            import matplotlib.pyplot as plt
            _trim_start_pv = st.session_state.get("mv_trim_start", 0.0)
            _trim_end_pv = st.session_state.get("mv_trim_end", float(dur_info))
            fig = _render_audio_preview(
                st.session_state["_mv_audio_y"],
                st.session_state["_mv_audio_sr"],
                dur_info, _trim_start_pv, _trim_end_pv,
            )
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    # ── GIF or rendered video ─────────────────────────────────────────────────
    if "_mv_rendered_bytes" in st.session_state:
        st.video(st.session_state["_mv_rendered_bytes"])
        dl_name = st.session_state.get("_mv_output_filename") or uploaded.name.rsplit(".", 1)[0] + "_visualizer"
        st.download_button(
            "Download MP4",
            data=st.session_state["_mv_rendered_bytes"],
            file_name=f"{dl_name}.mp4",
            mime="video/mp4",
            use_container_width=True,
        )
    elif "_mv_preview_gif" in st.session_state:
        st.image(st.session_state["_mv_preview_gif"], caption="30-frame preview", use_container_width=True)

with col_settings:
    # ── Video settings ────────────────────────────────────────────────────────
    with st.expander("Video Settings", expanded=True):
        resolution = st.selectbox("Resolution", ["1920x1080", "1280x720"], index=0)
        res_w, res_h = map(int, resolution.split("x"))
        fps = st.selectbox("FPS", [24, 30, 60], index=1)
        n_bars = st.slider("Bar count", min_value=50, max_value=400, value=150, step=10)
        use_glow = st.toggle("Glow effect", value=True)
        glow_sigma = st.slider("Glow sigma", 2.0, 20.0, 8.0, 1.0, disabled=not use_glow)
        crf = st.slider("Output quality (CRF)", 15, 35, 18, 1,
            help="Lower = better quality & larger file. 18=high, 23=medium, 28=small")

    # ── Color scheme ──────────────────────────────────────────────────────────
    with st.expander("Color Scheme", expanded=False):
        preset_names = list(COLOR_PRESETS.keys()) + ["Custom"]
        preset = st.selectbox("Preset", preset_names, index=0)

        if preset == "Custom":
            bg_hex = st.color_picker("Background", "#0a0a1e")
            bar_hex = st.color_picker("Bar color", "#00ffff")
            glow_hex = st.color_picker("Glow color", "#00c8ff")
            bg_rgb = _hex_to_rgb(bg_hex)
            bar_rgb = _hex_to_rgb(bar_hex)
            glow_rgb = _hex_to_rgb(glow_hex)
        else:
            p = COLOR_PRESETS[preset]
            bg_rgb = p["bg"]
            bar_rgb = p["bar"]
            glow_rgb = p["glow"]

        use_gradient = st.toggle("Gradient (bass to treble)")
        if use_gradient:
            gc1, gc2 = st.columns(2)
            with gc1:
                bass_hex = st.color_picker("Bass color", _rgb_to_hex(*bar_rgb))
                bass_rgb = _hex_to_rgb(bass_hex)
            with gc2:
                treble_hex = st.color_picker("Treble color", "#ff6600")
                treble_rgb = _hex_to_rgb(treble_hex)
        else:
            bass_rgb = bar_rgb
            treble_rgb = bar_rgb

    # ── Audio trim ────────────────────────────────────────────────────────────
    with st.expander("Audio Trim", expanded=False):
        if dur_info:
            dur_f = float(dur_info)
            trim_start = st.slider(
                "Start (s)", 0.0, max(0.0, dur_f - 0.5), 0.0, 0.1,
                key="mv_trim_start",
            )
            _trim_end_min = min(trim_start + 0.5, dur_f)
            _trim_end_default = st.session_state.get("mv_trim_end", dur_f)
            _trim_end_default = max(_trim_end_default, _trim_end_min)
            trim_end = st.slider(
                "End (s)", _trim_end_min, dur_f, _trim_end_default, 0.1,
                key="mv_trim_end",
            )
            trimmed_dur = trim_end - trim_start
            st.caption(f"Trimmed duration: {trimmed_dur:.1f}s")
        else:
            trim_start, trim_end = 0.0, None

    # ── Title overlay ─────────────────────────────────────────────────────────
    with st.expander("Title Overlay", expanded=False):
        title_enabled = st.toggle("Enable title overlay", value=False)
        if title_enabled:
            track_name = st.text_input("Track name")
            artist = st.text_input("Artist")
            title_position = st.selectbox(
                "Position", ["top-left", "top-right", "bottom-left", "bottom-right"]
            )
            title_fontsize = st.slider("Font size", 16, 72, 36)
            title_color = st.color_picker("Title color", "#FFFFFF")
            title_opacity = st.slider("Opacity", 0.0, 1.0, 1.0, 0.05)
            title_display = st.selectbox("Display mode", ["Always visible", "First N seconds"])
            if title_display == "First N seconds":
                title_duration = st.number_input("Duration (seconds)", 1, 60, 5)
            else:
                title_duration = 0
        else:
            track_name = artist = ""
            title_position = "top-left"
            title_fontsize = 36
            title_color = "#FFFFFF"
            title_opacity = 1.0
            title_display = "Always visible"
            title_duration = 0

    # ── Output filename ───────────────────────────────────────────────────────
    default_name = uploaded.name.rsplit(".", 1)[0] + "_visualizer"
    output_filename = st.text_input("Output filename", value=default_name, placeholder="my_video")
    output_filename = (output_filename.strip() or default_name)

    # ── Buttons ───────────────────────────────────────────────────────────────
    col_preview_btn, col_render_btn = st.columns(2)

    settings = {
        "width": res_w,
        "height": res_h,
        "fps": fps,
        "n_bars": n_bars,
        "use_glow": use_glow,
        "glow_sigma": glow_sigma,
        "crf": crf,
        "bg_rgb": bg_rgb,
        "bar_rgb": bar_rgb,
        "glow_rgb": glow_rgb,
        "gradient": use_gradient,
        "bass_rgb": bass_rgb,
        "treble_rgb": treble_rgb,
        "trim_start": trim_start,
        "trim_end": trim_end if dur_info else None,
        "title_enabled": title_enabled,
        "track_name": track_name,
        "artist": artist,
        "title_position": title_position,
        "title_fontsize": title_fontsize,
        "title_color": title_color,
        "title_opacity": title_opacity,
        "title_display": title_display,
        "title_duration": title_duration,
    }

    with col_preview_btn:
        if st.button("Quick Preview", use_container_width=True):
            render_path = tmp_audio_path
            needs_conversion = suffix in ("m4a", "ogg")
            converted_path = None
            if needs_conversion:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_f:
                    converted_path = wav_f.name
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", tmp_audio_path, "-ar", "44100", converted_path],
                        capture_output=True, check=True, timeout=120,
                    )
                    render_path = converted_path
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    show_error(f"Failed to convert {suffix.upper()} to WAV: {e}")
                    st.stop()
            try:
                with st.spinner("Generating preview..."):
                    gif_bytes = _render_gif_preview(render_path, settings)
                    st.session_state["_mv_preview_gif"] = gif_bytes
                    st.session_state.pop("_mv_rendered_bytes", None)
                st.rerun()
            except Exception as e:
                logger.exception("Preview failed: %s", e)
                show_error(f"Preview failed: {e}")
            finally:
                if converted_path:
                    try:
                        os.unlink(converted_path)
                    except OSError:
                        pass

    with col_render_btn:
        render_clicked = st.button("Render Video", type="primary", use_container_width=True)

    if render_clicked:
        # Prepare audio file (convert M4A/OGG to WAV if needed)
        render_path = tmp_audio_path
        needs_conversion = suffix in ("m4a", "ogg")
        converted_path = None

        if needs_conversion:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_f:
                converted_path = wav_f.name
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", tmp_audio_path, "-ar", "44100", converted_path],
                    capture_output=True, check=True, timeout=120,
                )
                render_path = converted_path
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                show_error(f"Failed to convert {suffix.upper()} to WAV: {e}")
                st.stop()

        with st.status("Rendering...", expanded=True) as status:
            try:
                result = _render_video(render_path, settings, status)
                if result:
                    st.session_state["_mv_rendered_bytes"] = result
                    st.session_state["_mv_settings"] = settings
                    st.session_state["_mv_output_filename"] = output_filename
                    st.session_state.pop("_mv_preview_gif", None)
                    show_success("Video rendered successfully!")
                    st.rerun()
            except Exception as e:
                logger.exception("Render failed: %s", e)
                show_error(f"Render failed: {e}")
            finally:
                if converted_path:
                    try:
                        os.unlink(converted_path)
                    except OSError:
                        pass
