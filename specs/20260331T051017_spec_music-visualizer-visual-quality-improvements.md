# Music Visualizer — Visual Quality Improvements

## Context
The current bars look soft/blurry and lack the smooth temporal motion of the reference `WaveformRenderer` code. After side-by-side analysis, there are 5 concrete root causes. The reference code produces crisp bars with a smooth glow halo underneath, while ours blurs the bars themselves.

## Root Causes (ordered by visual impact)

### 1. Wrong composite order — THE main cause of soft bars
**Current:** bars drawn into `frame_buf` → blur `frame_buf` → bars are baked into the blur
**Reference:** draw `bar_layer` (float32) → blur `bar_layer` for glow → composite `bg + glow + bars`
Result: bars are always pixel-sharp; glow appears *behind* them as a halo

### 2. No EMA temporal smoothing
**Current:** raw spectrum values jump frame-to-frame
**Reference:** `spectrum[i] = 0.45 * spectrum[i] + 0.55 * spectrum[i-1]`
Result: bars animate smoothly instead of flickering

### 3. No power curve on bar heights
**Current:** `bar_h = magnitude * max_bar_h` — only loud frequencies show tall bars
**Reference:** `bars_curved = bars ** 0.6` — lifts quiet frequencies, fills the spectrum
Result: all bars have visible height; visualization looks dense and full

### 4. No energy-reactive scaling
**Current:** bar height is absolute — doesn't breathe with the music
**Reference:** `energy_scale = 0.4 + rms_energy[fi] * 0.7` multiplied into bar height
Result: quiet passages shrink, loud passages fill the frame dynamically

### 5. Beat flash accumulator (minor but noticeable)
**Current:** hard brightness multiplier tied to decayed beat_mask
**Reference:** `flash += 0.55` on beat, `flash -= 0.12` every frame, lerp bar color → white
Result: smoother, more gradual flash that fades naturally across ~5 frames

## File to Modify
`admin/pages/music_visualizer.py` — all changes in this single file

## Changes

### A. `_analyze_audio` — add EMA smoothing + RMS energy
- Change `n_fft=2048` → `n_fft=4096` (better low-frequency resolution)
- After normalization, apply EMA: `for i in range(1, n_frames): spectrum[i] = 0.45 * spectrum[i] + 0.55 * spectrum[i-1]`
- Compute RMS energy per frame: `frame_len = sr // fps`, `energy = [rms(y[i*fl:(i+1)*fl]) for i in range(n_frames)]`, normalize to 0–1
- Return signature changes: `return sr, duration, spectrum, beat_mask, energy`

### B. `_make_frame_factory` — fix composite + power curve + energy scaling + beat flash
- Accept new `energy: np.ndarray` parameter
- **Composite fix**: draw bars into float32 `bar_layer` (zeros, same shape as frame), not `frame_buf`
- **Glow**: blur `bar_layer[::4, ::4]`, upscale, multiply by `GLOW_STRENGTH=1.8`
- **Composite**: `result = np.clip(bg_float + glow_layer + bar_layer * 255, 0, 255).astype(uint8)`
- **Power curve**: `bar_heights = (magnitudes ** 0.6) * energy_scale * max_bar_h` where `energy_scale = 0.4 + energy[fi] * 0.7`
- **Beat flash**: mutable `flash = [0.0]` in closure; on beat: `flash[0] = min(flash[0] + 0.55, 1.0)`; each frame: `flash[0] = max(flash[0] - 0.12, 0.0)`; lerp `bar_colors_f` toward white by `flash[0] * 0.8`
- **Center line**: after composite, `result[center_y, :] = np.clip(result[center_y, :].astype(float) + 46, 0, 255).astype(uint8)` — subtle brightening

### C. `_render_video` — unpack new energy return value
- `sr, duration, spectrum, beat_mask, energy = _analyze_audio(...)`
- Pass `energy=energy` to `_make_frame_factory`

## Critical files
- `admin/pages/music_visualizer.py` — only file changed

## Verification
1. `docker compose build admin && docker compose up -d admin`
2. Upload WAV, render with glow on — bars should be crisp with halo glow behind them
3. Bars should animate smoothly (no frame-to-frame flickering)
4. On beats, bars should flash toward white and decay gradually (~5 frames)
5. Quiet passages should show small-but-visible bars (power curve effect)
6. Test glow off: bars should still be crisp, no regression
