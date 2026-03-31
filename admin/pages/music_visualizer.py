"""Music Visualizer — generate MP4 videos with bar waveform animations from audio."""

import logging
import os
import subprocess
import tempfile

import numpy as np
import streamlit as st
from PIL import Image

# moviepy 1.0.3 uses Image.ANTIALIAS, removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

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
def _analyze_audio(audio_path: str, fps: int, n_bars: int):
    """Run STFT and beat tracking. Returns (sr, duration, spectrum, beat_mask)."""
    import librosa

    y, sr = librosa.load(audio_path, sr=None, mono=True)
    duration = len(y) / sr

    hop_length = max(1, sr // fps)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop_length))

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

    # Beat tracking
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    beat_mask = np.zeros(n_frames, dtype=np.float32)
    for bf in beat_frames:
        if bf < n_frames:
            beat_mask[bf] = 1.0
    # Decay beat pulses over a few frames
    for i in range(1, n_frames):
        beat_mask[i] = max(beat_mask[i], beat_mask[i - 1] * 0.85)

    return sr, duration, spectrum, beat_mask


# ── Frame rendering ──────────────────────────────────────────────────────────
def _make_title_overlay(width: int, height: int, settings: dict) -> np.ndarray | None:
    """Pre-render title text as an RGBA numpy array using Pillow (no ImageMagick)."""
    if not settings.get("title_enabled"):
        return None

    lines = []
    if settings.get("track_name"):
        lines.append(settings["track_name"])
    if settings.get("artist"):
        lines.append(settings["artist"])
    if not lines:
        return None

    from PIL import ImageDraw, ImageFont

    font_size = settings.get("title_fontsize", 36)
    title_color_hex = settings.get("title_color", "#FFFFFF")
    title_rgb = _hex_to_rgb(title_color_hex)
    opacity = int(settings.get("title_opacity", 1.0) * 255)

    # Load Liberation Sans (installed in Docker)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()

    # Measure text
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    line_bboxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [bb[3] - bb[1] for bb in line_bboxes]
    line_widths = [bb[2] - bb[0] for bb in line_bboxes]
    total_h = sum(line_heights) + (len(lines) - 1) * 4
    max_w = max(line_widths)

    # Create RGBA overlay image
    txt_img = Image.new("RGBA", (max_w + 4, total_h + 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_img)
    y_cursor = 0
    for i, line in enumerate(lines):
        draw.text((0, y_cursor), line, fill=(*title_rgb, opacity), font=font)
        y_cursor += line_heights[i] + 4

    txt_arr = np.array(txt_img)  # (h, w, 4) RGBA

    # Compute position
    position = settings.get("title_position", "top-left")
    pad = 20
    th, tw = txt_arr.shape[:2]
    if position == "top-left":
        px, py = pad, pad
    elif position == "top-right":
        px, py = width - tw - pad, pad
    elif position == "bottom-left":
        px, py = pad, height - th - pad
    else:  # bottom-right
        px, py = width - tw - pad, height - th - pad

    # Bake into a full-frame RGBA array
    overlay = np.zeros((height, width, 4), dtype=np.uint8)
    # Clamp to frame bounds
    y1, y2 = max(0, py), min(height, py + th)
    x1, x2 = max(0, px), min(width, px + tw)
    sy1, sy2 = y1 - py, y2 - py
    sx1, sx2 = x1 - px, x2 - px
    overlay[y1:y2, x1:x2] = txt_arr[sy1:sy2, sx1:sx2]

    return overlay


def _make_frame_factory(
    width: int, height: int, n_bars: int,
    spectrum: np.ndarray, beat_mask: np.ndarray,
    bg_rgb: tuple, bar_colors: np.ndarray, glow_rgb: tuple,
    use_glow: bool, glow_sigma: float, fps: int,
    title_overlay: np.ndarray | None = None,
    title_end_frame: int | None = None,
):
    """Return a make_frame(t) closure with pre-computed geometry."""
    from scipy.ndimage import gaussian_filter

    gap = max(1, width // (n_bars * 8))
    total_gap = gap * (n_bars - 1)
    bar_w = max(1, (width - total_gap) // n_bars)
    x_starts = np.array([i * (bar_w + gap) for i in range(n_bars)], dtype=int)
    x_ends = x_starts + bar_w

    center_y = height // 2
    max_bar_h = int(height * 0.42)
    n_frames = spectrum.shape[0]

    frame_buf = np.zeros((height, width, 3), dtype=np.uint8)

    # Pre-compute title alpha for blending
    if title_overlay is not None:
        title_alpha = title_overlay[:, :, 3:4].astype(np.float32) / 255.0
        title_rgb = title_overlay[:, :, :3].astype(np.float32)
        title_mask = title_alpha > 0  # any pixel with alpha
        # Squeeze mask for indexing
        title_mask_2d = title_mask[:, :, 0]
    else:
        title_alpha = title_rgb = title_mask_2d = None

    def make_frame(t):
        fi = min(int(t * fps), n_frames - 1)
        magnitudes = spectrum[fi]
        beat = beat_mask[fi]

        frame_buf[:] = bg_rgb

        for b in range(n_bars):
            mag = magnitudes[b]
            # Beat boost
            boosted = min(1.0, mag + beat * 0.25)
            bar_h = int(boosted * max_bar_h)
            if bar_h < 1:
                continue

            color = bar_colors[b]
            # Brightness boost on beat
            if beat > 0.3:
                brightness = 1.0 + beat * 0.4
                color = np.clip(color * brightness, 0, 255).astype(np.uint8)

            xs, xe = x_starts[b], x_ends[b]
            # Symmetric bars (up and down from center)
            y_top = center_y - bar_h
            y_bot = center_y + bar_h
            frame_buf[max(0, y_top):center_y, xs:xe] = color
            frame_buf[center_y:min(height, y_bot), xs:xe] = color

        if use_glow and glow_sigma > 0:
            # Glow at half resolution for performance
            small = frame_buf[::2, ::2].astype(np.float32)
            blurred = gaussian_filter(small, sigma=(glow_sigma, glow_sigma, 0))
            # Upscale back
            glow_layer = np.repeat(np.repeat(blurred, 2, axis=0), 2, axis=1)[:height, :width]
            # Additive blend
            result = np.clip(frame_buf.astype(np.float32) + glow_layer * 0.5, 0, 255).astype(np.uint8)
        else:
            result = frame_buf.copy()

        # Title overlay (Pillow-rendered, no ImageMagick)
        if title_alpha is not None:
            show_title = True
            if title_end_frame is not None and fi > title_end_frame:
                show_title = False
            if show_title:
                bg_f = result.astype(np.float32)
                blended = bg_f * (1 - title_alpha) + title_rgb * title_alpha
                result = blended.astype(np.uint8)

        return result

    return make_frame


# ── Rendering pipeline ───────────────────────────────────────────────────────
def _render_video(
    audio_path: str, settings: dict, progress_status
) -> bytes | None:
    """Full render pipeline: analyze → build frames → composite → encode."""
    import moviepy.editor as mpe

    width = settings["width"]
    height = settings["height"]
    fps = settings["fps"]
    n_bars = settings["n_bars"]

    # 1. Analyze audio
    progress_status.update(label="Analyzing audio...", state="running")
    sr, duration, spectrum, beat_mask = _analyze_audio(audio_path, fps, n_bars)

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

    # 4. Build frame factory
    progress_status.update(label="Building frame renderer...", state="running")
    make_frame = _make_frame_factory(
        width, height, n_bars, spectrum, beat_mask,
        bg_rgb, bar_colors, glow_rgb,
        settings["use_glow"], settings["glow_sigma"], fps,
        title_overlay=title_overlay, title_end_frame=title_end_frame,
    )

    # 5. Create video clip
    progress_status.update(label="Rendering video frames...", state="running")
    video = mpe.VideoClip(make_frame, duration=duration)
    audio = mpe.AudioFileClip(audio_path)
    video = video.set_audio(audio)

    # 6. Write to temp file
    progress_status.update(label="Encoding MP4...", state="running")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_f:
        out_path = out_f.name

    try:
        video.write_videofile(
            out_path, fps=fps, codec="libx264", audio_codec="aac",
            logger=None, preset="medium",
        )
        with open(out_path, "rb") as f:
            result_bytes = f.read()
    finally:
        audio.close()
        video.close()
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

# Cache upload bytes in session state
if st.session_state.get("_mv_audio_name") != uploaded.name:
    st.session_state["_mv_audio_name"] = uploaded.name
    st.session_state["_mv_audio_bytes"] = uploaded.read()
    st.session_state.pop("_mv_rendered_bytes", None)

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

    # Show rendered video or placeholder
    if "_mv_rendered_bytes" in st.session_state:
        st.video(st.session_state["_mv_rendered_bytes"])
        st.download_button(
            "Download MP4",
            data=st.session_state["_mv_rendered_bytes"],
            file_name=f"{uploaded.name.rsplit('.', 1)[0]}_visualizer.mp4",
            mime="video/mp4",
            use_container_width=True,
        )

with col_settings:
    # ── Video settings ────────────────────────────────────────────────────────
    with st.expander("Video Settings", expanded=True):
        resolution = st.selectbox("Resolution", ["1920x1080", "1280x720"], index=0)
        res_w, res_h = map(int, resolution.split("x"))
        fps = st.selectbox("FPS", [24, 30, 60], index=1)
        n_bars = st.slider("Bar count", min_value=50, max_value=400, value=150, step=10)
        use_glow = st.toggle("Glow effect", value=True)
        glow_sigma = st.slider("Glow sigma", 2.0, 20.0, 8.0, 1.0, disabled=not use_glow)

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

    # ── Render button ─────────────────────────────────────────────────────────
    if st.button("Render Video", type="primary", use_container_width=True):
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

        settings = {
            "width": res_w,
            "height": res_h,
            "fps": fps,
            "n_bars": n_bars,
            "use_glow": use_glow,
            "glow_sigma": glow_sigma,
            "bg_rgb": bg_rgb,
            "bar_rgb": bar_rgb,
            "glow_rgb": glow_rgb,
            "gradient": use_gradient,
            "bass_rgb": bass_rgb,
            "treble_rgb": treble_rgb,
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

        with st.status("Rendering...", expanded=True) as status:
            try:
                result = _render_video(render_path, settings, status)
                if result:
                    st.session_state["_mv_rendered_bytes"] = result
                    st.session_state["_mv_settings"] = settings
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
