# Plan: Fix AxiosError 400 in Media Editor + Add Debug Logging

## Context

The media editor's `st_canvas` component throws `AxiosError: Request failed with status code 400` when a photo is uploaded. Investigation shows:

- `streamlit-drawable-canvas` 0.9.3 passes `background_image` (PIL Image) to Streamlit, which registers it with the internal `MediaFileHandler` and generates a URL like `/_stcore/media/{hash}`
- The canvas frontend JS fetches that URL to render the background photo
- In Streamlit 1.39.0, the MediaFileHandler URL is unstable — on reruns or mode switches (which change the canvas `key`), the old URL expires/mismatches and returns **400**
- Disabling XSRF helped partially but the root issue is the MediaFileHandler registration, not CSRF

**Fix**: Stop using `background_image=` (the PIL route) entirely. Instead, encode the photo as a base64 data URL once and inject it into the FabricJS canvas JSON as `backgroundImage`. FabricJS loads it directly from the data URL — no HTTP request to Streamlit's media server.

The user also asked whether there is background logging. Yes: the app writes structured JSON logs to `/app/logs/tangerine.log` (volume `etl_logs`). But `media_editor.py` currently does not use it. We'll add a logger so errors show up there.

---

## File to Modify

| File | Action |
|------|---------|
| `admin/pages/media_editor.py` | Fix `_render_image_editor` — replace `background_image=` with FabricJS `backgroundImage` in JSON; add logger |

---

## Implementation

### 1. Base64 background (eliminates 400)

On new file upload, resize the PIL image to canvas dimensions (aspect-ratio-preserved), convert to base64 PNG, store once in session state:

```python
# Aspect-ratio-correct canvas dimensions
ratio = w / h
if w > 800 or h > 600:
    if w / 800 >= h / 600:
        canvas_w, canvas_h = 800, int(800 / ratio)
    else:
        canvas_w, canvas_h = int(600 * ratio), 600
else:
    canvas_w, canvas_h = w, h

# Encode for FabricJS (once per file)
if "_bg_data_url" not in st.session_state:
    buf = io.BytesIO()
    img.resize((canvas_w, canvas_h), Image.LANCZOS).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    st.session_state["_bg_data_url"] = f"data:image/png;base64,{b64}"
```

### 2. Inject into FabricJS JSON

Build `initial_drawing` on every render by merging the stored objects with the background:

```python
initial_drawing = {
    "version": "5.3.0",
    "objects": st.session_state["canvas_json"].get("objects", []),
    "backgroundImage": {
        "type": "image",
        "version": "5.3.0",
        "left": 0, "top": 0,
        "width": canvas_w, "height": canvas_h,
        "src": st.session_state["_bg_data_url"],
        "scaleX": 1.0, "scaleY": 1.0,
        "selectable": False, "hasControls": False, "evented": False,
    },
}
```

Pass `background_image=None` to `st_canvas`. The background photo is rendered entirely by FabricJS.

### 3. Persist only objects (not background)

When saving canvas state back, store only the `objects` array (avoids re-storing the large base64 in session state):

```python
if canvas_result.json_data is not None:
    st.session_state["canvas_json"]["objects"] = canvas_result.json_data.get("objects", [])
```

### 4. Reset Canvas

Clear objects only, not the background:
```python
if st.button("↩️ Reset Canvas"):
    st.session_state["canvas_json"] = {"version": "5.3.0", "objects": []}
    st.rerun()
```

### 5. Download

`canvas_result.image_data` is a full RGBA render of FabricJS canvas — background photo + all objects + strokes — so download works as-is. No change needed.

### 6. Add debug logging

At the top of `_render_image_editor`, set up a standard Python logger that writes to the existing log file:

```python
import logging
logger = logging.getLogger("media_editor")
```

Wrap the session state setup in try/except and log exceptions:
```python
except Exception as e:
    logger.exception("media_editor error: %s", e)
    show_error(f"Error loading image: {e}")
    return
```

---

## Session State Keys

| Key | Purpose |
|-----|---------|
| `_uploaded_name` | Tracks current file name (top-level, already exists) |
| `_uploaded_bytes` | Cached raw bytes (top-level, already exists) |
| `_editor_file` | Triggers reset when file changes |
| `_editor_img` | Cached PIL Image (for size info only) |
| `_bg_data_url` | Base64 PNG data URL of resized photo |
| `canvas_json` | FabricJS objects array `{"version":..., "objects":[...]}` |
| `canvas_mode` | Active mode: paint/text/shapes/overlay/move |

Reset `_bg_data_url` and `canvas_json` when `_editor_file` changes (new upload).

---

## Checking Logs

To view errors in production:
```bash
docker exec tangerine-admin-1 tail -f /app/logs/tangerine.log
```
Or from host (volume is `etl_logs`):
```bash
docker exec tangerine-admin-1 cat /app/logs/tangerine.log | python3 -m json.tool | grep media_editor
```

---

## Verification

1. Rebuild: `docker compose build admin && docker compose up -d admin`
2. Upload `rick_and_morty.png` — canvas should appear immediately with photo as background, no 400 in browser console
3. Switch modes — background photo persists
4. Paint/Text/Shapes/Overlay — all work on top of photo
5. Download PNG — result includes photo + all edits
6. Upload a second image — canvas resets cleanly
7. Check logs: `docker exec tangerine-admin-1 tail /app/logs/tangerine.log`
