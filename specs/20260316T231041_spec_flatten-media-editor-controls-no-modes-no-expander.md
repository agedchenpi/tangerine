# Plan: Flatten Media Editor Controls — No Modes, No Expanders

## Context

The current controls panel has a segmented control (Paint/Shapes/Move) that shows/hides sub-controls, plus expanders for Text and Overlay. The user wants all tools flat on one page — no hidden content, no modes to remember.

## File to Modify

`admin/pages/media_editor.py` — lines 155-249 (the `col_controls` block only)

## Current Layout (too nested)

```
[Segmented: Paint | Shapes | Move]   ← hides/shows sub-controls
  (conditional settings)
─────────
[▸ Add Text expander]                ← hidden by default
[▸ Add Overlay expander]             ← hidden by default
─────────
[Download] [Reset]
```

## New Layout (flat, everything visible)

```
── Tool ─────────────────────────
[Paint | Rect | Circle | Line | Move]   ← single selector, all drawing tools
Color: [■]   Size: [━━━━○━━]           ← settings for active tool (inline)

── Text ─────────────────────────
[Hello!______] Size [━━○━] Color [■] Bg [■]
[Add Text]

── Image Overlay ────────────────
[Upload file]  Scale [━━○━]
[Add Overlay]

─────────────────────────────────
[Download PNG]  [Reset Canvas]
```

## Key Changes

1. **Replace segmented control** — merge Paint + Shapes (rect/circle/line) + Move into a single `st.segmented_control` with 5 options: `paint`, `rect`, `circle`, `line`, `move`
2. **Remove expanders** — Text and Overlay sections are always visible, just separated by labels
3. **Inline tool settings** — Paint shows color + size; Rect/Circle/Line show color + line width; Move shows a short tip
4. **Update `_draw_mode_map`** — 5 entries mapping directly to canvas `drawing_mode` values (no intermediate "shapes" grouping)

## Implementation Detail

```python
with col_controls:
    # ── Tool ───────────────────────────────────────────────
    tool = st.segmented_control(
        "Tool",
        options=["paint", "rect", "circle", "line", "move"],
        format_func={
            "paint": "🎨 Paint", "rect": "▭ Rect", "circle": "⬭ Circle",
            "line": "╱ Line", "move": "↔️ Move",
        }.get,
        default="paint",
        key="drawing_tool",
    )

    if tool == "paint":
        st.color_picker("Brush color", "#FF0000", key="paint_color")
        st.slider("Brush size", 1, 50, 5, key="paint_size")
    elif tool in ("rect", "circle", "line"):
        st.color_picker("Shape color", "#FF0000", key="shape_color")
        st.slider("Line width", 1, 20, 3, key="shape_lw")
    elif tool == "move":
        st.caption("Click to select, drag to move, handles to resize/rotate")

    st.divider()

    # ── Text (always visible, no expander) ─────────────────
    st.markdown("**Add Text**")
    text_input = st.text_input(...)
    font_size = st.slider(...)
    tcol1, tcol2 = st.columns(2)
    with tcol1: text_color = st.color_picker(...)
    with tcol2: bg_color = st.color_picker(...)
    if st.button("Add Text", ...): ...

    st.divider()

    # ── Overlay (always visible, no expander) ──────────────
    st.markdown("**Add Image Overlay**")
    overlay_file = st.file_uploader(...)
    overlay_scale = st.slider(...)
    if st.button("Add Overlay", ...): ...

    st.divider()

    # ── Actions ────────────────────────────────────────────
    [Download PNG]  [Reset Canvas]
```

Also update `_draw_mode_map` above canvas render:
```python
_draw_mode_map = {
    "paint": ("freedraw", ss.get("paint_size", 5), ss.get("paint_color", "#FF0000")),
    "rect":  ("rect",     ss.get("shape_lw", 3),   ss.get("shape_color", "#FF0000")),
    "circle":("circle",   ss.get("shape_lw", 3),   ss.get("shape_color", "#FF0000")),
    "line":  ("line",     ss.get("shape_lw", 3),   ss.get("shape_color", "#FF0000")),
    "move":  ("transform", 3, "#000000"),
}
```

## What Stays Unchanged

- Canvas rendering, `_live_objects()`, `update_streamlit=True`, state preservation logic
- Add Text / Add Overlay button handlers (same logic, just not inside expanders)
- Download / Reset logic
- Video editor (untouched)

## Verification

1. `docker compose build admin && docker compose up -d admin`
2. All 5 tools selectable, settings appear inline
3. Text and Overlay sections always visible (no clicking to expand)
4. Paint strokes → Add Text → strokes preserved
5. Download PNG includes all edits
6. Reset clears canvas
