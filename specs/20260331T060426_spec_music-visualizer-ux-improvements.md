# Music Visualizer — UX Improvements

## Context
The visualizer currently requires a full render before the user can see any output — there's no way to preview settings, trim audio, or understand what the final video will look like. Four concrete UX gaps identified:

1. No preview — render is blind until complete (full render can take minutes)
2. No trim controls — audio must be pre-trimmed externally
3. No waveform/spectrum view — user can't see the audio structure before rendering
4. Output quality (CRF 18) is hardcoded — no file size vs. quality tradeoff

## File to Modify
`admin/pages/music_visualizer.py` — all changes in this single file

---

## Changes

### A. CRF quality slider (simplest — 3 lines)

In `Video Settings` expander, add:
```python
crf = st.slider("Output quality (CRF)", 15, 35, 18, 1,
    help="Lower = better quality & larger file. 18=high, 23=medium, 28=small")
```
Add `"crf": crf` to settings dict.

In `_render_video`, replace hardcoded `"-crf", "18"` with `"-crf", str(settings["crf"])`.

---

### B. Audio trim controls

**New expander** `"Audio Trim"` in `col_settings` (after Color Scheme, before Title Overlay):
```python
with st.expander("Audio Trim", expanded=False):
    if dur_info:
        trim_start = st.slider("Start (s)", 0.0, float(dur_info), 0.0, 0.1)
        trim_end   = st.slider("End (s)",   trim_start + 0.5, float(dur_info), float(dur_info), 0.1)
    else:
        trim_start, trim_end = 0.0, None
```

Add `"trim_start": trim_start`, `"trim_end": trim_end` to settings dict.

**`_analyze_audio` signature** — add `offset: float = 0.0`, `trim_duration: float | None = None`:
```python
y, sr = librosa.load(audio_path, sr=None, mono=True, offset=offset, duration=trim_duration)
```

**`_render_video`** — pass trim to `_analyze_audio` and add to ffmpeg audio input:
```python
offset = settings.get("trim_start", 0.0)
trim_dur = settings.get("trim_end", None)
if trim_dur:
    trim_dur -= offset  # convert to duration
sr, duration, spectrum, beat_mask, energy = _analyze_audio(audio_path, fps, n_bars,
    offset=offset, trim_duration=trim_dur)
```

For ffmpeg, trim the audio track:
```python
# audio input args (before -i audio_path)
audio_input_args = ["-i", audio_path]
if settings.get("trim_start", 0.0) > 0 or settings.get("trim_end"):
    audio_input_args = [
        "-ss", str(settings["trim_start"]),
        *(["-to", str(settings["trim_end"])] if settings.get("trim_end") else []),
        "-i", audio_path,
    ]
```

---

### C. Waveform/spectrum preview

**New function `_render_audio_preview(y, sr, duration, trim_start, trim_end)`:**
- Takes already-loaded audio array `y` (full file, not trimmed) + trim bounds
- Returns a matplotlib `Figure` with two subplots:
  1. **Waveform** — `y` downsampled to ~3000 points, plotted as amplitude vs time
     - Shaded region for trim bounds (if any)
     - Dark background (`#0a0a1e`), line color `#00c8ff`
  2. **Spectral energy** — `librosa.feature.rms(y=y)` over time as a filled area
     - Same theme

**Where to call it:** In `col_preview`, after the audio info block, always-on (not behind expander). Cache the `y` array in session state as `_mv_audio_y` keyed by filename so the preview redraws instantly when trim sliders change (Streamlit reruns automatically).

```python
# After audio info block in col_preview:
if "_mv_audio_y" not in st.session_state:
    import librosa
    y_full, sr_full = librosa.load(tmp_audio_path, sr=22050, mono=True)
    st.session_state["_mv_audio_y"] = y_full
    st.session_state["_mv_audio_sr"] = sr_full

fig = _render_audio_preview(
    st.session_state["_mv_audio_y"],
    st.session_state["_mv_audio_sr"],
    dur_info, trim_start, trim_end
)
st.pyplot(fig, use_container_width=True)
plt.close(fig)
```

Note: `trim_start`/`trim_end` come from the trim sliders, but they're defined in `col_settings` which renders after `col_preview` in code. Solution: read trim values from `st.session_state` in the preview (sliders write to session state by default via their `key=` parameter), or restructure so trim sliders are collected before the column split and only *displayed* inside col_settings.

**Restructure approach (cleanest):** Collect trim values before the `st.columns` split using `st.session_state` keys on the sliders (`key="mv_trim_start"`, `key="mv_trim_end"`), then reference `st.session_state.get("mv_trim_start", 0.0)` in col_preview.

---

### D. 30-frame GIF preview

**New function `_render_gif_preview(audio_path, settings) -> bytes`:**
```python
def _render_gif_preview(audio_path: str, settings: dict) -> bytes:
    from PIL import Image
    import io

    # Half resolution for speed
    preview_settings = {**settings, "width": settings["width"] // 2, "height": settings["height"] // 2}

    offset = settings.get("trim_start", 0.0)
    trim_dur = (settings["trim_end"] - offset) if settings.get("trim_end") else None
    sr, duration, spectrum, beat_mask, energy = _analyze_audio(
        audio_path, settings["fps"], settings["n_bars"], offset=offset, trim_duration=trim_dur
    )

    n_frames = spectrum.shape[0]
    frame_indices = np.linspace(0, n_frames - 1, 30, dtype=int)

    # Build renderer at half-res
    bar_colors = ...  # same logic as _render_video
    render_frame = _make_frame_factory(preview_settings["width"], preview_settings["height"], ...)

    # Render 30 frames
    pil_frames = []
    w, h = preview_settings["width"], preview_settings["height"]
    for fi in frame_indices:
        raw = render_frame(fi)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
        pil_frames.append(Image.fromarray(arr).quantize(colors=128))

    buf = io.BytesIO()
    pil_frames[0].save(buf, format="GIF", save_all=True,
                        append_images=pil_frames[1:], loop=0, duration=120, optimize=True)
    return buf.getvalue()
```

**UI:** Add a "Quick Preview (GIF)" button next to the Render button:
```python
col_preview_btn, col_render_btn = st.columns(2)
with col_preview_btn:
    if st.button("Quick Preview", use_container_width=True):
        with st.spinner("Generating preview..."):
            gif_bytes = _render_gif_preview(render_path, settings)
            st.session_state["_mv_preview_gif"] = gif_bytes
with col_render_btn:
    render_clicked = st.button("Render Video", type="primary", use_container_width=True)
```

In `col_preview`, show GIF if present and no rendered video yet:
```python
if "_mv_preview_gif" in st.session_state and "_mv_rendered_bytes" not in st.session_state:
    st.image(st.session_state["_mv_preview_gif"], caption="30-frame preview", use_container_width=True)
```

---

## Layout Changes Summary

```
col_preview (3)                    col_settings (2)
─────────────────────────────────  ──────────────────────────────────
Audio info (duration, sr, format)  [Video Settings] ← add CRF slider
Waveform + spectral energy plot    [Color Scheme]
                                   [Audio Trim]  ← NEW expander
                                   [Title Overlay]
Rendered video / GIF preview       Output filename
                                   [Quick Preview] [Render Video]
```

---

## Critical files
- `admin/pages/music_visualizer.py` — only file changed

## Key Implementation Notes
- Trim sliders use `key="mv_trim_start"` / `key="mv_trim_end"` so waveform preview can read them from `st.session_state` before slider widgets render
- Audio waveform loads at 22050 Hz (half native) and caches in session state — no re-analysis on slider drag
- GIF uses Pillow `.quantize(colors=128)` for acceptable quality with small file size
- When trim changes, clear `_mv_rendered_bytes` and `_mv_preview_gif` from session state to avoid stale previews

## Verification
1. `docker compose build admin && docker compose up -d admin`
2. Upload WAV → waveform + spectral energy chart appears immediately
3. Adjust trim sliders → waveform shading updates, audio info reflects trimmed duration
4. Click "Quick Preview" → animated GIF appears in ~10s, shows 30 evenly-spaced frames
5. Adjust CRF slider to 28 → render → file is noticeably smaller than CRF 18
6. Render with trim → output video starts/ends at correct timestamps
