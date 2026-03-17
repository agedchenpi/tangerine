# Plan: DaVinci Resolve-Style UX Improvements for Video Editor

## Context

The video editor was recently rebuilt with an interactive timeline component and canvas preview, but it's missing essential NLE (non-linear editor) controls. Two issues reported:

1. **No transport controls** — no play/pause, step forward/back, or go-to-start/end buttons. Only a bare slider for scrubbing. Users can't preview playback or step frame-by-frame.
2. **+Video tool unusable** — uploading a second video fails silently due to `new_vid.read()` on a potentially-exhausted buffer, and there's no resolution mismatch warning.

Goal: Add DaVinci Resolve-style transport controls, fix the +Video tool, and improve the timeline component.

## Files to Modify

| File | Changes |
|------|---------|
| `admin/pages/media_editor.py` | Transport bar, +Video fix, layout restructure, preview clip |
| `admin/components/timeline_editor/frontend/index.html` | Taller rows, source labels, keyboard shortcuts |
| `admin/components/timeline_editor/__init__.py` | No changes needed |

## Change 1: Transport Bar with Playback Controls

**New function `_render_transport_bar()`** — placed full-width between the canvas/controls columns and the timeline.

Layout:
```
[Timecode: 00:03.5 / 00:12.5]
[|<<] [|<] [▶ Preview] [>|] [>>|]     (5 columns)
[──────── Playhead Slider ────────]    (full width)
```

- **|<<** (Go to start): `_tl_playhead = 0.0`
- **|<** (Step back): `_tl_playhead -= 0.1` (clamped to 0)
- **▶ Preview**: Renders 3-5s clip around playhead via moviepy (`preset='ultrafast'`), shows with `st.video()`. Stores bytes in `ss["_preview_clip_bytes"]`.
- **>|** (Step forward): `_tl_playhead += 0.1` (clamped to total_dur)
- **>>|** (Go to end): `_tl_playhead = total_dur`
- **Timecode**: `_format_timecode()` helper → `MM:SS.f` format
- **Slider**: Moved from inside `col_canvas` (line 849) to here

**New function `_render_preview_clip()`**:
- Window: `start = max(0, playhead - 1.0)`, `end = min(total_dur, playhead + 4.0)`
- Render via moviepy with `preset='ultrafast'`, reduced quality
- Show spinner during render, then `st.video(preview_bytes)`
- Close button clears preview

**Session state additions** (init block at ~line 725):
- `ss["_preview_clip_bytes"] = None`

## Change 2: Fix +Video Tool

**Problem** (lines 950-963): `new_vid.read()` can fail because Streamlit's `UploadedFile` buffer may already be consumed on rerun.

**Fix**: Cache uploaded video bytes immediately, same pattern as main upload (lines 33-36):

```python
elif tool == "video":
    st.caption("Add another video clip to the timeline.")
    new_vid = st.file_uploader(
        "Upload video", type=["mp4", "mov", "avi", "mkv", "webm"], key="v_new_video",
    )
    # Cache bytes immediately like the main uploader does
    if new_vid is not None and ss.get("_new_vid_name") != new_vid.name:
        ss["_new_vid_name"] = new_vid.name
        ss["_new_vid_bytes"] = new_vid.read()

    has_new = ss.get("_new_vid_bytes") is not None and new_vid is not None
    if st.button("Add Video", key="btn_add_video", use_container_width=True, disabled=not has_new):
        try:
            src_id = _add_video_source(ss, ss["_new_vid_bytes"], ss["_new_vid_name"])
            new_src = ss["_video_sources"][src_id]
            new_w, new_h = new_src["size"]
            if (new_w, new_h) != (vw, vh):
                show_warning(f"Resolution mismatch: {new_w}x{new_h} vs primary {vw}x{vh}. Output uses primary resolution.")
            show_success(f"Added {ss['_new_vid_name']} to timeline.")
            ss.pop("_new_vid_bytes", None)
            ss.pop("_new_vid_name", None)
            st.rerun()
        except Exception as e:
            show_error(str(e))
```

Also add validation in `_add_video_source()` (line 444):
- Check `len(file_bytes) > 0`
- Check `clip.duration is not None and clip.duration > 0`

## Change 3: Layout Restructure

Move from current layout:
```
[Canvas + Slider] [3]  |  [Controls] [2]
[Timeline]
```

To DaVinci Resolve layout:
```
[Canvas Preview] [3]   |  [Controls] [2]
────────────────────────────────────────
[Transport Bar: timecode + buttons + slider]  (full width)
[Preview clip video player]                   (full width, when playing)
────────────────────────────────────────
[Timeline Component]                          (full width)
```

Implementation:
1. Remove playhead slider from inside `col_canvas` (lines 848-855)
2. After the `with col_controls:` block ends (~line 1065), add `st.divider()` + `_render_transport_bar()` call
3. Preview clip display goes between transport bar and timeline
4. Timeline component stays at bottom

## Change 4: Timeline Component JS Enhancements

**In `index.html`:**

### Taller rows
- `ROW_H`: 32 → 40 (easier click targets)

### Source name labels on V1 clips
- Pass `source_name` in segment data from Python (already have source names in `sources` dict)
- JS label: show `seg.source_name.substring(0, 15)` instead of time range

### Keyboard shortcuts
Add `keydown` listener (only when iframe has focus):
- **Space**: send `{action: "play_toggle"}`
- **ArrowLeft**: send `{action: "step_back"}`
- **ArrowRight**: send `{action: "step_forward"}`
- **Home**: send `{action: "goto_start"}`
- **End**: send `{action: "goto_end"}`

Handle in `_process_timeline_action()`:
- `step_back/forward/goto_start/goto_end`: modify `_tl_playhead`
- `play_toggle`: set `ss["_play_preview_requested"] = True`

### Playhead handle larger
- Increase triangle from 6px half-width to 8px for easier grabbing
- `PLAYHEAD_W`: 12 → 16

## Change 5: Segment Data Enhancement for Python→JS

Update `seg_data` serialization (line ~1071) to include `source_name`:

```python
seg_data = [
    {"id": s["id"], "src_start": s["src_start"], "src_end": s["src_end"],
     "source_id": s.get("source_id", "source_0"),
     "source_name": sources.get(s.get("source_id", "source_0"), {}).get("name", "?")}
    for s in segments
]
```

## Implementation Order

1. Fix +Video tool (Change 2) — bug fix, smallest scope
2. Transport bar + preview clip (Changes 1 & 3) — layout restructure with new controls
3. Timeline JS enhancements (Change 4 & 5) — taller rows, labels, keyboard shortcuts

## Verification

1. Upload MP4 → canvas shows first frame, transport bar visible below
2. Click step forward/back → frame updates by 0.1s increments
3. Click go-to-start/end → playhead jumps correctly
4. Click "Preview" → spinner, then short video clip plays inline
5. Playhead slider still syncs with timeline component
6. Keyboard: click timeline, press arrow keys → playhead steps, space → preview
7. +Video: upload second clip → success message, segment appears on V1 with filename label
8. +Video with different resolution → warning shown, render still works
9. Timeline rows are taller and easier to click
10. V1 segments show source filenames instead of just time ranges
