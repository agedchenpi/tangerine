# Plan: Interactive Timeline Video Editor with Canvas Preview

## Context

The video editor currently has a static HTML timeline (display-only) with selectbox-based clip selection. The user wants a proper interactive editor with:

1. **Interactive timeline component** — click to select clips, drag edges to resize/trim, drag overlays to reposition in time, draggable playhead for scrubbing
2. **Canvas preview (st_canvas)** — show video frame at playhead time with draggable FabricJS text/image overlays for WYSIWYG x/y positioning
3. **Multiple video sources** — upload additional video files as new clips on the timeline

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `admin/components/timeline_editor/__init__.py` | **NEW** | Python wrapper for custom Streamlit component |
| `admin/components/timeline_editor/frontend/index.html` | **NEW** | Interactive HTML5 Canvas timeline (JS + CSS) |
| `admin/pages/media_editor.py` lines 299–857 | **REWRITE** | Video editor with canvas preview + timeline integration |

**Read-only references:**
- `admin/utils/ui_helpers.py:9-43` — `get_theme_colors()` dict structure
- `admin/components/notifications.py` — `show_success`, `show_error`, `show_warning`
- Image editor (lines 52–296) — st_canvas patterns to reuse

## Layout

```
Canvas (st_canvas) [3]              | Controls [2]
──────────────────────────────────  | ──────────────────────────
Video frame at playhead time        | Tool: [Select|Split|+Video|+Text|+Image]
+ Draggable text/image overlays    | Tool-specific controls
                                    | ──────────────────────────
Playhead: [0s -------●------ 10s]  | Selected clip properties
                                    | ──────────────────────────
                                    | [Render] [Clear All]
                                    | [Download]
═══════════════════════════════════════════════════════════════
Interactive Timeline Component (full width, custom Streamlit component):
  Playhead ▼ (draggable)
  Time: |0s     |2s     |4s     |6s     |8s     |10s
  V1:   [==clip1.mp4==][==clip2.mp4==][====clip1====]
  T1:   [  "Hello World"  ]
  I1:            [ IMG ]
```

## Data Model (session state)

```python
ss["_video_sources"] = {           # multiple source files
    "source_0": {"path": "/tmp/x.mp4", "duration": 12.5, "size": (1920,1080), "name": "clip.mp4"}
}
ss["_video_next_source_id"] = 1
ss["_tl_segments"] = [             # V1 track — each references a source
    {"id": 0, "source_id": "source_0", "src_start": 0.0, "src_end": 12.5}
]
ss["_tl_texts"] = []               # {"id", "text", "fontsize", "color", "x", "y", "start", "end"}
ss["_tl_images"] = []              # {"id", "img_path", "img_b64", "start", "end", "x", "y", "scale"}
ss["_tl_selected"] = None          # {"track": "segment"|"text"|"image", "id": N} or None
ss["_tl_next_id"] = 1
ss["_tl_playhead"] = 0.0           # scrub position in composed timeline
ss["_video_rendered_bytes"] = None
```

Key changes from current model:
- Segments gain `source_id` (multi-source support)
- Text overlays: `position` string → pixel `x`, `y` (canvas-driven)
- Image overlays: add `img_b64` (for canvas display), `scale`
- `_tl_selected`: tuple → dict (JSON-serializable for JS component)
- New: `_tl_playhead` for scrub position

## Step 1: Custom Timeline Component

### `admin/components/timeline_editor/__init__.py`

```python
import streamlit.components.v1 as components
from pathlib import Path

_component_func = components.declare_component(
    "timeline_editor",
    path=str(Path(__file__).parent / "frontend"),
)

def timeline_editor(segments, texts, images, selected, total_duration, playhead, theme_colors, key="timeline_editor"):
    return _component_func(
        segments=segments, texts=texts, images=images,
        selected=selected, total_duration=total_duration,
        playhead=playhead, theme_colors=theme_colors,
        key=key, default=None,
    )
```

### `admin/components/timeline_editor/frontend/index.html`

Single-file HTML/CSS/JS using the Streamlit iframe protocol (no npm build):

**Protocol:**
- Component → Streamlit: `postMessage({isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1})`
- Component → Streamlit: `postMessage({isStreamlitMessage: true, type: "streamlit:setComponentValue", value: data})`
- Component → Streamlit: `postMessage({isStreamlitMessage: true, type: "streamlit:setFrameHeight", height: N})`
- Streamlit → Component: message with `type: "streamlit:render"`, `args`, `theme`

**Rendering (HTML5 Canvas):**
- Time ruler (top, 24px): auto-scaled ticks
- V1 row (32px): blue `#4A90D9` segment blocks
- T1 row (32px): green `#50C878` text blocks with truncated labels
- I1 row (32px): purple `#9B59B6` image blocks labeled "IMG"
- Playhead: red vertical line with draggable triangle handle
- Selected clip: accent border from `theme_colors.accent`
- Track labels: 50px left column

**Interactions:**
| Interaction | Returns to Python |
|-------------|-------------------|
| Click clip (no drag) | `{"action": "select", "track": "segment", "id": 0}` |
| Click empty area | `{"action": "select", "track": null, "id": null}` |
| Drag clip edge | `{"action": "resize", "track": "text", "id": 2, "start": 0.5, "end": 3.0}` |
| Drag clip body (T1/I1) | `{"action": "move", "track": "text", "id": 2, "start": 1.0, "end": 4.0}` |
| Drag/click playhead | `{"action": "scrub", "time": 3.5}` |

**Drag rules:**
- V1 segments: edge drag only (trim), no body drag (segments are contiguous)
- T1/I1 overlays: both edge drag (resize) and body drag (move in time)
- Hit test: 6px from edge = resize mode, otherwise = move mode
- Cursor feedback: `col-resize` on edges, `grab`/`grabbing` on bodies

## Step 2: Canvas Preview (st_canvas)

### Frame extraction

New helper `_extract_frame_at_time(sources, segments, playhead)`:
- Walk segments to find which one contains the playhead time
- Compute source-relative time: `src_t = seg["src_start"] + (playhead - offset)`
- Call `moviepy.VideoFileClip(path).get_frame(src_t)` → numpy array → PIL Image
- Cache in session state keyed by `(round(playhead, 1), segment_hash)` to avoid re-extraction on every rerun

### Canvas setup

Same pattern as the image editor (lines 126–157):
- Frame image → base64 JPEG → `backgroundImage` in FabricJS `initial_drawing`
- Build FabricJS objects for overlays **active at playhead time** (where `start <= playhead <= end`):
  - Text → `{"type": "i-text", "left": x, "top": y, "text": ..., "fontSize": ..., "fill": ...}`
  - Image → `{"type": "image", "left": x, "top": y, "src": img_b64, "scaleX": ..., "scaleY": ...}`
- Canvas in `transform` drawing mode (drag to reposition)
- Coordinates scaled between video resolution and canvas display size

### Position sync back to data model

New helper `_sync_canvas_to_overlays(canvas_result, ss, canvas_w, canvas_h, vw, vh)`:
- Read `canvas_result.json_data["objects"]`
- Match by positional index (objects built in deterministic order: texts sorted by id, then images sorted by id)
- Convert canvas coords → video coords: `video_x = int(obj["left"] * vw / canvas_w)`
- Update overlay `x`, `y` in session state if changed
- Invalidate rendered bytes on change

### Playhead slider

`st.slider("Playhead", 0.0, total_dur, playhead, 0.1, key="_playhead_slider")` below the canvas. Syncs with timeline component's playhead.

## Step 3: Multi-Source Video Support

### Adding video sources

"+Video" tool in the right column:
- `st.file_uploader` for additional video files
- New helper `_add_video_source(ss, file_bytes, filename)`:
  - Write to tempfile, read metadata with moviepy
  - Add to `_video_sources` dict with new `source_id`
  - Append new segment to `_tl_segments` at end of timeline
  - Set source_id on the segment

### Render pipeline changes

`_render_video_pipeline(sources, segments, texts, images)`:
- Each segment loads from its own `source_id`'s path
- `mpe.VideoFileClip(sources[seg["source_id"]]["path"]).subclip(seg["src_start"], seg["src_end"])`
- Text overlays use `.set_position((txt["x"], txt["y"]))` (pixel coords, not string)
- Concatenate with `method="compose"` (handles resolution mismatches via padding)

## Step 4: `_render_video_editor()` Flow

```
1. Guards: 500MB limit, 200MB warning, moviepy import check
2. Session init (on new file):
   - Create primary source in _video_sources
   - Init single full-duration segment with source_id
   - Init empty texts/images, playhead=0
3. Process timeline action from previous cycle:
   - select → update _tl_selected
   - resize → update clip start/end (roll edit for V1 junctions)
   - move → shift overlay start/end
   - scrub → update _tl_playhead
4. Sync canvas positions (from previous cycle's canvas_result)
5. Compute total_dur, canvas dimensions
6. Extract frame at playhead (cached)
7. st.columns([3, 2]):
   Left col:
     - st_canvas with frame background + active overlay objects
     - Playhead st.slider
   Right col:
     - Tool segmented_control: [select, split, +video, +text, +image]
     - select: properties panel for selected clip (trim, delete, edit)
     - split: segment picker + split time + button
     - +video: file_uploader → _add_video_source()
     - +text: text/fontsize/color/x/y inputs → append to _tl_texts
     - +image: file_uploader + scale → append to _tl_images
     - Divider
     - Render / Clear All buttons (2 cols)
     - Download button (after render)
8. Full-width timeline component:
   result = timeline_editor(segments, texts, images, selected, total_dur, playhead, colors)
   if result: ss["_tl_action"] = result; st.rerun()
```

## Segment Resize Behavior

- **V1 junction edge** (between two segments): **roll edit** — one segment shrinks, adjacent grows, total duration unchanged
- **V1 outer edge** (first segment's left, last segment's right): **trim** — adjusts src_start/src_end within source bounds, changes total duration
- **T1/I1 edges**: freely resize start/end, clamped to [0, total_dur]
- Minimum clip duration: 0.1s

## Verification

1. Upload MP4 → canvas shows first frame, single blue segment on V1 timeline
2. Drag playhead on timeline → canvas frame updates, slider syncs
3. Use slider → timeline playhead syncs
4. Click segment on timeline → accent border, properties panel appears
5. Drag segment edge → segment trims, adjacent adjusts (roll edit)
6. Split tool → two segments appear on V1
7. +Text → green block on T1; text appears on canvas at playhead time; drag text on canvas → x/y updates
8. +Image → purple block on I1; image on canvas; drag to reposition
9. Drag text block on T1 timeline → start/end time shifts
10. +Video → upload second clip → new segment appears at end of V1
11. Render → concatenates all segments + overlays → MP4
12. Download works
13. Clear All → reset to primary source single segment
14. Dark/light mode → timeline + canvas colors adapt
