# Music Visualizer - Streamlit Page

## Context
The user has a standalone Python script (`musicvisualizer_v2.py`) that generates MP4 videos with symmetric bar waveform visualizations from audio files. It uses FFT analysis, beat detection, and gaussian glow effects. The goal is to optimize the code, add color customization + title overlays, and integrate it as a new Streamlit page in the Tangerine admin app.

## Files to Create/Modify

| Action | File | Change |
|--------|------|--------|
| **Create** | `admin/pages/music_visualizer.py` | New page (~450 lines) |
| **Modify** | `admin/app.py` | Add `st.Page` entry in "Tools" group (line 89) |
| **Modify** | `requirements/admin.txt` | Add `librosa>=0.10.0`, `scipy>=1.11.0` |
| **Modify** | `Dockerfile.streamlit` | Add `libsndfile1` to apt-get (line 18) |

## Dependencies

```
librosa>=0.10.0    # Audio feature extraction (STFT, beat tracking)
scipy>=1.11.0      # Signal processing (gaussian_filter for glow)
```

System: `libsndfile1` added to Dockerfile.streamlit apt-get line (required by librosa's soundfile backend).

## Optimizations from Original Script

1. **Vectorized STFT analysis** - Use librosa's STFT with `hop_length = sr // fps` to get one spectral column per frame (instead of manual FFT per frame)
2. **Log-spaced frequency bands** - Better perceptual mapping than linear bins
3. **Pre-allocated frame buffer** - Reuse single `np.zeros` array across frames instead of allocating per frame
4. **Pre-computed bar geometry** - x_starts, x_ends, color arrays computed once
5. **Glow at half resolution** - Apply `gaussian_filter` on 2x downsampled frame, then upscale (4x fewer pixels)
6. **Beat mask pre-computed** - Array of beat pulses built once during analysis, not detected per frame
7. **Remove unused chroma analysis** - Original computed chroma features but never used them

## Color System

**Presets** (selectbox):
- Cyan / Dark, Orange / Dark, Green / Dark, Purple / Dark, White / Black, Custom

**Custom mode** shows `st.color_picker` for: background, waveform bar, glow color

**Gradient toggle**: When enabled, shows bass color + treble color pickers. `_compute_bar_colors()` interpolates linearly across `n_bars` producing a `(n_bars, 3)` uint8 array.

## Title/Track Overlay

- Optional toggle, disabled by default
- Fields: Track Name, Artist (rendered as two lines)
- Position: selectbox (top-left, top-right, bottom-left, bottom-right) with 20px padding
- Font size slider (16-72, default 36), color picker, opacity slider
- Display mode: "Always visible" or "First N seconds" (with duration input)
- Rendered via moviepy `TextClip` + `CompositeVideoClip` (same pattern as media_editor.py)
- Font: Liberation-Sans (already installed in Docker)

## Page Layout

```
[Page Header: "Music Visualizer" icon="🎵"]
[File Uploader: WAV, MP3, FLAC, OGG, M4A]

[col_preview (3) | col_settings (2)]
  LEFT:                          RIGHT:
    Audio info (duration, sr)      Expander: Video Settings
    Video preview (st.video)         - Resolution (1920x1080 / 1280x720)
    Download button                  - FPS (24/30/60)
                                     - Bar count (50-400)
                                     - Glow toggle + sigma
                                   Expander: Color Scheme
                                     - Preset selectbox
                                     - Custom pickers (if Custom)
                                     - Gradient toggle + colors
                                   Expander: Title Overlay
                                     - Enable toggle
                                     - Track name, artist
                                     - Position, font size, color, opacity
                                     - Display duration mode
                                   [Render Button]
```

## Session State Keys (prefix: `_mv_`)

- `_mv_audio_bytes` / `_mv_audio_name` - Cached upload
- `_mv_rendered_bytes` - Final MP4 output
- `_mv_settings` - Settings snapshot at render time

## Rendering Pipeline

1. Write uploaded bytes to temp file (WAV conversion via ffmpeg if needed for M4A/OGG)
2. `_analyze_audio()` - librosa STFT, beat tracking, log-spaced band binning
3. `_make_frame_factory()` - Returns closure with pre-computed geometry + colors
4. Build `VideoClip(make_frame, duration)` + `AudioFileClip` + optional `TextClip`
5. `write_videofile()` with libx264/aac codec
6. Read bytes, cache in session state, show `st.video()` + download button
7. Progress via `st.status()` with labeled steps

## Edge Cases / Safeguards

- Duration limit warning at 10+ minutes (render time estimate shown)
- M4A/OGG codec fallback: convert to WAV via `ffmpeg` subprocess before librosa load
- Frame index clamping: `min(fi, n_frames - 1)` to prevent out-of-bounds
- Pillow ANTIALIAS compat shim (same as media_editor.py)
- Temp files use `delete=False` pattern (consistent with media_editor.py)

## Verification

1. Rebuild Docker: `docker compose build streamlit`
2. Navigate to Tools > Music Visualizer in the admin app
3. Upload a WAV or MP3 file
4. Test each color preset + custom colors + gradient mode
5. Test title overlay in each corner position, both "always" and "first N seconds" modes
6. Render and verify: audio syncs with bars, beat flashes work, glow visible, title renders
7. Download the MP4 and play in external player to confirm quality
