# Plan: Timeline Segment Reorder + PiP Layout Presets

## Context

The video editor supports multiple video sources (V1 segments + V2 overlays), but:
1. V1 segments can't be reordered — they're locked in upload order
2. V2 overlays have x/y/scale controls but no quick layout presets for common arrangements (PiP corners, center, full)

The user wants to rearrange segment order and easily position overlay videos for simultaneous playback.

## File to Modify

| File | Change |
|------|--------|
| `admin/pages/media_editor.py` | Add reorder helper, reorder buttons in segment properties, PiP preset function, preset buttons in V2 properties |

No frontend (`index.html`) changes needed — the timeline canvas already renders segments in list order.

## Changes

### 1. Add `_tl_reorder_segment()` helper (~line 344, after `_tl_split_segment`)

Swaps a segment with its neighbor in `_tl_segments`. Takes `direction` (-1 = earlier, +1 = later). Invalidates render cache.

### 2. Add reorder buttons in segment properties panel (lines 529–543)

Between the `src_end` input and the Update/Delete buttons, add a row with two columns:
- **"◀ Move Earlier"** — calls `_tl_reorder_segment(ss, clip["id"], -1)`, disabled if first segment
- **"Move Later ▶"** — calls `_tl_reorder_segment(ss, clip["id"], +1)`, disabled if last segment

### 3. Add `_apply_layout_preset()` function (~line 625, before render pipeline)

Sets `x`, `y`, `scale` on the first V2 overlay based on preset name. Takes video dimensions `vw`, `vh` for positioning. Presets:
- `pip_top_right` / `pip_top_left` / `pip_bottom_right` / `pip_bottom_left` — scale 0.3, positioned in corners
- `pip_center` — scale 0.5, centered
- `full_overlay` — scale 1.0 at origin

Invalidates both `_video_rendered_bytes` and `_frame_cache_key`.

### 4. Add preset buttons in V2 overlay properties (after scale slider, line 589)

Two rows of 3 buttons each:
```
[ PiP ↗ ] [ PiP ↙ ] [ PiP ↘ ]
[ PiP ↖ ] [ Center ] [ Full  ]
```

Each calls `_apply_layout_preset()` then `st.rerun()`.

## Verification

1. `python3 -m py_compile admin/pages/media_editor.py`
2. `docker compose up -d --build admin`
3. Upload video → select the segment in timeline → verify Move Earlier/Later buttons appear, Earlier is disabled for first segment
4. Add a second segment (split or +Video) → select it → Move Earlier → verify order swaps in timeline
5. Add a V2 overlay (+Video) → select it → verify PiP preset buttons appear
6. Click "PiP ↗" → preview should show overlay small in top-right corner
7. Click "Center" → overlay should be centered at 50% scale
8. Render → verify final video reflects the layout
