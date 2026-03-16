# Plan: Media Editor — Interactive Canvas Refactor

## Context
The image editor currently uses static PIL rendering with sliders for positioning text, shapes, and overlays. The user wants:
- **Text**: No X/Y sliders — just type text, pick text color + background color, click Add, then **drag it** into position on the photo
- **Shapes**: Draw shapes and **drag/move** them on the photo
- **Overlay**: Upload image and **drag/move** it on the photo
- **Draw**: True freehand MS-Paint-style brush over the image with mouse click/drag

This requires replacing the static PIL+slider approach with a **unified interactive canvas** using `streamlit-drawable-canvas` (FabricJS-backed), which supports drag/move/resize via `drawing_mode="transform"`, shape drawing modes, and freehand painting.

## Only File to Modify
| File | Action |
|------|--------|
| `admin/pages/media_editor.py` | **Rewrite `_render_image_editor` only** — video editor is unchanged |

---

## Core Architecture: Unified Interactive Canvas

Replace the four separate PIL-based tabs with a single `st_canvas` component that acts as the interactive surface for all editing. FabricJS (the backend of `streamlit-drawable-canvas`) supports:

- `drawing_mode="freedraw"` — freehand paint strokes
- `drawing_mode="rect"` / `"circle"` / `"line"` — draw shapes directly on canvas
- `drawing_mode="transform"` — drag, resize, rotate any existing object
- `initial_drawing` — inject pre-built FabricJS JSON objects (text, images) that appear as movable objects

### Session State
- `st.session_state["canvas_json"]` — FabricJS JSON dict `{"version": "5.3.0", "objects": [...]}` — persists ALL canvas objects (text, shapes, overlays, paint strokes) across reruns and mode switches
- `st.session_state["_editor_file"]` — tracks loaded file to reset state on new upload
- `st.session_state["canvas_mode"]` — current active tab/mode

### Canvas Key Strategy
Use `key=f"canvas_{mode}"` so the canvas re-initializes when mode switches. On every render, save `canvas_result.json_data` back to session state — this ensures objects survive the key change via `initial_drawing`.

---

## Layout

```
col_canvas (left, wider) | col_controls (right)
─────────────────────────────────────────────────
st_canvas (always visible)  | Tabs: Paint | Text | Shapes | Overlay | Move
                             | (controls relevant to current tab)
                             |
                             | [⬇️ Download PNG]  [↩️ Reset]
```

---

## Tab Specifications

### 🎨 Paint tab
- `drawing_mode = "freedraw"`
- Controls: brush color picker, brush size slider (1–50)
- No "Apply" button needed — strokes are captured automatically in `json_data` as `path` objects
- Hint caption: "Paint directly on the canvas with your mouse"

### ✏️ Text tab
- `drawing_mode = "transform"` (so user can immediately reposition after adding)
- Controls: text input, font size slider (10–120), text color picker, background color picker
- **"Add Text" button** → appends FabricJS `i-text` object to `canvas_json["objects"]`:
  ```json
  {
    "type": "i-text",
    "left": 50, "top": 50,
    "text": "<user input>",
    "fontSize": <size>,
    "fill": "<text_color_hex>",
    "backgroundColor": "<bg_color_hex>",
    "fontFamily": "Arial",
    "selectable": true,
    "hasControls": true
  }
  ```
- Caption hint: "After adding, use Move tab to drag text into position"

### 🔷 Shapes tab
- `drawing_mode` = selectbox choice: `"rect"` / `"circle"` / `"line"`
- Controls: shape type selectbox, color picker, line width slider (1–20)
- User draws shape directly on canvas — no "Add" button needed
- Caption hint: "Draw on the canvas, then switch to Move tab to reposition"

### 🖼️ Overlay tab
- `drawing_mode = "transform"`
- Controls: file uploader (png/jpg/jpeg/webp), scale slider (5–100% of canvas width)
- **"Add Overlay" button** → converts uploaded image to base64 data URL, appends FabricJS `image` object:
  ```json
  {
    "type": "image",
    "left": 50, "top": 50,
    "src": "data:image/png;base64,...",
    "scaleX": <scale_factor>, "scaleY": <scale_factor>,
    "selectable": true,
    "hasControls": true
  }
  ```
- Caption hint: "After adding, use Move tab to drag the overlay into position"

### ↔️ Move tab
- `drawing_mode = "transform"`
- No extra controls — just a caption: "Click any object to select it, then drag to move or use handles to resize/rotate"
- This is where all drag-and-drop positioning happens for text, shapes, and overlays

---

## Canvas Rendering (always present)

```python
canvas_result = st_canvas(
    fill_color="rgba(0,0,0,0)",
    stroke_width=brush_size,
    stroke_color=brush_color,
    background_image=img.convert("RGB"),
    initial_drawing=st.session_state["canvas_json"],
    height=canvas_h,   # min(h, 600)
    width=canvas_w,    # min(w, 800)
    drawing_mode=mode,
    update_streamlit=True,
    key=f"canvas_{active_tab}",
)

# Persist objects on every render
if canvas_result.json_data is not None and canvas_result.json_data.get("objects"):
    st.session_state["canvas_json"] = canvas_result.json_data
```

## Download
- `canvas_result.image_data` → numpy RGBA array → `Image.fromarray(arr, "RGBA")` → save as PNG
- This flattens background + all FabricJS objects + paint strokes into one image
- Download is at canvas display size (not original image size — acceptable trade-off)

---

## Reused Utilities
- `load_custom_css()`, `add_page_header()` — `admin/utils/ui_helpers.py`
- `show_success`, `show_error`, `show_warning`, `show_info` — `admin/components/notifications.py`
- `streamlit_drawable_canvas.st_canvas` — already in `requirements/admin.txt`

---

## Verification
1. Upload an image
2. **Paint tab**: draw freehand strokes with mouse — should paint like MS Paint
3. **Text tab**: type text, pick colors → click Add Text → text appears on canvas → switch to Move tab → drag text to desired position
4. **Shapes tab**: select rect → draw a rectangle on canvas → switch to Move tab → drag it around
5. **Overlay tab**: upload a PNG → click Add Overlay → image appears → switch to Move tab → drag it
6. **Download PNG** — result includes all edits flattened onto the original image
7. Switch tabs — all objects should persist (not disappear)
8. Rebuild: `docker compose build admin && docker compose up -d admin`
