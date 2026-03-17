# Plan: Video Editor UX Fixes — V2 Track, Preview Visibility, Render Display

## Context

After deploying logging, the user tested the video editor and found three UX issues:
1. **+Video** appends new clips sequentially on V1 (concatenated). User wants them on a **separate V2 track** as overlays, like how T1/I1 work — positioned freely in time.
2. **No obvious play button** — the "Preview" button is buried in the transport bar and easy to miss.
3. **Render button appears to do nothing** — after rendering, the video is only shown in a canvas fallback path. Normally the user just sees a download button with no video player.

## Files to Modify

| File | Changes |
|------|---------|
| `admin/pages/media_editor.py` | V2 data model, render/preview pipeline, display fixes |
| `admin/components/timeline_editor/__init__.py` | Add `video_overlays` parameter |
| `admin/components/timeline_editor/frontend/index.html` | Add V2 row (4th track) |

## Change 1: Add V2 Video Overlay Track

### 1a. New session state — `_tl_video_overlays`

In `_render_video_editor()` session init block (~line 871), add alongside `_tl_texts`/`_tl_images`:
```python
ss["_tl_video_overlays"] = []
```
Also add to "Clear All" reset block (~line 1197).

Each item structure:
```python
{"id": int, "source_id": str, "start": float, "end": float,
 "src_start": float, "src_end": float, "x": 0, "y": 0, "scale": 1.0}
```

### 1b. Modify `_add_video_source()` (~line 446)

Change lines 474-477: instead of appending to `_tl_segments`, append to `_tl_video_overlays`:
```python
ss["_tl_video_overlays"].append({
    "id": _tl_get_next_id(ss),
    "source_id": src_id,
    "start": 0.0, "end": min(duration, _tl_duration(ss["_tl_segments"])),
    "src_start": 0.0, "src_end": duration,
    "x": 0, "y": 0, "scale": 1.0,
})
```
Clamp `end` to V1 total duration so V2 doesn't exceed the timeline.

### 1c. Modify `_tl_delete_clip()` (~line 342)

Add case:
```python
elif track == "video_overlay":
    ss["_tl_video_overlays"] = [v for v in ss["_tl_video_overlays"] if v["id"] != clip_id]
```

### 1d. Modify `_process_timeline_action()` (~line 629)

In the `resize` handler, add `elif track == "video_overlay"` to iterate `_tl_video_overlays` and update `start`/`end`.

In the `move` handler (~line 670), extend the items lookup:
```python
items = (ss["_tl_texts"] if track == "text"
         else ss["_tl_images"] if track == "image"
         else ss["_tl_video_overlays"] if track == "video_overlay"
         else [])
```

### 1e. Add V2 to the Select tool clip list (~line 1029)

After the segments loop and before the texts loop, add:
```python
for vov in ss["_tl_video_overlays"]:
    src_name = sources.get(vov["source_id"], {}).get("name", "?")
    label = f'V2: {src_name} @ {vov["start"]:.1f}-{vov["end"]:.1f}s'
    clip_options.append(label)
    clip_map[label] = {"track": "video_overlay", "id": vov["id"]}
```

### 1f. Add `_render_clip_properties()` case for `video_overlay` (~line 538)

Pattern follows the image overlay properties panel. Fields: source name (caption), start/end times, x/y position, scale, Update/Delete buttons.

### 1g. Modify `_extract_frame_at_time()` (~line 368)

After getting the base frame from V1, composite V2 overlay frames:
```python
# After getting base pil_img, before return:
for vov in ss.get("_tl_video_overlays", []):
    if vov["start"] <= playhead <= vov["end"]:
        vov_src_t = vov["src_start"] + (playhead - vov["start"])
        try:
            vc = mpe.VideoFileClip(sources[vov["source_id"]]["path"])
            vf = vc.get_frame(vov_src_t)
            vc.close()
            ov_img = Image.fromarray(vf)
            if vov.get("scale", 1.0) != 1.0:
                ov_img = ov_img.resize((int(ov_img.width * vov["scale"]), int(ov_img.height * vov["scale"])), Image.LANCZOS)
            pil_img.paste(ov_img, (vov["x"], vov["y"]))
        except Exception as e:
            logger.error("V2 frame extraction failed: %s", e)
```
Note: This requires access to `ss` — add it as a parameter. Currently the function signature is `_extract_frame_at_time(sources, segments, playhead)` — change to `_extract_frame_at_time(sources, segments, playhead, ss)` and update the single call site (~line 917).

### 1h. Modify `_render_video_pipeline()` (~line 568)

Add `video_overlays` parameter. After building `overlays` list for text/images, add V2 clips:
```python
for vov in video_overlays:
    src_clip = mpe.VideoFileClip(sources[vov["source_id"]]["path"])
    sub = (src_clip.subclip(vov["src_start"], vov["src_end"])
           .resize(vov.get("scale", 1.0))
           .set_position((vov["x"], vov["y"]))
           .set_start(vov["start"])
           .set_end(min(vov["end"], base.duration)))
    overlays.append(sub)
```
Update call site at ~line 1224 to pass `ss["_tl_video_overlays"]`.

### 1i. Modify `_render_preview_clip()` (~line 753)

Add `video_overlays` parameter. Same pattern as render pipeline — add V2 subclips active in the preview window. Update call site at ~line 1245.

### 1j. Pass V2 data to timeline JS component

Near line 1252, create serializable data and pass to `timeline_editor()`:
```python
vov_data = [
    {"id": v["id"], "source_id": v["source_id"], "start": v["start"], "end": v["end"],
     "source_name": sources.get(v["source_id"], {}).get("name", "?")}
    for v in ss["_tl_video_overlays"]
]
```

### 1k. Timeline JS — add V2 row

In `admin/components/timeline_editor/frontend/index.html`:

- Add color: `const VOV_COLOR = "#E67E22";` (orange, distinct from V1 blue)
- Change `canvasH` from `ROW_H * 3` to `ROW_H * 4` (both line 27 and line 474)
- Change `labels` from `["V1", "T1", "I1"]` to `["V1", "V2", "T1", "I1"]`; loop `r < 4`
- In `hitTest()`, insert V2 as row index 1:
  ```js
  {track: "video_overlay", items: buildOverlayRects(args.video_overlays || [])}
  ```
  Push T1 to row 2, I1 to row 3
- In `draw()`, add V2 drawing at `rowY(1)` with `VOV_COLOR`; shift T1 to `rowY(2)`, I1 to `rowY(3)`

### 1l. Timeline Python wrapper

In `admin/components/timeline_editor/__init__.py`, add `video_overlays` parameter to both the function signature and the `_component_func()` call.

## Change 2: Make Preview Button More Visible

### 2a. Add play button in canvas area

In `col_canvas`, after the canvas/frame display and before the info caption (~line 1008), add:
```python
if st.button("▶ Play Preview", key="btn_canvas_preview", use_container_width=True, type="primary"):
    ss["_play_preview_requested"] = True
    st.rerun()
```
This puts a big, primary-styled play button directly below the video canvas.

### 2b. Make transport preview button primary

At ~line 728, add `type="primary"` to the existing "▶ Preview" button.

### 2c. Add header to preview output

In `_render_preview_clip()`, before `st.video()` calls, add `st.subheader("Preview")` so the rendered preview is clearly labeled.

## Change 3: Show Rendered Video After Render

### 3a. Display rendered video in canvas area

At the top of `col_canvas` (~line 927), add a check before the normal canvas flow:
```python
with col_canvas:
    if ss.get("_video_rendered_bytes"):
        st.markdown("**Rendered Output**")
        st.video(ss["_video_rendered_bytes"], format="video/mp4")
        if st.button("Back to Editor", key="btn_back_to_editor", use_container_width=True):
            ss["_video_rendered_bytes"] = None
            st.rerun()
    elif st_canvas is not None and frame_img is not None:
        # ... existing canvas code
```
This replaces the canvas with the rendered video, making it impossible to miss. "Back to Editor" returns to the normal editing view.

### 3b. Add completion banner

Before `st.rerun()` after render success (~line 1229), set:
```python
ss["_render_just_completed"] = True
```
Then in the canvas area rendered-output block, check and show:
```python
if ss.pop("_render_just_completed", False):
    st.success("Render complete! Preview your video below.")
```

## Implementation Order

1. **Change 3** (render display) — simplest, highest impact, ~15 lines
2. **Change 2** (preview visibility) — simple UX, ~10 lines
3. **Change 1** (V2 track) — largest scope, ~150 lines across 3 files
4. Rebuild container: `docker compose up -d --build admin`

## Verification

1. `python3 -m py_compile admin/pages/media_editor.py` — syntax check
2. `docker compose up -d --build admin` — rebuild
3. Upload a video → click **Render** → rendered video should display in the canvas area with "Back to Editor" button
4. Click **▶ Play Preview** (big primary button below canvas) → preview clip should appear labeled "Preview"
5. Use **+Video** to add a second clip → it should appear on V2 row in the timeline, not concatenated on V1
6. Move/resize the V2 clip on the timeline → verify drag works
7. Render with V2 overlay → output should show composited video
8. Check `docker compose logs admin --tail 50` for logging output
