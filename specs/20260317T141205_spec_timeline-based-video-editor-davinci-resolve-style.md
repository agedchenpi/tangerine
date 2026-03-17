# Plan: Timeline-Based Video Editor (DaVinci Resolve Style)

## Context

The video editor was recently rewritten from disconnected tabs to an effects queue, but the user wants a proper **timeline-based editor** inspired by DaVinci Resolve's Edit page. The key difference: instead of a flat effects list, the editor should have **visual tracks** (V1 video, T1 text, I1 image) where clips are represented as positioned blocks on a timeline, and the video track can be **split** into segments like a real NLE.

**Dockerfile already fixed** (ImageMagick + fonts-liberation installed) — no changes needed there.

## File to Modify

**`admin/pages/media_editor.py`** — rewrite lines 299–557 (video editor section: helpers + `_render_video_editor()`)

## Key References (read-only)
- `admin/utils/ui_helpers.py:9-43` — `is_dark_mode()`, `get_theme_colors()` for theme-aware HTML
- `admin/styles/custom.css` — design tokens (no modification needed)
- `admin/components/notifications.py` — `show_success`, `show_error`, `show_warning`

## Layout

```
col_preview [3]                    | col_controls [2]
─────────────────────────────────  | ──────────────────────────────
Video Preview (original/rendered)  | Tool: [Select | Split | +Text | +Image]
Metadata caption                   | ──────────────────────────────
                                   | Selected Clip Properties:
                                   |   (context-dependent controls)
                                   | ──────────────────────────────
                                   | [▶ Render] [↩️ Clear] [⬇️ DL]
═══════════════════════════════════════════════════════════════════
Timeline (full width, st.markdown with unsafe_allow_html=True):
  Time:  |0s      |2s      |4s      |6s      |8s      |10s
  V1:    [====Seg 1====][====Seg 2====][======Seg 3======]
  T1:    [  "Hello World"  ]
  I1:              [ IMG ]
```

## Data Model (session state)

```python
ss["_tl_segments"] = [{"id": 0, "src_start": 0.0, "src_end": duration}]  # subclip ranges in ORIGINAL video
ss["_tl_texts"] = []      # {"id", "text", "start", "end", "fontsize", "color", "position"}
ss["_tl_images"] = []     # {"id", "img_path", "start", "end", "x", "y"}
ss["_tl_selected"] = None # ("segment", id) | ("text", id) | ("image", id)
ss["_tl_next_id"] = 1     # monotonic ID counter
ss["_video_rendered_bytes"] = None
```

- Segment `src_start`/`src_end` = ranges within the **original** source video
- Overlay `start`/`end` = positions in the **composed** timeline (sum of all segment durations)

## Helper Functions (replace `_format_effect` and `_apply_effects`)

### `_tl_duration(segments) -> float`
Sum of `(seg["src_end"] - seg["src_start"])` for all segments.

### `_tl_get_next_id(ss) -> int`
Increment + return `ss["_tl_next_id"]`.

### `_tl_split_segment(segments, seg_id, split_time, ss) -> list`
- Find segment by ID, compute its timeline offset (sum of preceding durations)
- Convert timeline-relative `split_time` to source-relative: `src_split = seg["src_start"] + (split_time - offset)`
- Replace segment with two new segments (new IDs), return updated list

### `_tl_delete_clip(ss, track, clip_id)`
- Remove from appropriate list; prevent deleting last segment
- Clamp overlay times if timeline shortened; remove overlays past new end
- Clear rendered bytes + selection if deleted was selected

### `_render_timeline_html(segments, texts, images, selected, total_dur) -> str`
Pure HTML/CSS rendered via `st.markdown(unsafe_allow_html=True)`:
- Use `get_theme_colors()` for dark/light mode colors (inline styles)
- Container: relative position, ~160px height, rounded corners
- **Time ruler** (top, 20px): auto-scaled tick marks (1s/2s/5s/10s steps based on duration)
- **V1 row** (30px): blue (`#4A90D9`) segment blocks, positioned as `left/width` percentages
- **T1 row** (30px): green (`#50C878`) text blocks with truncated labels
- **I1 row** (30px): purple (`#9B59B6`) image blocks labeled "IMG"
- Selected clip: `2px solid` accent border (`#FFA05C` dark / `#FF8C42` light)
- Track labels: 60px left column ("V1", "T1", "I1")

### `_render_clip_properties(ss, track, clip, total_dur, vw, vh)`
Context-dependent properties panel in right column:
- **Segment**: src_start/src_end number inputs (trim), Split button, Delete button (disabled if last)
- **Text**: text input, fontsize, color picker, position selectbox, start/end, Update + Delete buttons
- **Image**: path (read-only), start/end, x/y sliders, Update + Delete buttons
- **None selected**: caption "Select a clip to edit"

### `_render_video_pipeline(src_path, segments, texts, images) -> bytes | None`
Render pipeline (replaces `_apply_effects`):
1. Create subclips for each segment from source
2. `mpe.concatenate_videoclips(subclips)` to join V1
3. Create TextClip/ImageClip overlays with time positions
4. `CompositeVideoClip([base] + overlays)` if overlays exist
5. Write to temp MP4, return bytes

## Main Function: `_render_video_editor()` Flow

1. **Guards**: 500MB limit, 200MB warning, moviepy import check
2. **Session init** (on new file): write temp file once, read metadata, init timeline with single full-duration segment
3. **Columns**: `st.columns([3, 2], gap="large")`
4. **Left col**: video preview (rendered or original) + metadata caption
5. **Right col**:
   - Tool selector: `["select", "split", "text", "image"]` via `st.segmented_control`
   - **select**: Selectbox listing all clips by label → update `_tl_selected` → show properties panel
   - **split**: Number input for time + "Split" button → `_tl_split_segment()`
   - **text**: New overlay controls + "Add Text" button → append to `_tl_texts`
   - **image**: File uploader + controls + "Add Overlay" button → append to `_tl_images`
   - Divider
   - Action buttons: Render, Clear All (2 columns)
   - Download button (only after render)
6. **Timeline** (full width below columns): `_render_timeline_html()` via `st.markdown`

## Key Operations

| Operation | How it works |
|-----------|-------------|
| **Split** | User picks a time; segment containing it splits into two sub-segments |
| **Delete segment** | Remove from list (min 1 required); clamp overlays to new duration |
| **Trim segment** | Edit src_start/src_end in properties panel (range within original video) |
| **Add text/image** | Append to overlay list; start/end in composed timeline coordinates |
| **Edit overlay** | Select → modify properties → Update button |
| **Render** | Concatenate segments → composite overlays → write MP4 |

## Verification

1. **Rebuild Docker image**: `docker compose build admin && docker compose up -d admin`
   - This is required to pick up the code changes (volume-mounted or rebuilt)
2. Upload MP4 → preview in left col, single-segment timeline at bottom
3. Split at 5s → timeline shows two segments
4. Select segment → properties panel shows trim controls
5. Add text overlay → green block appears on T1 track
6. Add image overlay → purple block on I1 track
7. Delete a segment → timeline updates, overlays clamp
8. Render → spinner, rendered preview replaces original
9. Download works
10. Clear All → resets to single segment, no overlays
11. Dark mode toggle → timeline colors adapt
