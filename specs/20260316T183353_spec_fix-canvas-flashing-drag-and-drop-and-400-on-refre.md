# Plan: Fix Canvas Flashing, Drag-and-Drop, and 400 on Refresh in Media Editor

## Context

After the previous fix (base64 background + theme sync reload removed), three new issues appeared:

1. **Canvas flashing** — when using paint + text box together, the canvas flashes constantly during painting
2. **Drag-and-drop broken** — objects cannot be dragged in Move mode
3. **400 on page refresh** — AxiosError 400 still occurs after a browser page refresh

**Root causes:**

- `key=f"canvas_{_mode}"` — canvas remounts (full FabricJS reinit) on every mode switch, causing `loadFromJSON` and loss of paint strokes
- `update_streamlit=True` + updating `canvas_json["objects"]` from `canvas_result.json_data` on every rerun — each Streamlit rerun rebuilds `initial_drawing` with new objects (including path data from paint strokes), the JSON string changes, the component detects the change and calls `loadFromJSON`, resetting the canvas mid-painting → flash. Same cause breaks drag: every mouse move triggers a rerun → `loadFromJSON` resets object positions → dragged object jumps back.
- 400 on refresh: the high-frequency WebSocket traffic from `update_streamlit=True` + rerun loop creates a timing window where a new upload PUT arrives before the Streamlit session reconnects after refresh.

---

## File to Modify

| File | Change |
|------|--------|
| `admin/pages/media_editor.py` | Fix `st_canvas` key, remove objects sync loop, fix Add Text/Overlay to merge current canvas state |

---

## Implementation

### 1. Stable canvas key (prevents remount on mode switch)

**Line 239:** Change `key=f"canvas_{_mode}"` → `key="canvas"`

FabricJS handles `drawing_mode` prop changes without remounting. Canvas state (paint strokes, objects) is preserved when switching modes.

### 2. Remove `st.rerun()` on mode change (line 123)

```python
# Before:
if new_mode != st.session_state["canvas_mode"]:
    st.session_state["canvas_mode"] = new_mode
    st.rerun()

# After:
if new_mode != st.session_state["canvas_mode"]:
    st.session_state["canvas_mode"] = new_mode
    # No st.rerun() needed — stable key means FabricJS switches mode via prop change
```

Without `key=f"canvas_{_mode}"`, a rerun would just rebuild the same canvas. The `drawing_mode` prop update on the next natural rerun (from any widget interaction) is sufficient. The radio button itself already triggers a Streamlit rerun — removing the explicit `st.rerun()` avoids a double rerun.

### 3. Stop auto-updating `canvas_json["objects"]` on every rerun (eliminates flash + drag breakage)

**Lines 241-242:** Remove the automatic save:
```python
# REMOVE this block:
if canvas_result.json_data is not None:
    st.session_state["canvas_json"]["objects"] = canvas_result.json_data.get("objects", [])
```

**Why this fixes the flash:** `initial_drawing` is built from `canvas_json["objects"]`. When `canvas_result.json_data` is written back on every rerun, the JSON string changes (new path objects from paint strokes are added), the React component detects the change, and calls `loadFromJSON`, resetting the canvas. With this line removed, `canvas_json["objects"]` only changes on explicit user actions (Add Text, Add Overlay, Reset), so `initial_drawing` stays stable between reruns.

**Why this fixes drag-and-drop:** With a stable `initial_drawing`, Streamlit reruns triggered by `update_streamlit=True` mouse events no longer cause `loadFromJSON` to fire. FabricJS maintains its own state; dragged objects stay where the user drops them.

### 4. Fix Add Text and Add Overlay to merge current canvas state

When the user clicks "Add Text" or "Add Overlay", we must first capture the current FabricJS objects (including any paint strokes) from `canvas_result.json_data`, then append the new object, then save. This ensures `loadFromJSON` on the following rerun includes existing strokes alongside the new element.

**Add Text (lines 140-153):**
```python
if st.button("Add Text", key="btn_text", use_container_width=True):
    # Capture current canvas state (paint strokes + existing objects)
    current_objects = (
        canvas_result.json_data.get("objects", [])
        if canvas_result.json_data is not None
        else st.session_state["canvas_json"].get("objects", [])
    )
    current_objects.append({
        "type": "i-text",
        "left": 50, "top": 50,
        "text": text_input,
        "fontSize": font_size,
        "fill": text_color,
        "backgroundColor": bg_color,
        "fontFamily": "Arial",
        "selectable": True,
        "hasControls": True,
    })
    st.session_state["canvas_json"]["objects"] = current_objects
    show_success("Text added — switch to ↔️ Move to drag it into position.")
    st.rerun()
```

**Add Overlay (lines 170-187):** Same pattern — read `canvas_result.json_data` first before appending overlay object.

### 5. Compress background to JPEG (reduces WebSocket message size)

**Lines 93-96:** Change PNG encoding to JPEG quality 70:
```python
buf = io.BytesIO()
img.resize((canvas_w, canvas_h), Image.LANCZOS).convert("RGB").save(buf, format="JPEG", quality=70)
b64 = base64.b64encode(buf.getvalue()).decode()
st.session_state["_bg_data_url"] = f"data:image/jpeg;base64,{b64}"
```

Reduces background from ~2 MB (PNG) to ~200 KB (JPEG Q70). Smaller `initial_drawing` means lower WebSocket payload on every rerun, reducing the 400-on-refresh timing window.

---

## What stays unchanged

- `update_streamlit=True` — needed for `canvas_result.image_data` (RGBA render) used by the download button
- `background_image=None` — base64 approach from previous fix remains
- `initial_drawing` structure with `backgroundImage` — remains

---

## Session State Keys (unchanged)

| Key | Purpose |
|-----|---------|
| `_editor_file` | Triggers reset when file changes |
| `_editor_img` | Cached PIL Image (size info) |
| `_bg_data_url` | Base64 JPEG data URL of resized photo |
| `canvas_json` | FabricJS objects `{"version":..., "objects":[...]}` — only updated on Add Text, Add Overlay, Reset |
| `canvas_mode` | Active mode: paint/text/shapes/overlay/move |

---

## Verification

1. Rebuild: `docker compose build admin && docker compose up -d admin`
2. Upload `rick_and_morty.png` — canvas loads, no 400 in browser console
3. Paint freely — no flashing during strokes
4. Switch to Text → Add Text — text appears, existing strokes preserved
5. Switch to Move — drag the text object — it stays where dropped, no jumping
6. Switch back to Paint — strokes resume, text still visible
7. Download PNG — result includes background + all strokes + text
8. Hard refresh browser → re-upload → confirm no 400
