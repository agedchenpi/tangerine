# Music Visualizer — Performance + Progress Feedback

## Context
A 31.4s WAV at 30fps 1920x1080 takes well over a minute to render with no visible progress. Two problems: (1) the render is slow, (2) the user has no idea what's happening during the render.

## Root Causes (ordered by impact)
1. **Glow at half-res** — `gaussian_filter` on 540×960×3 floats × 942 frames is the #1 CPU hog
2. **x264 `preset=medium`** — slow encoding for no perceptible quality gain
3. **moviepy overhead** — Python-level frame callback with no progress hook
4. **Python bar loop** — 150 iterations/frame doing per-bar arithmetic + np.clip
5. **Title: full-frame float blend** — converts entire 1920×1080 frame to float32 for a ~400×60px text region
6. **`frame_buf.copy()`** — 6MB allocation every frame even when unnecessary

## File to Modify
`admin/pages/music_visualizer.py` — all changes are in this single file

## Changes

### 1. Replace moviepy with direct ffmpeg subprocess pipe
Remove moviepy from `_render_video()` entirely. Pipe raw RGB24 frames to ffmpeg stdin via `subprocess.Popen`. This:
- Gives us a per-frame loop we control (enables progress bar)
- Uses `preset=veryfast` + `crf 18` (3-4x faster encoding, negligible quality diff)
- Muxes audio directly via ffmpeg `-i audio_path` (no AudioFileClip needed)

### 2. Add `st.progress()` with frame count + ETA
Inside the frame loop, update every 10 frames:
```
Frame 450/942 | 18.2 fps | ETA 27s
```
Phases shown via `st.status()`: Analyzing audio → Rendering frames (with progress bar) → Done

### 3. Glow at quarter-resolution (4x speedup on glow path)
Change `frame_buf[::2, ::2]` → `frame_buf[::4, ::4]`, halve sigma, 4x upsample back. Glow is inherently blurry so quarter-res is visually fine.

### 4. Vectorize bar computation
Move `boosted`, `bar_heights`, and beat-brightness color calc outside the per-bar loop. The loop body becomes just two numpy slice assignments per bar.

### 5. Title overlay: bounding-box blend only
Pre-compute tight (ty1:ty2, tx1:tx2) ROI of non-zero alpha pixels. Blend only that ~400×60 region instead of the full 1920×1080 frame. ~85x less work.

### 6. Eliminate unnecessary frame copy
When glow is off and title is off, write `frame_buf.tobytes()` directly — no `.copy()` needed since we overwrite it next frame.

## Expected Result
- **Before:** >60s render, no progress feedback
- **After:** ~15-20s render, live progress bar with ETA
- User sees: "Analyzing audio..." → progress bar with frame count → "Done!"

## Verification
1. `docker compose build admin && docker compose up -d admin`
2. Upload same 5.7MB WAV file, render with glow on
3. Confirm progress bar appears and updates smoothly
4. Confirm output MP4 plays correctly with audio sync
5. Test with glow off, title on/off to verify all code paths
