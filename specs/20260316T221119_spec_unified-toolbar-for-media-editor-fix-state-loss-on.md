# Plan: Unified Toolbar for Media Editor (Fix State Loss on Mode Switch)

## Context

When switching between modes (paint → text → shapes → overlay → move), canvas edits can be lost. The root cause is that `update_streamlit=False` means `canvas_result.json_data` is always `None`. When the user clicks "Add Text" or "Add Overlay", the code falls back to the stale `canvas_json` from session state — discarding any paint strokes, shapes, or object movements made since the last explicit save.

Beyond the state loss bug, the 5-mode radio design creates friction: users must remember to switch modes, and captions like "switch to Move mode to drag it into position" reveal that the UX is fighting the underlying tool.

**Goal**: Replace the mode-based UI with a unified toolbar where all tools are visible and accessible, and canvas state is always preserved.

---

## Root Cause Analysis

**State loss flow** (current code, lines 190-193 and 232-236):
```python
current_objects = (
    canvas_result.json_data.get("objects", [])        # ← None (update_streamlit=False)
    if canvas_result.json_data is not None
    else st.session_state["canvas_json"].get("objects", [])  # ← stale fallback
)
```

1. User paints strokes → strokes live in FabricJS only (not in `canvas_json`)
2. User clicks "Add Text" → `canvas_result.json_data` is `None`
3. Falls back to `canvas_json` (no strokes) → appends text → `st.rerun()`
4. `initial_drawing` rebuilt from updated `canvas_json` (text but no strokes)
5. Canvas loads new `initial_drawing` → **strokes lost**

**Fix**: Set `update_streamlit=True` so `canvas_result.json_data` always reflects the actual canvas state. The previous reason for `False` (400 errors) is resolved by the canvas fork upgrade.

---

## Files to Modify

| File | Change |
|------|--------|
| `admin/pages/media_editor.py` | Rewrite controls section (lines 102-275) |

No other files need changes. No database changes.

---

## Implementation

### 1. Enable `update_streamlit=True` (line 152)

```python
update_streamlit=True,   # Canvas fork 0.9.8 fixes the 400 errors that broke this
```

This ensures `canvas_result.json_data` is always populated with current canvas objects.

### 2. Auto-sync canvas state (after canvas render, before controls)

After the `st_canvas()` call, sync current canvas state back to session state so it's never stale:

```python
# Sync FabricJS state → session state (prevents stale fallback)
if canvas_result.json_data is not None:
    st.session_state["canvas_json"]["objects"] = canvas_result.json_data.get("objects", [])
```

This runs on every rerun but doesn't cause a loop because `initial_drawing` is built BEFORE this line (from the previous `canvas_json`), so it doesn't change during the same rerun.

### 3. Replace mode-based UI with unified toolbar

**Current layout** (5 radio modes, only one panel visible at a time):
```
[Radio: Paint | Text | Shapes | Overlay | Move]
─────────────
(mode-specific controls — only one visible)
```

**New layout** (all tools accessible, compact):
```
── Drawing Tool ──────────────
[Segmented: 🎨 Paint | 🔷 Shapes | ↔️ Move]
(active tool settings inline)

── Add Elements ──────────────
[Text expander]   input + size + color + [Add]
[Overlay expander] file + scale + [Add]

──────────────────────────────
[Download PNG]  [Reset Canvas]
```

**Key design decisions:**
- **Drawing tool selector** (paint/shapes/move) — this is the only thing that changes `drawing_mode` on the canvas. Use `st.segmented_control` (available in Streamlit 1.49.1)
- **Text & Overlay as expanders** — these are "add" actions, not drawing modes. They append objects and work regardless of the active drawing tool. Always visible, no mode switch needed
- **Remove "switch to Move mode" captions** — Move is just another tool option, not a separate workflow
- **Tool-specific settings shown inline** below the selector (paint: color + size; shapes: type + color + width; move: tip text)

### 4. Detailed control structure

```python
with col_controls:
    # ── Drawing Tool ──────────────────────────────────
    tool = st.segmented_control(
        "Drawing Tool",
        options=["paint", "shapes", "move"],
        format_func={"paint": "🎨 Paint", "shapes": "🔷 Shapes", "move": "↔️ Move"}.get,
        default="paint",
        key="drawing_tool",
    )

    # Tool-specific settings (inline, not hidden)
    if tool == "paint":
        st.color_picker("Brush color", "#FF0000", key="paint_color")
        st.slider("Brush size", 1, 50, 5, key="paint_size")
    elif tool == "shapes":
        st.selectbox("Shape", ["rect", "circle", "line"], key="shape_type", ...)
        st.color_picker("Color", "#FF0000", key="shape_color")
        st.slider("Line width", 1, 20, 3, key="shape_lw")
    elif tool == "move":
        st.caption("Click any object to select, drag to move, use handles to resize/rotate")

    st.divider()

    # ── Add Elements ──────────────────────────────────
    with st.expander("📝 Add Text"):
        text_input = st.text_input("Text", value="Hello!", key="txt_input")
        font_size = st.slider("Font size", 10, 120, 40, key="txt_size")
        text_color = st.color_picker("Text color", "#FFFFFF", key="txt_color")
        bg_color = st.color_picker("Background", "#000000", key="txt_bg")
        if st.button("Add Text", key="btn_text", use_container_width=True):
            # canvas_result.json_data is now always available (update_streamlit=True)
            current_objects = st.session_state["canvas_json"].get("objects", [])
            current_objects.append({...text object...})
            st.session_state["canvas_json"]["objects"] = current_objects
            st.rerun()

    with st.expander("🖼️ Add Overlay"):
        overlay_file = st.file_uploader(...)
        overlay_scale = st.slider(...)
        if st.button("Add Overlay", ...):
            # Same pattern — reads from already-synced canvas_json
            ...

    st.divider()

    # ── Download / Reset ──────────────────────────────
    [Download PNG button]
    [Reset Canvas button]
```

### 5. Update `_draw_mode_map` to match new tool names

Replace the 5-mode map with the 3-tool map:
```python
_draw_mode_map = {
    "paint":  ("freedraw", paint_size, paint_color),
    "shapes": (shape_type, shape_lw, shape_color),
    "move":   ("transform", 3, "#000000"),
}
```

### 6. Remove stale session state keys

- Remove `canvas_mode` — replaced by `drawing_tool`
- Keep all other session state keys (paint_color, paint_size, shape_*, txt_*, ov_*)

---

## What stays unchanged

- `key="canvas"` — stable canvas key (no remount)
- `background_image=None` + base64 `backgroundImage` in `initial_drawing` — avoids MediaFileHandler
- JPEG Q70 background compression
- Download / Reset button logic
- Video editor (untouched)

---

## Verification

1. `docker compose build admin && docker compose up -d admin`
2. Upload a .png → canvas loads, no errors
3. **Paint strokes → Add Text → verify strokes preserved** (the main bug fix)
4. **Paint strokes → Add Overlay → verify strokes preserved**
5. Draw shapes → switch to Paint → switch to Move → all objects visible
6. Move objects around → Add Text → verify moved positions preserved
7. Download PNG → includes background + all edits at correct positions
8. Reset Canvas → clean slate
9. Hard refresh → re-upload → no errors
10. Verify no flash/flicker during normal drawing with `update_streamlit=True`
