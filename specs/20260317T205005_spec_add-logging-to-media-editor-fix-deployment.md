# Plan: Add Logging to Media Editor + Fix Deployment

## Context

The media editor has **zero operational logging**. The `logger` on line 14 is defined but only used in 2 exception handlers for the image editor. All video editor operations — uploads, +Video, preview rendering, timeline actions, frame extraction — run with no logging. When things fail (like +Video or preview), they fail silently because:

1. `_extract_frame_at_time()` catches all exceptions and returns `None` silently
2. `_render_preview_clip()` only shows transient `show_error()` toasts that disappear
3. No action logging — we can't tell what the user did or what state the system was in

Additionally, the **container is running stale code** — the recent transport bar, +Video fix, and preview features were never deployed. The container still has the old `new_vid.read()` bug.

**Goal**: Add comprehensive logging so all media editor actions are debuggable, fix silent failures, and rebuild the container with the latest code.

## Files to Modify

| File | Changes |
|------|---------|
| `admin/pages/media_editor.py` | Add `logger.info/error/debug` calls throughout video editor |
| `admin/components/notifications.py` | Add optional logging to notification helpers |
| `Dockerfile.streamlit` | Rebuild needed (no file changes, just `docker compose up --build`) |

## Change 1: Add Logging Throughout `media_editor.py`

Add `logger.info()` / `logger.error()` / `logger.debug()` calls at every significant action point. The logger already exists on line 14: `logger = logging.getLogger("media_editor")`.

### Session init (in `_render_video_editor`, ~line 841)
```python
logger.info("Video loaded: %s (%dx%d, %.1fs, %.1f MB)", filename, vw, vh, dur, size_mb)
```

### Frame extraction (`_extract_frame_at_time`, line ~395)
Replace silent `except Exception: return None` with:
```python
except Exception as e:
    logger.error("Frame extraction failed at t=%.1f src=%s: %s", src_t, src_id, e)
    return None
```

### +Video tool (after `_add_video_source` call, ~line 1100)
```python
logger.info("Added video source: %s (src_id=%s, %dx%d, %.1fs)", ss["_new_vid_name"], src_id, new_w, new_h, new_src["duration"])
```
And in the except block:
```python
logger.error("Failed to add video source %s: %s", ss.get("_new_vid_name", "?"), e, exc_info=True)
```

### Preview clip (`_render_preview_clip`, ~line 806)
```python
# Before rendering:
logger.info("Rendering preview clip: playhead=%.1f, window=%.1f-%.1f", playhead, start, end)
# After success:
logger.info("Preview rendered: %d bytes", len(ss["_preview_clip_bytes"]))
# On error:
logger.error("Preview render failed: %s", e, exc_info=True)
```

### Transport bar actions (`_render_transport_bar`)
```python
logger.debug("Transport: goto_start")
logger.debug("Transport: step_back to %.1f", ss["_tl_playhead"])
logger.debug("Transport: preview requested")
logger.debug("Transport: step_fwd to %.1f", ss["_tl_playhead"])
logger.debug("Transport: goto_end")
```

### Timeline actions (`_process_timeline_action`)
```python
logger.debug("Timeline action: %s", action)
```

### Full render (`_render_video_pipeline`)
```python
# Before:
logger.info("Starting full render: %d segments, %d texts, %d images", len(segments), len(texts), len(images))
# After success (before return):
logger.info("Render complete: %d bytes", len(result))
# On error:
logger.error("Render failed: %s", e, exc_info=True)
```

### Add video source (`_add_video_source`)
```python
# After validation:
logger.info("Writing video source to temp: %s (%d bytes)", filename, len(file_bytes))
# After metadata read:
logger.info("Video source metadata: %s duration=%.1f size=%s", filename, duration, size)
```

### Split segment
```python
logger.info("Split segment %d at timeline t=%.1f", seg_id, split_time)
```

### Delete clip
```python
logger.info("Delete clip: track=%s id=%d", track, clip_id)
```

### Clear all
```python
logger.info("Clear all: reset timeline to original")
```

## Change 2: Add Logging to `notifications.py`

Add a module-level logger and log every notification so they appear in Docker logs:

```python
import logging

logger = logging.getLogger("notifications")

def show_error(message: str):
    logger.error("UI error: %s", message)
    st.error(f"🚨 **Error!** {message}", icon="🚨")

def show_warning(message: str):
    logger.warning("UI warning: %s", message)
    st.warning(f"⚠️ **Warning!** {message}", icon="⚠️")

def show_success(message: str):
    logger.info("UI success: %s", message)
    st.success(f"✅ **Success!** {message}", icon="✅")
    st.toast(f"✅ {message}", icon="✅")

def show_info(message: str):
    logger.info("UI info: %s", message)
    st.info(f"ℹ️ **Info:** {message}", icon="ℹ️")
```

This way **every user-facing message also appears in `docker compose logs admin`**.

## Change 3: Fix `st.video()` MIME Type

Add `format="video/mp4"` to all `st.video()` calls in the media editor. Currently 4 calls have no MIME type specified, which can cause browser playback issues:

- `_render_preview_clip`: 2 calls → add `format="video/mp4"`
- `_render_video_editor` canvas fallback: 2 calls → add `format="video/mp4"`

## Change 4: Rebuild and Deploy Container

```bash
docker compose up -d --build admin
```

This is **required** — the container is currently running stale code without:
- The +Video byte-caching fix
- The transport bar / preview functions
- Any of the logging we're adding

## Implementation Order

1. Add logging to `notifications.py` (Change 2) — smallest scope, benefits all pages
2. Add logging to `media_editor.py` (Change 1) — the bulk of the work
3. Fix `st.video()` MIME types (Change 3) — quick fix
4. Rebuild container (Change 4) — deploy everything

## Verification

1. `python3 -m py_compile admin/pages/media_editor.py` — syntax check
2. `docker compose up -d --build admin` — rebuild
3. Upload a video in the media editor
4. `docker compose logs admin --tail 50` — should see "Video loaded: ..." log line
5. Try +Video tool → logs should show "Added video source" or "Failed to add video source" with traceback
6. Try Preview → logs should show "Rendering preview clip" and either success bytes or error traceback
7. Check that transport bar and playhead slider appear (confirms latest code deployed)
