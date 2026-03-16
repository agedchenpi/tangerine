# Plan: Fix AxiosError 400 When Loading PNG in Media Editor

## Context

The media editor still throws AxiosError 400 when uploading a .png file, despite previous fixes (base64 backgroundImage, stable canvas key, removed auto-sync loop, JPEG compression). The remaining root causes:

1. **Library incompatibility**: `streamlit-drawable-canvas==0.9.3` is archived (since March 2025) and uses the deprecated `st_image.image_to_url()` API that was moved in Streamlit 1.39.0. A maintained fork `streamlit-drawable-canvas-fix==0.9.8` fixes this import (`from streamlit.elements.lib.image_utils import image_to_url`). Confirmed: the fork uses the same Python module name `streamlit_drawable_canvas` — no import changes needed.

2. **WebSocket traffic flood**: `update_streamlit=True` fires on every mouse event during painting, sending the full canvas PNG data URL (~500KB-2MB) + FabricJS JSON back to the server, and the server sends `initialDrawing` (with ~100KB base64 background) back to the client — 10-30 times per second. This saturates the WebSocket and creates race conditions that produce 400 errors.

---

## Files to Modify

| File | Change |
|------|--------|
| `requirements/admin.txt` | Swap `streamlit-drawable-canvas==0.9.3` → `streamlit-drawable-canvas-fix==0.9.8` |
| `admin/pages/media_editor.py` | Change `update_streamlit=True` → `update_streamlit=False` |

---

## Implementation

### 1. Switch to maintained fork

**File**: `requirements/admin.txt` (line 15)

```diff
- streamlit-drawable-canvas==0.9.3  # Freehand drawing component
+ streamlit-drawable-canvas-fix==0.9.8  # Freehand drawing component (maintained fork)
```

The fork fixes the deprecated `image_to_url` import and `baseUrlPath` routing in the React frontend. Same module name `streamlit_drawable_canvas` — no code changes needed for the import on line 54.

### 2. Set `update_streamlit=False`

**File**: `admin/pages/media_editor.py` (line 152)

```diff
- update_streamlit=True,
+ update_streamlit=False,
```

This stops the per-mouse-event WebSocket round trips. FabricJS still works fully client-side — painting, dragging, resizing all happen in the browser without server communication.

**Download button impact**: With `update_streamlit=False`, the component still sends data on discrete completion events (`onPathCreated`, `onObjectModified`) — not just mouse moves. So `canvas_result.image_data` populates after each completed stroke or object action. The existing fallback (`else: img.save(...)`) handles the initial `None` state gracefully. No code change needed for the download logic.

---

## What stays unchanged (already applied in working copy)

- `key="canvas"` — stable canvas key (prevents remount on mode switch)
- `background_image=None` + base64 `backgroundImage` in `initial_drawing` — avoids MediaFileHandler
- JPEG Q70 background compression — reduces payload size
- Removed auto-sync loop — `canvas_json["objects"]` only updates on explicit actions
- Add Text/Overlay merge `canvas_result.json_data` before appending

---

## Verification

1. `docker compose build admin && docker compose up -d admin`
2. Upload a .png file — no AxiosError 400 in browser console
3. Paint freely — smooth strokes, no flashing
4. Switch modes — canvas state preserved
5. Add Text → Move → drag — object stays where dropped
6. Download PNG — includes background + all edits (after completing at least one action)
7. Hard refresh browser → re-upload → no 400
8. Check browser DevTools Network tab — dramatically fewer WebSocket messages during painting
