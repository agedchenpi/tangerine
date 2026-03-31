# Plan: Music Visualizer Rendering Optimization

## Context
The music visualizer renders MP4 videos at 1920×1080 @ 30fps, taking ~15–20s for a 30s audio clip. Profiling the render loop reveals three dominant costs per frame:
1. **Glow blur** — `scipy.gaussian_filter` on a quarter-res float32 buffer (~62ms vs OpenCV's ~14ms per call)
2. **Glow upsampling** — `np.repeat(np.repeat(...))` back to full resolution (slow in Python; `cv2.resize` is ~150x faster)
3. **Buffer allocation** — `np.zeros((1080, 1920, 3), dtype=np.float32)` allocated fresh every frame (~900 frames = ~22GB of allocation/deallocation total)

Secondary costs: FFmpeg not using all CPU cores or animation-tuning, energy array computed via a Python list comprehension instead of vectorized NumPy.

Online research confirms:
- `cv2.GaussianBlur` / `cv2.stackBlur` are 4–5x faster than `scipy.gaussian_filter` (ResearchGate benchmark)
- `cv2.resize(INTER_LINEAR)` is ~150x faster than `scipy.ndimage.zoom` / `np.repeat` for upsampling (Joseph Long bicubic bake-off)
- FFmpeg `-tune animation` is designed for large flat-color areas (exactly what a visualizer produces)
- FFmpeg `-threads 0` enables all logical cores for slice-parallel encoding

## Files to Modify

| File | Change |
|------|--------|
| `admin/pages/music_visualizer.py` | Core optimizations (blur, upsample, allocation, ffmpeg flags, energy vectorization) |
| `requirements/admin.txt` | Add `opencv-python-headless>=4.8.0` |

## Changes

### 1. `requirements/admin.txt`
Add one line to the Music Visualizer section:
```
opencv-python-headless>=4.8.0   # fast blur + resize for glow effect
```

### 2. `_make_frame_factory` — glow pipeline (lines 328, 394–400)

**Replace** `from scipy.ndimage import gaussian_filter` with `import cv2`

**Replace** (inside the `render_frame` closure, the glow block):
```python
# OLD (slow)
small = bar_layer[::4, ::4]
blurred = gaussian_filter(small, sigma=(glow_sigma * 0.5, glow_sigma * 0.5, 0))
glow_layer = np.repeat(np.repeat(blurred, 4, axis=0), 4, axis=1)[:height, :width]
```
With:
```python
# NEW (~5–10x faster combined)
ksize = max(3, int(glow_sigma * 2) | 1)   # odd kernel ≥ 3
small = bar_layer[::4, ::4]
blurred = cv2.GaussianBlur(small, (ksize, ksize), glow_sigma * 0.5)
glow_layer = cv2.resize(blurred, (width, height), interpolation=cv2.INTER_LINEAR)
```

### 3. `_make_frame_factory` — pre-allocate buffers (lines 382)

Move `bar_layer` allocation **outside** the closure (pre-compute once):
```python
# OUTSIDE render_frame (pre-allocated):
bar_layer = np.zeros((height, width, 3), dtype=np.float32)

# INSIDE render_frame (reset each frame, no allocation):
bar_layer.fill(0.0)
```

### 4. `_make_frame_factory` — in-place clip (lines 398–402)

```python
# OLD — allocates new array
result = np.clip(bg_float + glow_layer * GLOW_STRENGTH + bar_layer, 0, 255).astype(np.uint8)

# NEW — reuse result buffer (pre-allocate result as uint8 outside closure)
np.add(bg_float, glow_layer * GLOW_STRENGTH, out=composite_f)  # or direct clip
np.add(composite_f, bar_layer, out=composite_f)
np.clip(composite_f, 0, 255, out=composite_f)
result = composite_f.view(np.uint8)[..., ::4] # simpler: just use np.clip with out param on existing buffer
```
Simpler implementation: pre-allocate `composite_f = np.empty((height, width, 3), dtype=np.float32)` outside closure and use `np.clip(..., out=composite_uint8)` with a pre-allocated uint8 result buffer.

### 5. `_analyze_audio` — vectorize energy computation (lines 87–91)

**Replace** Python list comprehension:
```python
# OLD — Python loop, n_frames iterations
raw_energy = np.array(
    [np.sqrt(np.mean(y[i * frame_len:(i + 1) * frame_len] ** 2))
     for i in range(n_frames)],
    dtype=np.float32,
)
```
With vectorized reshape:
```python
# NEW — single NumPy call
n_samples = n_frames * frame_len
y_padded = np.pad(y, (0, max(0, n_samples - len(y))))[:n_samples]
raw_energy = np.sqrt(
    y_padded.reshape(n_frames, frame_len).astype(np.float32) ** 2
    .mean(axis=1)
)
```

### 6. FFmpeg command — add `-tune animation -threads 0` (lines 489–505)

In the `ffmpeg_cmd` list, after `-crf crf`:
```python
"-tune", "animation",   # optimizes for flat-color large areas (visualizers)
"-threads", "0",        # use all logical CPU cores for slice-parallel encoding
```

## Expected Impact

| Change | Target | Expected Speedup |
|--------|--------|-----------------|
| `cv2.GaussianBlur` | blur step | ~4–5x |
| `cv2.resize` vs `np.repeat` | upsample step | ~50–150x on that op |
| Pre-allocated `bar_layer` | per-frame alloc | ~5–15% overall |
| Vectorized energy | audio analysis | negligible (runs once) |
| FFmpeg flags | encode phase | ~10–30% encode time |
| **Combined** | **total render** | **~2–4x end-to-end** |

Estimated new render time: **5–8s** for a 30s clip at 1080p 30fps (down from ~15–20s).

## Verification

1. Upload a 30s MP3, render at 1920×1080 30fps with glow enabled
2. Compare render time before/after (check the fps counter in the status bar)
3. Play the output video — verify glow quality is visually equivalent
4. Test with glow disabled to confirm the non-glow path still works
5. Check Docker builds cleanly with the new `opencv-python-headless` dependency (`docker compose build streamlit`)
