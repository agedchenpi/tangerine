"""Media Editor — image and video editing tools."""

import base64
import io
import logging
import tempfile

import streamlit as st
from PIL import Image, ImageDraw

# moviepy 1.0.3 uses Image.ANTIALIAS, removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from utils.ui_helpers import load_custom_css, add_page_header
from components.notifications import show_success, show_error, show_warning, show_info

logger = logging.getLogger("media_editor")

load_custom_css()
add_page_header("Media Editor", icon="🎨")

# ── File upload ───────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload an image or video",
    type=["png", "jpg", "jpeg", "gif", "bmp", "webp", "mp4", "mov", "avi", "mkv", "webm"],
    help="Images: PNG, JPG, GIF, BMP, WEBP  |  Videos: MP4, MOV, AVI, MKV, WEBM",
)

if uploaded is None:
    show_info("Upload an image or video file to get started.")
    st.stop()

mime = uploaded.type or ""

# Cache file bytes in session state — UploadedFile can only be reliably read once per rerun
if st.session_state.get("_uploaded_name") != uploaded.name:
    st.session_state["_uploaded_name"] = uploaded.name
    st.session_state["_uploaded_bytes"] = uploaded.read()

file_bytes: bytes = st.session_state["_uploaded_bytes"]

# ── Route by type ─────────────────────────────────────────────────────────────
if mime.startswith("image/"):
    _render_image = True
elif mime.startswith("video/"):
    _render_image = False
else:
    show_warning(f"Unsupported file type: {mime}. Please upload an image or video.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE EDITOR
# ══════════════════════════════════════════════════════════════════════════════
def _render_image_editor(img_bytes: bytes) -> None:
    try:
        from streamlit_drawable_canvas import st_canvas
    except ImportError:
        show_warning("streamlit-drawable-canvas is not installed. Rebuild the Docker image to enable this feature.")
        return

    try:
        # Reset canvas state when a new file is loaded
        if st.session_state.get("_editor_file") != uploaded.name:
            st.session_state["_editor_file"] = uploaded.name
            st.session_state["canvas_json"] = {"version": "5.3.0", "objects": []}
            st.session_state["_editor_img"] = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            # Clear cached base64 so it's re-encoded for the new image
            st.session_state.pop("_bg_data_url", None)

        if "canvas_json" not in st.session_state:
            st.session_state["canvas_json"] = {"version": "5.3.0", "objects": []}
        if "_editor_img" not in st.session_state:
            st.session_state["_editor_img"] = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        logger.exception("media_editor error loading image: %s", e)
        show_error(f"Error loading image: {e}")
        return

    img: Image.Image = st.session_state["_editor_img"]
    w, h = img.size

    # Aspect-ratio-preserving canvas dimensions
    ratio = w / h
    if w > 800 or h > 600:
        if w / 800 >= h / 600:
            canvas_w, canvas_h = 800, int(800 / ratio)
        else:
            canvas_w, canvas_h = int(600 * ratio), 600
    else:
        canvas_w, canvas_h = w, h

    # Encode background image as base64 data URL once per file (avoids MediaFileHandler 400s)
    if "_bg_data_url" not in st.session_state:
        try:
            buf = io.BytesIO()
            img.resize((canvas_w, canvas_h), Image.LANCZOS).convert("RGB").save(buf, format="JPEG", quality=70)
            b64 = base64.b64encode(buf.getvalue()).decode()
            st.session_state["_bg_data_url"] = f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            logger.exception("media_editor error encoding background: %s", e)
            show_error(f"Error encoding image: {e}")
            return

    col_canvas, col_controls = st.columns([3, 2], gap="large")

    # ── Resolve canvas drawing_mode and stroke from session state ──────────────
    ss = st.session_state
    _tool = ss.get("drawing_tool", "move")
    _draw_mode_map = {
        "move":   ("transform", 3, "#000000"),
        "paint":  ("freedraw",
                   ss.get("paint_size", 5),
                   ss.get("paint_color", "#FF0000")),
        "rect":   ("rect",
                   ss.get("shape_lw", 3),
                   ss.get("shape_color", "#FF0000")),
        "circle": ("circle",
                   ss.get("shape_lw", 3),
                   ss.get("shape_color", "#FF0000")),
        "line":   ("line",
                   ss.get("shape_lw", 3),
                   ss.get("shape_color", "#FF0000")),
        "text":   ("transform", 3, "#000000"),
        "image":  ("transform", 3, "#000000"),
    }
    _draw_mode, _stroke_w, _stroke_c = _draw_mode_map.get(_tool, _draw_mode_map["move"])

    # ── Canvas — rendered first so canvas_result is available to controls ──────
    # Build FabricJS JSON with backgroundImage (base64 data URL) to avoid
    # Streamlit MediaFileHandler 400 errors on rerun/mode-switch
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

    with col_canvas:
        st.caption(f"{w} × {h} px  |  Canvas: {canvas_w} × {canvas_h} px")
        canvas_result = st_canvas(
            fill_color="rgba(0,0,0,0)",
            stroke_width=_stroke_w,
            stroke_color=_stroke_c,
            background_image=None,
            initial_drawing=initial_drawing,
            height=canvas_h,
            width=canvas_w,
            drawing_mode=_draw_mode,
            display_toolbar=True,
            update_streamlit=True,
            key="canvas",
        )

    # Helper: get live canvas objects (from FabricJS if available, else session state)
    def _live_objects() -> list:
        if canvas_result.json_data is not None:
            return list(canvas_result.json_data.get("objects", []))
        return list(st.session_state["canvas_json"].get("objects", []))

    # ── Track canvas history for undo/redo ───────────────────────────────────
    if "_canvas_history" not in ss:
        ss["_canvas_history"] = [[]]
        ss["_history_idx"] = 0

    if canvas_result.json_data is not None:
        current_objs = canvas_result.json_data.get("objects", [])
        history = ss["_canvas_history"]
        idx = ss["_history_idx"]
        last = history[idx] if history else []
        if len(current_objs) != len(last) or current_objs != last:
            ss["_canvas_history"] = history[: idx + 1] + [list(current_objs)]
            ss["_history_idx"] = idx + 1

    # ── Controls — per-tool settings ──────────────────────────────────────────
    with col_controls:
        # ── Tool selector (7 tools, Move default) ─────────────────────────
        tool = st.segmented_control(
            "Tool",
            options=["move", "paint", "rect", "circle", "line", "text", "image"],
            format_func={
                "move": "↔️ Move", "paint": "🎨 Paint", "rect": "▭ Rect",
                "circle": "⬭ Circle", "line": "╱ Line",
                "text": "📝 Text", "image": "🖼️ Image",
            }.get,
            default="move",
            key="drawing_tool",
        )

        # ── Per-tool inline settings ──────────────────────────────────────
        if tool == "move":
            st.caption("Click to select, drag to move, handles to resize/rotate")
        elif tool == "paint":
            st.color_picker("Brush color", "#FF0000", key="paint_color")
            st.slider("Brush size", 1, 50, 5, key="paint_size")
        elif tool in ("rect", "circle", "line"):
            st.color_picker("Shape color", "#FF0000", key="shape_color")
            st.slider("Line width", 1, 20, 3, key="shape_lw")
        elif tool == "text":
            text_input = st.text_input("Text", value="Hello!", key="txt_input")
            font_size = st.slider("Font size", 10, 120, 40, key="txt_size")
            tcol1, tcol2 = st.columns(2)
            with tcol1:
                text_color = st.color_picker("Text color", "#FFFFFF", key="txt_color")
            with tcol2:
                bg_color = st.color_picker("Background", "#000000", key="txt_bg")
            if st.button("Add Text", key="btn_text", use_container_width=True):
                current_objects = _live_objects()
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
                ss["canvas_json"]["objects"] = current_objects
                show_success("Text added!")
                ss["drawing_tool"] = "move"
                st.rerun()
        elif tool == "image":
            overlay_file = st.file_uploader(
                "Overlay image", type=["png", "jpg", "jpeg", "webp"], key="overlay_file",
            )
            overlay_scale = st.slider("Scale (% of canvas width)", 5, 100, 30, key="ov_scale")
            if st.button("Add Overlay", key="btn_overlay", use_container_width=True, disabled=overlay_file is None):
                try:
                    ov_img = Image.open(overlay_file).convert("RGBA")
                    ov_bytes = io.BytesIO()
                    ov_img.save(ov_bytes, format="PNG")
                    b64 = base64.b64encode(ov_bytes.getvalue()).decode()
                    scale_factor = (canvas_w * overlay_scale / 100) / ov_img.width
                    current_objects = _live_objects()
                    current_objects.append({
                        "type": "image",
                        "left": 50, "top": 50,
                        "src": f"data:image/png;base64,{b64}",
                        "scaleX": scale_factor, "scaleY": scale_factor,
                        "selectable": True, "hasControls": True,
                    })
                    ss["canvas_json"]["objects"] = current_objects
                    show_success("Overlay added!")
                    ss["drawing_tool"] = "move"
                    st.rerun()
                except Exception as e:
                    show_error(str(e))

        st.divider()

        # ── Undo / Redo ───────────────────────────────────────────────────
        ucol1, ucol2 = st.columns(2)
        with ucol1:
            if st.button("⟲ Undo", use_container_width=True, key="btn_undo"):
                idx = ss.get("_history_idx", 0)
                if idx > 0:
                    ss["_history_idx"] = idx - 1
                    ss["canvas_json"]["objects"] = list(ss["_canvas_history"][idx - 1])
                    st.rerun()
        with ucol2:
            if st.button("⟳ Redo", use_container_width=True, key="btn_redo"):
                idx = ss.get("_history_idx", 0)
                history = ss.get("_canvas_history", [])
                if idx < len(history) - 1:
                    ss["_history_idx"] = idx + 1
                    ss["canvas_json"]["objects"] = list(history[idx + 1])
                    st.rerun()

        # ── Download / Reset ──────────────────────────────────────────────
        if canvas_result.image_data is not None:
            import numpy as np
            flat_img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
            buf = io.BytesIO()
            flat_img.save(buf, format="PNG")
        else:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
        st.download_button(
            "⬇️ Download PNG",
            data=buf.getvalue(),
            file_name="edited_image.png",
            mime="image/png",
            use_container_width=True,
        )
        if st.button("↩️ Reset Canvas", use_container_width=True):
            ss["canvas_json"] = {"version": "5.3.0", "objects": []}
            ss["_canvas_history"] = [[]]
            ss["_history_idx"] = 0
            st.rerun()



# ══════════════════════════════════════════════════════════════════════════════
# VIDEO EDITOR — Interactive Timeline with Canvas Preview
# ══════════════════════════════════════════════════════════════════════════════

from utils.ui_helpers import get_theme_colors
from components.timeline_editor import timeline_editor


def _tl_duration(segments: list) -> float:
    """Total composed timeline duration from all segments."""
    return sum(seg["src_end"] - seg["src_start"] for seg in segments)


def _tl_get_next_id(ss) -> int:
    """Increment and return the next monotonic clip ID."""
    nid = ss.get("_tl_next_id", 1)
    ss["_tl_next_id"] = nid + 1
    return nid


def _tl_split_segment(segments: list, seg_id: int, split_time: float, ss) -> list:
    """Split a segment at a timeline-relative time into two new segments."""
    offset = 0.0
    for i, seg in enumerate(segments):
        seg_dur = seg["src_end"] - seg["src_start"]
        if seg["id"] == seg_id:
            local_t = split_time - offset
            if local_t <= 0.01 or local_t >= seg_dur - 0.01:
                return segments  # too close to edge
            src_split = seg["src_start"] + local_t
            new_a = {
                "id": _tl_get_next_id(ss), "source_id": seg.get("source_id", "source_0"),
                "src_start": seg["src_start"], "src_end": src_split,
            }
            new_b = {
                "id": _tl_get_next_id(ss), "source_id": seg.get("source_id", "source_0"),
                "src_start": src_split, "src_end": seg["src_end"],
            }
            return segments[:i] + [new_a, new_b] + segments[i + 1:]
        offset += seg_dur
    return segments


def _tl_delete_clip(ss, track: str, clip_id: int) -> None:
    """Delete a clip from the timeline; prevent deleting the last segment."""
    logger.info("Delete clip: track=%s id=%d", track, clip_id)
    if track == "segment":
        segs = ss["_tl_segments"]
        if len(segs) <= 1:
            return
        ss["_tl_segments"] = [s for s in segs if s["id"] != clip_id]
        new_dur = _tl_duration(ss["_tl_segments"])
        ss["_tl_texts"] = [t for t in ss["_tl_texts"] if t["start"] < new_dur]
        for t in ss["_tl_texts"]:
            t["end"] = min(t["end"], new_dur)
        ss["_tl_images"] = [im for im in ss["_tl_images"] if im["start"] < new_dur]
        for im in ss["_tl_images"]:
            im["end"] = min(im["end"], new_dur)
        ss["_tl_video_overlays"] = [v for v in ss["_tl_video_overlays"] if v["start"] < new_dur]
        for v in ss["_tl_video_overlays"]:
            v["end"] = min(v["end"], new_dur)
    elif track == "text":
        ss["_tl_texts"] = [t for t in ss["_tl_texts"] if t["id"] != clip_id]
    elif track == "image":
        ss["_tl_images"] = [im for im in ss["_tl_images"] if im["id"] != clip_id]
    elif track == "video_overlay":
        ss["_tl_video_overlays"] = [v for v in ss["_tl_video_overlays"] if v["id"] != clip_id]

    ss["_video_rendered_bytes"] = None
    sel = ss.get("_tl_selected")
    if sel and sel.get("track") == track and sel.get("id") == clip_id:
        ss["_tl_selected"] = None


def _extract_frame_at_time(sources: dict, segments: list, playhead: float):
    """Extract a video frame at the given playhead time as a PIL Image."""
    import moviepy.editor as mpe

    ss = st.session_state
    offset = 0.0
    for seg in segments:
        seg_dur = seg["src_end"] - seg["src_start"]
        if offset + seg_dur > playhead or seg is segments[-1]:
            src_id = seg.get("source_id", "source_0")
            src = sources.get(src_id)
            if not src:
                return None
            src_t = seg["src_start"] + (playhead - offset)
            src_t = max(seg["src_start"], min(src_t, seg["src_end"] - 0.01))

            cache_key = (round(playhead, 1), src_id, round(src_t, 1))
            if ss.get("_frame_cache_key") == cache_key and ss.get("_frame_cache_img") is not None:
                return ss["_frame_cache_img"]

            try:
                clip = mpe.VideoFileClip(src["path"])
                frame = clip.get_frame(src_t)
                clip.close()
                pil_img = Image.fromarray(frame)

                # Composite V2 video overlays
                for vov in ss.get("_tl_video_overlays", []):
                    if vov["start"] <= playhead <= vov["end"]:
                        vov_src_t = vov["src_start"] + (playhead - vov["start"])
                        try:
                            vc = mpe.VideoFileClip(sources[vov["source_id"]]["path"])
                            vf = vc.get_frame(vov_src_t)
                            vc.close()
                            ov_img = Image.fromarray(vf)
                            if vov.get("scale", 1.0) != 1.0:
                                ov_img = ov_img.resize(
                                    (int(ov_img.width * vov["scale"]), int(ov_img.height * vov["scale"])),
                                    Image.LANCZOS,
                                )
                            pil_img.paste(ov_img, (vov["x"], vov["y"]))
                        except Exception as e:
                            logger.error("V2 frame extraction failed: %s", e)

                ss["_frame_cache_key"] = cache_key
                ss["_frame_cache_img"] = pil_img
                return pil_img
            except Exception as e:
                logger.error("Frame extraction failed at t=%.1f src=%s: %s", src_t, src_id, e)
                return None
        offset += seg_dur
    return None


def _sync_canvas_to_overlays(canvas_result, ss, canvas_w, canvas_h, vw, vh):
    """Read canvas object positions and sync x/y back to overlay data model."""
    if canvas_result is None or canvas_result.json_data is None:
        return
    objects = canvas_result.json_data.get("objects", [])

    active_texts = sorted(
        [t for t in ss["_tl_texts"] if t["start"] <= ss["_tl_playhead"] <= t["end"]],
        key=lambda t: t["id"],
    )
    active_images = sorted(
        [im for im in ss["_tl_images"] if im["start"] <= ss["_tl_playhead"] <= im["end"]],
        key=lambda im: im["id"],
    )

    idx = 0
    changed = False
    for txt in active_texts:
        if idx < len(objects):
            obj = objects[idx]
            new_x = int(obj.get("left", 0) * vw / canvas_w)
            new_y = int(obj.get("top", 0) * vh / canvas_h)
            if new_x != txt["x"] or new_y != txt["y"]:
                txt["x"] = new_x
                txt["y"] = new_y
                changed = True
            idx += 1

    for img in active_images:
        if idx < len(objects):
            obj = objects[idx]
            new_x = int(obj.get("left", 0) * vw / canvas_w)
            new_y = int(obj.get("top", 0) * vh / canvas_h)
            if new_x != img["x"] or new_y != img["y"]:
                img["x"] = new_x
                img["y"] = new_y
                changed = True
            idx += 1

    if changed:
        ss["_video_rendered_bytes"] = None


def _add_video_source(ss, file_bytes: bytes, filename: str) -> str:
    """Write video to tempfile, read metadata, add source + segment to timeline."""
    import moviepy.editor as mpe

    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("Video file is empty.")

    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(file_bytes)
        path = f.name
    logger.info("Writing video source to temp: %s (%d bytes)", filename, len(file_bytes))

    clip = mpe.VideoFileClip(path)
    if clip.duration is None or clip.duration <= 0:
        clip.close()
        raise ValueError("Video has no valid duration.")
    duration = clip.duration
    size = tuple(clip.size)
    clip.close()
    logger.info("Video source metadata: %s duration=%.1f size=%s", filename, duration, size)

    src_id = f"source_{ss['_video_next_source_id']}"
    ss["_video_next_source_id"] += 1
    ss["_video_sources"][src_id] = {
        "path": path, "duration": duration, "size": size, "name": filename,
    }

    tl_dur = _tl_duration(ss["_tl_segments"])
    ss["_tl_video_overlays"].append({
        "id": _tl_get_next_id(ss), "source_id": src_id,
        "start": 0.0, "end": min(duration, tl_dur),
        "src_start": 0.0, "src_end": duration,
        "x": 0, "y": 0, "scale": 1.0,
    })
    ss["_video_rendered_bytes"] = None
    return src_id


def _render_clip_properties(ss, track, clip, total_dur, vw, vh) -> None:
    """Render context-dependent properties panel for the selected clip."""
    if track == "segment":
        st.markdown("**Segment Properties**")
        src_id = clip.get("source_id", "source_0")
        src = ss["_video_sources"].get(src_id, {})
        st.caption(f"Source: {src.get('name', 'unknown')}")
        new_start = st.number_input(
            "Source start (s)", min_value=0.0, value=clip["src_start"],
            step=0.1, key="prop_seg_start",
        )
        max_end = src.get("duration", clip["src_end"] + 60.0)
        new_end = st.number_input(
            "Source end (s)", min_value=0.1, value=clip["src_end"],
            max_value=max_end, step=0.1, key="prop_seg_end",
        )
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("Update", key="btn_seg_update", use_container_width=True):
                if new_start < new_end:
                    clip["src_start"] = new_start
                    clip["src_end"] = new_end
                    ss["_video_rendered_bytes"] = None
                    st.rerun()
                else:
                    show_warning("Start must be before end.")
        with pc2:
            disabled = len(ss["_tl_segments"]) <= 1
            if st.button("Delete", key="btn_seg_del", use_container_width=True, disabled=disabled):
                _tl_delete_clip(ss, "segment", clip["id"])
                st.rerun()

    elif track == "text":
        st.markdown("**Text Overlay Properties**")
        new_text = st.text_input("Text", value=clip["text"], key="prop_txt_text")
        new_fs = st.slider("Font size", 12, 120, clip["fontsize"], key="prop_txt_fs")
        tc1, tc2 = st.columns(2)
        with tc1:
            new_color = st.color_picker("Color", clip["color"], key="prop_txt_color")
        with tc2:
            new_x = st.number_input("X", 0, vw, clip["x"], key="prop_txt_x")
        new_y = st.number_input("Y", 0, vh, clip["y"], key="prop_txt_y")
        new_start = st.number_input(
            "Start (s)", 0.0, total_dur - 0.1, clip["start"], 0.1, key="prop_txt_start",
        )
        new_end = st.number_input(
            "End (s)", 0.1, total_dur, clip["end"], 0.1, key="prop_txt_end",
        )
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("Update", key="btn_txt_update", use_container_width=True):
                clip.update(text=new_text, fontsize=new_fs, color=new_color,
                            x=new_x, y=new_y, start=new_start, end=new_end)
                ss["_video_rendered_bytes"] = None
                st.rerun()
        with pc2:
            if st.button("Delete", key="btn_txt_del", use_container_width=True):
                _tl_delete_clip(ss, "text", clip["id"])
                st.rerun()

    elif track == "video_overlay":
        st.markdown("**Video Overlay (V2) Properties**")
        src_id = clip.get("source_id", "source_0")
        src = ss["_video_sources"].get(src_id, {})
        st.caption(f"Source: {src.get('name', 'unknown')}")
        new_start = st.number_input(
            "Start (s)", 0.0, total_dur - 0.1, clip["start"], 0.1, key="prop_vov_start",
        )
        new_end = st.number_input(
            "End (s)", 0.1, total_dur, clip["end"], 0.1, key="prop_vov_end",
        )
        vc1, vc2 = st.columns(2)
        with vc1:
            new_x = st.number_input("X", 0, vw, clip["x"], key="prop_vov_x")
        with vc2:
            new_y = st.number_input("Y", 0, vh, clip["y"], key="prop_vov_y")
        new_scale = st.slider("Scale", 0.1, 3.0, clip.get("scale", 1.0), 0.1, key="prop_vov_scale")
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("Update", key="btn_vov_update", use_container_width=True):
                clip.update(start=new_start, end=new_end, x=new_x, y=new_y, scale=new_scale)
                ss["_video_rendered_bytes"] = None
                st.rerun()
        with pc2:
            if st.button("Delete", key="btn_vov_del", use_container_width=True):
                _tl_delete_clip(ss, "video_overlay", clip["id"])
                st.rerun()

    elif track == "image":
        st.markdown("**Image Overlay Properties**")
        new_start = st.number_input(
            "Start (s)", 0.0, total_dur - 0.1, clip["start"], 0.1, key="prop_img_start",
        )
        new_end = st.number_input(
            "End (s)", 0.1, total_dur, clip["end"], 0.1, key="prop_img_end",
        )
        ic1, ic2 = st.columns(2)
        with ic1:
            new_x = st.slider("X pos", 0, vw, clip["x"], key="prop_img_x")
        with ic2:
            new_y = st.slider("Y pos", 0, vh, clip["y"], key="prop_img_y")
        new_scale = st.slider("Scale", 0.1, 3.0, clip.get("scale", 1.0), 0.1, key="prop_img_scale")
        pc1, pc2 = st.columns(2)
        with pc1:
            if st.button("Update", key="btn_img_update", use_container_width=True):
                clip.update(start=new_start, end=new_end, x=new_x, y=new_y, scale=new_scale)
                ss["_video_rendered_bytes"] = None
                st.rerun()
        with pc2:
            if st.button("Delete", key="btn_img_del", use_container_width=True):
                _tl_delete_clip(ss, "image", clip["id"])
                st.rerun()


def _render_video_pipeline(sources: dict, segments: list, texts: list, images: list, video_overlays: list | None = None):
    """Render the timeline to MP4 bytes: segments -> concat -> overlays -> composite."""
    import moviepy.editor as mpe

    video_overlays = video_overlays or []
    logger.info("Starting full render: %d segments, %d texts, %d images, %d video_overlays", len(segments), len(texts), len(images), len(video_overlays))
    try:
        clips_cache = {}
        subclips = []
        for seg in segments:
            src_id = seg.get("source_id", "source_0")
            if src_id not in clips_cache:
                clips_cache[src_id] = mpe.VideoFileClip(sources[src_id]["path"])
            subclips.append(clips_cache[src_id].subclip(seg["src_start"], seg["src_end"]))

        base = mpe.concatenate_videoclips(subclips, method="compose")

        overlays = []
        for txt in texts:
            pos = (txt["x"], txt["y"])
            tc = (
                mpe.TextClip(
                    txt["text"],
                    fontsize=txt["fontsize"],
                    color=txt["color"],
                    font="Liberation-Sans",
                )
                .set_position(pos)
                .set_start(txt["start"])
                .set_end(min(txt["end"], base.duration))
            )
            overlays.append(tc)
        for img_ov in images:
            ic = (
                mpe.ImageClip(img_ov["img_path"])
                .resize(img_ov.get("scale", 1.0))
                .set_position((img_ov["x"], img_ov["y"]))
                .set_start(img_ov["start"])
                .set_end(min(img_ov["end"], base.duration))
            )
            overlays.append(ic)
        for vov in video_overlays:
            src_clip = mpe.VideoFileClip(sources[vov["source_id"]]["path"])
            sub = (
                src_clip.subclip(vov["src_start"], vov["src_end"])
                .resize(vov.get("scale", 1.0))
                .set_position((vov["x"], vov["y"]))
                .set_start(vov["start"])
                .set_end(min(vov["end"], base.duration))
            )
            overlays.append(sub)

        if overlays:
            final = mpe.CompositeVideoClip([base] + overlays)
        else:
            final = base

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_f:
            out_path = out_f.name
        final.write_videofile(out_path, logger=None)
        for c in clips_cache.values():
            c.close()
        with open(out_path, "rb") as f:
            result = f.read()
        logger.info("Render complete: %d bytes", len(result))
        return result
    except Exception as e:
        logger.error("Render failed: %s", e, exc_info=True)
        show_error(f"Render failed: {e}")
        return None


def _process_timeline_action(ss, action: dict) -> None:
    """Process an action dict returned by the interactive timeline component."""
    logger.debug("Timeline action: %s", action)
    act = action.get("action")

    if act == "select":
        track = action.get("track")
        cid = action.get("id")
        if track and cid is not None:
            ss["_tl_selected"] = {"track": track, "id": cid}
        else:
            ss["_tl_selected"] = None

    elif act == "scrub":
        ss["_tl_playhead"] = float(action.get("time", 0.0))

    elif act == "resize":
        track = action.get("track")
        cid = action.get("id")
        new_start = action.get("start")
        new_end = action.get("end")
        if track == "segment":
            for seg in ss["_tl_segments"]:
                if seg["id"] == cid:
                    src_id = seg.get("source_id", "source_0")
                    src_dur = ss["_video_sources"].get(src_id, {}).get("duration", seg["src_end"])
                    seg["src_start"] = max(0.0, min(new_start, seg["src_end"] - 0.1))
                    seg["src_end"] = max(seg["src_start"] + 0.1, min(new_end, src_dur))
                    break
        elif track == "text":
            for t in ss["_tl_texts"]:
                if t["id"] == cid:
                    t["start"] = max(0.0, new_start)
                    t["end"] = new_end
                    break
        elif track == "image":
            for im in ss["_tl_images"]:
                if im["id"] == cid:
                    im["start"] = max(0.0, new_start)
                    im["end"] = new_end
                    break
        elif track == "video_overlay":
            for vov in ss["_tl_video_overlays"]:
                if vov["id"] == cid:
                    vov["start"] = max(0.0, new_start)
                    vov["end"] = new_end
                    break
        ss["_video_rendered_bytes"] = None

    elif act == "move":
        track = action.get("track")
        cid = action.get("id")
        items = (ss["_tl_texts"] if track == "text"
                 else ss["_tl_images"] if track == "image"
                 else ss["_tl_video_overlays"] if track == "video_overlay"
                 else [])
        for item in items:
            if item["id"] == cid:
                item["start"] = max(0.0, action.get("start", item["start"]))
                item["end"] = action.get("end", item["end"])
                break
        ss["_video_rendered_bytes"] = None

    elif act == "step_back":
        ss["_tl_playhead"] = max(0.0, ss.get("_tl_playhead", 0.0) - 0.1)

    elif act == "step_forward":
        total = action.get("total_duration", 1.0)
        ss["_tl_playhead"] = min(total, ss.get("_tl_playhead", 0.0) + 0.1)

    elif act == "goto_start":
        ss["_tl_playhead"] = 0.0

    elif act == "goto_end":
        ss["_tl_playhead"] = float(action.get("total_duration", 1.0))

    elif act == "play_toggle":
        ss["_play_preview_requested"] = True


def _format_timecode(seconds: float) -> str:
    """Format seconds as MM:SS.f timecode."""
    seconds = max(0.0, seconds)
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins:02d}:{secs:04.1f}"


def _render_transport_bar(ss, total_dur: float, playhead: float) -> None:
    """Render DaVinci Resolve-style transport controls between canvas and timeline."""
    # Timecode display
    st.markdown(
        f"**`{_format_timecode(playhead)} / {_format_timecode(total_dur)}`**"
    )

    # Transport buttons
    bc1, bc2, bc3, bc4, bc5 = st.columns(5)
    with bc1:
        if st.button("|⏮", key="btn_goto_start", use_container_width=True, help="Go to start"):
            logger.debug("Transport: goto_start")
            ss["_tl_playhead"] = 0.0
            st.rerun()
    with bc2:
        if st.button("|◀", key="btn_step_back", use_container_width=True, help="Step back 0.1s"):
            ss["_tl_playhead"] = max(0.0, playhead - 0.1)
            logger.debug("Transport: step_back to %.1f", ss["_tl_playhead"])
            st.rerun()
    with bc3:
        if st.button("▶ Preview", key="btn_preview_play", use_container_width=True, type="primary", help="Preview ~5s clip"):
            logger.debug("Transport: preview requested")
            ss["_play_preview_requested"] = True
            st.rerun()
    with bc4:
        if st.button("▶|", key="btn_step_fwd", use_container_width=True, help="Step forward 0.1s"):
            ss["_tl_playhead"] = min(total_dur, playhead + 0.1)
            logger.debug("Transport: step_fwd to %.1f", ss["_tl_playhead"])
            st.rerun()
    with bc5:
        if st.button("⏭|", key="btn_goto_end", use_container_width=True, help="Go to end"):
            logger.debug("Transport: goto_end")
            ss["_tl_playhead"] = total_dur
            st.rerun()

    # Playhead slider (moved here from canvas column)
    new_playhead = st.slider(
        "Playhead", 0.0, max(total_dur, 0.1), playhead, 0.1,
        key="_playhead_slider",
    )
    if abs(new_playhead - playhead) > 0.05:
        ss["_tl_playhead"] = new_playhead
        st.rerun()


def _render_preview_clip(ss, sources: dict, segments: list, texts: list, images: list, playhead: float, total_dur: float, video_overlays: list | None = None) -> None:
    """Render a short preview clip around the playhead and display it."""
    if not ss.get("_play_preview_requested"):
        # Show existing preview if available
        if ss.get("_preview_clip_bytes"):
            st.video(ss["_preview_clip_bytes"], format="video/mp4")
            if st.button("Close Preview", key="btn_close_preview", use_container_width=True):
                ss["_preview_clip_bytes"] = None
                st.rerun()
        return

    ss["_play_preview_requested"] = False
    st.subheader("Preview")

    import moviepy.editor as mpe

    start = max(0.0, playhead - 1.0)
    end = min(total_dur, playhead + 4.0)
    if end - start < 0.5:
        end = min(total_dur, start + 1.0)

    logger.info("Rendering preview clip: playhead=%.1f, window=%.1f-%.1f", playhead, start, end)
    with st.spinner("Rendering preview..."):
        try:
            clips_cache = {}
            subclips = []
            for seg in segments:
                src_id = seg.get("source_id", "source_0")
                if src_id not in clips_cache:
                    clips_cache[src_id] = mpe.VideoFileClip(sources[src_id]["path"])
                subclips.append(clips_cache[src_id].subclip(seg["src_start"], seg["src_end"]))

            base = mpe.concatenate_videoclips(subclips, method="compose")
            preview = base.subclip(start, min(end, base.duration))

            overlays = []
            for txt in texts:
                if txt["end"] > start and txt["start"] < end:
                    tc = (
                        mpe.TextClip(txt["text"], fontsize=txt["fontsize"],
                                     color=txt["color"], font="Liberation-Sans")
                        .set_position((txt["x"], txt["y"]))
                        .set_start(max(0, txt["start"] - start))
                        .set_end(min(preview.duration, txt["end"] - start))
                    )
                    overlays.append(tc)
            for img_ov in images:
                if img_ov["end"] > start and img_ov["start"] < end:
                    ic = (
                        mpe.ImageClip(img_ov["img_path"])
                        .resize(img_ov.get("scale", 1.0))
                        .set_position((img_ov["x"], img_ov["y"]))
                        .set_start(max(0, img_ov["start"] - start))
                        .set_end(min(preview.duration, img_ov["end"] - start))
                    )
                    overlays.append(ic)
            for vov in (video_overlays or []):
                if vov["end"] > start and vov["start"] < end:
                    src_clip = mpe.VideoFileClip(sources[vov["source_id"]]["path"])
                    sub = (
                        src_clip.subclip(vov["src_start"], vov["src_end"])
                        .resize(vov.get("scale", 1.0))
                        .set_position((vov["x"], vov["y"]))
                        .set_start(max(0, vov["start"] - start))
                        .set_end(min(preview.duration, vov["end"] - start))
                    )
                    overlays.append(sub)

            if overlays:
                final = mpe.CompositeVideoClip([preview] + overlays)
            else:
                final = preview

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_f:
                out_path = out_f.name
            final.write_videofile(out_path, preset="ultrafast", logger=None)
            for c in clips_cache.values():
                c.close()
            with open(out_path, "rb") as f:
                ss["_preview_clip_bytes"] = f.read()
            logger.info("Preview rendered: %d bytes", len(ss["_preview_clip_bytes"]))
        except Exception as e:
            logger.error("Preview render failed: %s", e, exc_info=True)
            show_error(f"Preview failed: {e}")
            return

    if ss.get("_preview_clip_bytes"):
        st.video(ss["_preview_clip_bytes"], format="video/mp4")
        if st.button("Close Preview", key="btn_close_preview", use_container_width=True):
            ss["_preview_clip_bytes"] = None
            st.rerun()


def _render_video_editor(video_bytes: bytes, filename: str) -> None:
    size_mb = len(video_bytes) / (1024 * 1024)

    if size_mb > 500:
        show_error(f"File is {size_mb:.0f} MB — maximum allowed size is 500 MB.")
        st.stop()

    if size_mb > 200:
        show_warning(f"Large file ({size_mb:.0f} MB) — processing may be slow.")

    try:
        import moviepy.editor as mpe  # noqa: F401
    except ImportError:
        show_warning("moviepy is not installed. Rebuild the Docker image to enable video editing.")
        return

    try:
        from streamlit_drawable_canvas import st_canvas
    except ImportError:
        st_canvas = None

    ss = st.session_state
    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".mp4"

    # ── Session state init (once per file) ────────────────────────────────────
    if ss.get("_video_file") != uploaded.name:
        ss["_video_file"] = uploaded.name
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src_f:
            src_f.write(video_bytes)
            src_path = src_f.name
        try:
            clip = mpe.VideoFileClip(src_path)
            dur = clip.duration
            vsize = tuple(clip.size)
            clip.close()
        except Exception as e:
            show_error(f"Could not read video: {e}")
            return

        ss["_video_sources"] = {
            "source_0": {"path": src_path, "duration": dur, "size": vsize, "name": filename},
        }
        ss["_video_next_source_id"] = 1
        ss["_tl_segments"] = [{"id": 0, "source_id": "source_0", "src_start": 0.0, "src_end": dur}]
        ss["_tl_texts"] = []
        ss["_tl_images"] = []
        ss["_tl_video_overlays"] = []
        ss["_tl_selected"] = None
        ss["_tl_next_id"] = 1
        ss["_tl_playhead"] = 0.0
        ss["_video_rendered_bytes"] = None
        ss["_frame_cache_key"] = None
        ss["_frame_cache_img"] = None
        ss["_preview_clip_bytes"] = None
        ss["_play_preview_requested"] = False
        logger.info("Video loaded: %s (%dx%d, %.1fs, %.1f MB)", filename, vsize[0], vsize[1], dur, size_mb)

    sources = ss["_video_sources"]
    primary_src = sources["source_0"]
    orig_duration = primary_src["duration"]
    vw, vh = primary_src["size"]
    segments = ss["_tl_segments"]
    total_dur = _tl_duration(segments)
    playhead = ss.get("_tl_playhead", 0.0)

    # ── Process deferred timeline action from previous cycle ──────────────────
    tl_action = ss.pop("_tl_action", None)
    if tl_action:
        _process_timeline_action(ss, tl_action)
        playhead = ss.get("_tl_playhead", 0.0)

    # Clamp playhead
    playhead = max(0.0, min(playhead, total_dur))
    ss["_tl_playhead"] = playhead

    # ── Canvas dimensions ─────────────────────────────────────────────────────
    ratio = vw / vh if vh > 0 else 16 / 9
    canvas_w = min(700, vw)
    canvas_h = int(canvas_w / ratio)
    if canvas_h > 500:
        canvas_h = 500
        canvas_w = int(canvas_h * ratio)

    # ── Extract frame at playhead ─────────────────────────────────────────────
    frame_img = _extract_frame_at_time(sources, segments, playhead)

    # ── Sync canvas positions from previous cycle ─────────────────────────────
    prev_canvas = ss.pop("_video_canvas_result", None)
    if prev_canvas is not None:
        _sync_canvas_to_overlays(prev_canvas, ss, canvas_w, canvas_h, vw, vh)

    # ── Layout: canvas + controls ─────────────────────────────────────────────
    col_canvas, col_controls = st.columns([3, 2], gap="large")

    with col_canvas:
        # Show rendered video if available
        if ss.get("_video_rendered_bytes"):
            if ss.pop("_render_just_completed", False):
                st.success("Render complete! Preview your video below.")
            st.markdown("**Rendered Output**")
            st.video(ss["_video_rendered_bytes"], format="video/mp4")
            if st.button("Back to Editor", key="btn_back_to_editor", use_container_width=True):
                ss["_video_rendered_bytes"] = None
                st.rerun()
        # Canvas preview with frame + overlays
        elif st_canvas is not None and frame_img is not None:
            # Build background image as base64
            resized = frame_img.resize((canvas_w, canvas_h), Image.LANCZOS).convert("RGB")
            buf = io.BytesIO()
            resized.save(buf, format="JPEG", quality=70)
            bg_b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

            # Build FabricJS overlay objects for overlays active at playhead
            fabric_objects = []
            active_texts = sorted(
                [t for t in ss["_tl_texts"] if t["start"] <= playhead <= t["end"]],
                key=lambda t: t["id"],
            )
            active_images = sorted(
                [im for im in ss["_tl_images"] if im["start"] <= playhead <= im["end"]],
                key=lambda im: im["id"],
            )

            for txt in active_texts:
                cx = int(txt["x"] * canvas_w / vw) if vw > 0 else 50
                cy = int(txt["y"] * canvas_h / vh) if vh > 0 else 50
                fabric_objects.append({
                    "type": "i-text",
                    "left": cx, "top": cy,
                    "text": txt["text"],
                    "fontSize": max(8, int(txt["fontsize"] * canvas_w / vw)) if vw > 0 else txt["fontsize"],
                    "fill": txt["color"],
                    "fontFamily": "Arial",
                    "selectable": True, "hasControls": True,
                })

            for img_ov in active_images:
                cx = int(img_ov["x"] * canvas_w / vw) if vw > 0 else 50
                cy = int(img_ov["y"] * canvas_h / vh) if vh > 0 else 50
                scale = img_ov.get("scale", 1.0) * (canvas_w / vw) if vw > 0 else img_ov.get("scale", 1.0)
                if img_ov.get("img_b64"):
                    fabric_objects.append({
                        "type": "image",
                        "left": cx, "top": cy,
                        "src": img_ov["img_b64"],
                        "scaleX": scale, "scaleY": scale,
                        "selectable": True, "hasControls": True,
                    })

            initial_drawing = {
                "version": "5.3.0",
                "objects": fabric_objects,
                "backgroundImage": {
                    "type": "image", "version": "5.3.0",
                    "left": 0, "top": 0, "width": canvas_w, "height": canvas_h,
                    "src": bg_b64, "scaleX": 1.0, "scaleY": 1.0,
                    "selectable": False, "hasControls": False, "evented": False,
                },
            }

            canvas_result = st_canvas(
                fill_color="rgba(0,0,0,0)",
                stroke_width=0,
                stroke_color="#000000",
                background_image=None,
                initial_drawing=initial_drawing,
                height=canvas_h,
                width=canvas_w,
                drawing_mode="transform",
                display_toolbar=False,
                update_streamlit=True,
                key="video_canvas",
            )
            ss["_video_canvas_result"] = canvas_result
        elif frame_img is not None:
            # Fallback: just show the frame as an image
            st.image(frame_img.resize((canvas_w, canvas_h), Image.LANCZOS), use_container_width=True)
        else:
            st.markdown("**Original Video**")
            st.video(video_bytes, format="video/mp4")

        # Info caption
        src_names = ", ".join(s["name"] for s in sources.values())
        st.caption(
            f"{vw}x{vh} px  |  Original: {orig_duration:.1f}s  |  "
            f"Timeline: {total_dur:.1f}s  |  {size_mb:.1f} MB  |  Sources: {src_names}"
        )

        # Big play button below canvas
        if not ss.get("_video_rendered_bytes"):
            if st.button("▶ Play Preview", key="btn_canvas_preview", use_container_width=True, type="primary"):
                ss["_play_preview_requested"] = True
                st.rerun()

    with col_controls:
        tool = st.segmented_control(
            "Tool",
            options=["select", "split", "video", "text", "image"],
            format_func={
                "select": "Select", "split": "Split",
                "video": "+Video", "text": "+Text", "image": "+Image",
            }.get,
            default="select",
            key="video_tool",
        )

        # ── Select tool ──────────────────────────────────────────────────────
        if tool == "select":
            clip_options = []
            clip_map = {}
            for seg in segments:
                src_name = sources.get(seg.get("source_id", "source_0"), {}).get("name", "?")
                label = f"V1: {src_name} {seg['src_start']:.1f}-{seg['src_end']:.1f}s"
                clip_options.append(label)
                clip_map[label] = {"track": "segment", "id": seg["id"]}
            for vov in ss["_tl_video_overlays"]:
                src_name = sources.get(vov["source_id"], {}).get("name", "?")
                label = f'V2: {src_name} @ {vov["start"]:.1f}-{vov["end"]:.1f}s'
                clip_options.append(label)
                clip_map[label] = {"track": "video_overlay", "id": vov["id"]}
            for txt in ss["_tl_texts"]:
                label = f'T1: "{txt["text"]}" @ {txt["start"]:.1f}-{txt["end"]:.1f}s'
                clip_options.append(label)
                clip_map[label] = {"track": "text", "id": txt["id"]}
            for img_ov in ss["_tl_images"]:
                label = f'I1: Image @ {img_ov["start"]:.1f}-{img_ov["end"]:.1f}s'
                clip_options.append(label)
                clip_map[label] = {"track": "image", "id": img_ov["id"]}

            if clip_options:
                current_sel = ss.get("_tl_selected")
                sel_idx = 0
                if current_sel:
                    for ci, lbl in enumerate(clip_options):
                        cm = clip_map.get(lbl, {})
                        if cm.get("track") == current_sel.get("track") and cm.get("id") == current_sel.get("id"):
                            sel_idx = ci
                            break

                chosen = st.selectbox("Select clip", clip_options, index=sel_idx, key="clip_select")
                if chosen and clip_map.get(chosen):
                    ss["_tl_selected"] = clip_map[chosen]

                sel = ss.get("_tl_selected")
                if sel:
                    sel_track = sel["track"]
                    sel_id = sel["id"]
                    clip_obj = None
                    if sel_track == "segment":
                        clip_obj = next((s for s in segments if s["id"] == sel_id), None)
                    elif sel_track == "video_overlay":
                        clip_obj = next((v for v in ss["_tl_video_overlays"] if v["id"] == sel_id), None)
                    elif sel_track == "text":
                        clip_obj = next((t for t in ss["_tl_texts"] if t["id"] == sel_id), None)
                    elif sel_track == "image":
                        clip_obj = next((im for im in ss["_tl_images"] if im["id"] == sel_id), None)
                    if clip_obj:
                        st.divider()
                        _render_clip_properties(ss, sel_track, clip_obj, total_dur, vw, vh)
                    else:
                        ss["_tl_selected"] = None
            else:
                st.caption("No clips on timeline.")

        # ── Split tool ───────────────────────────────────────────────────────
        elif tool == "split":
            st.caption("Split a video segment at a specific time.")
            seg_labels = []
            seg_map = {}
            offset = 0.0
            for seg in segments:
                dur = seg["src_end"] - seg["src_start"]
                src_name = sources.get(seg.get("source_id", "source_0"), {}).get("name", "?")
                label = f"{src_name} {seg['src_start']:.1f}-{seg['src_end']:.1f}s (tl {offset:.1f}-{offset + dur:.1f}s)"
                seg_labels.append(label)
                seg_map[label] = (seg["id"], offset, dur)
                offset += dur

            chosen_seg = st.selectbox("Segment", seg_labels, key="split_seg_select")
            if chosen_seg and seg_map.get(chosen_seg):
                seg_id, seg_offset, seg_dur = seg_map[chosen_seg]
                split_t = st.number_input(
                    "Split at (timeline seconds)",
                    min_value=seg_offset + 0.1,
                    max_value=seg_offset + seg_dur - 0.1,
                    value=seg_offset + seg_dur / 2,
                    step=0.1,
                    key="split_time",
                )
                if st.button("Split", key="btn_split", use_container_width=True):
                    logger.info("Split segment %d at timeline t=%.1f", seg_id, split_t)
                    ss["_tl_segments"] = _tl_split_segment(segments, seg_id, split_t, ss)
                    ss["_video_rendered_bytes"] = None
                    st.rerun()

        # ── +Video tool ──────────────────────────────────────────────────────
        elif tool == "video":
            st.caption("Add another video clip to the timeline.")
            new_vid = st.file_uploader(
                "Upload video", type=["mp4", "mov", "avi", "mkv", "webm"], key="v_new_video",
            )
            # Cache bytes immediately — UploadedFile buffer can be exhausted on rerun
            if new_vid is not None and ss.get("_new_vid_name") != new_vid.name:
                ss["_new_vid_name"] = new_vid.name
                ss["_new_vid_bytes"] = new_vid.read()

            has_new = ss.get("_new_vid_bytes") is not None and new_vid is not None
            if st.button("Add Video", key="btn_add_video", use_container_width=True, disabled=not has_new):
                try:
                    src_id = _add_video_source(ss, ss["_new_vid_bytes"], ss["_new_vid_name"])
                    new_src = ss["_video_sources"][src_id]
                    new_w, new_h = new_src["size"]
                    logger.info("Added video source: %s (src_id=%s, %dx%d, %.1fs)", ss["_new_vid_name"], src_id, new_w, new_h, new_src["duration"])
                    if (new_w, new_h) != (vw, vh):
                        show_warning(f"Resolution mismatch: {new_w}x{new_h} vs primary {vw}x{vh}. Output uses primary resolution.")
                    show_success(f"Added {ss['_new_vid_name']} to timeline.")
                    ss.pop("_new_vid_bytes", None)
                    ss.pop("_new_vid_name", None)
                    st.rerun()
                except Exception as e:
                    logger.error("Failed to add video source %s: %s", ss.get("_new_vid_name", "?"), e, exc_info=True)
                    show_error(str(e))

        # ── +Text overlay tool ───────────────────────────────────────────────
        elif tool == "text":
            vt_text = st.text_input("Text", value="Sample Text", key="v_txt")
            vt_size = st.slider("Font size", 12, 120, 48, key="v_txt_size")
            tc1, tc2 = st.columns(2)
            with tc1:
                vt_color = st.color_picker("Color", "#FFFFFF", key="v_txt_color")
            with tc2:
                vt_x = st.number_input("X", 0, vw, vw // 2, key="v_txt_x")
            vt_y = st.number_input("Y", 0, vh, vh // 2, key="v_txt_y")
            vt_start = st.number_input(
                "Start (s)", 0.0, max(total_dur - 0.1, 0.0), 0.0, 0.1, key="v_txt_start",
            )
            vt_end = st.number_input(
                "End (s)", 0.1, total_dur, min(total_dur, 5.0), 0.1, key="v_txt_end",
            )
            if st.button("Add Text", key="btn_add_text", use_container_width=True):
                ss["_tl_texts"].append({
                    "id": _tl_get_next_id(ss), "text": vt_text, "fontsize": vt_size,
                    "color": vt_color, "x": vt_x, "y": vt_y,
                    "start": vt_start, "end": vt_end,
                })
                ss["_video_rendered_bytes"] = None
                st.rerun()

        # ── +Image overlay tool ──────────────────────────────────────────────
        elif tool == "image":
            ov_file = st.file_uploader(
                "Overlay image", type=["png", "jpg", "jpeg", "webp"], key="v_ov_file",
            )
            ov_start = st.number_input(
                "Start (s)", 0.0, max(total_dur - 0.1, 0.0), 0.0, 0.1, key="v_ov_start",
            )
            ov_end = st.number_input(
                "End (s)", 0.1, total_dur, min(total_dur, 5.0), 0.1, key="v_ov_end",
            )
            ic1, ic2 = st.columns(2)
            with ic1:
                ov_x = st.slider("X position", 0, vw, 10, key="v_ov_x")
            with ic2:
                ov_y = st.slider("Y position", 0, vh, 10, key="v_ov_y")
            ov_scale = st.slider("Scale", 0.1, 3.0, 1.0, 0.1, key="v_ov_scale")
            if st.button("Add Overlay", key="btn_add_overlay", use_container_width=True, disabled=ov_file is None):
                try:
                    pil_ov = Image.open(ov_file).convert("RGBA")
                    # Save to temp file for render pipeline
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as ov_f:
                        pil_ov.save(ov_f.name)
                        ov_img_path = ov_f.name
                    # Encode base64 for canvas display
                    ov_buf = io.BytesIO()
                    pil_ov.save(ov_buf, format="PNG")
                    img_b64 = f"data:image/png;base64,{base64.b64encode(ov_buf.getvalue()).decode()}"
                    ss["_tl_images"].append({
                        "id": _tl_get_next_id(ss), "img_path": ov_img_path,
                        "img_b64": img_b64, "start": ov_start, "end": ov_end,
                        "x": ov_x, "y": ov_y, "scale": ov_scale,
                    })
                    ss["_video_rendered_bytes"] = None
                    st.rerun()
                except Exception as e:
                    show_error(str(e))

        st.divider()

        # ── Action buttons ────────────────────────────────────────────────────
        ac1, ac2 = st.columns(2)
        with ac1:
            render_clicked = st.button(
                "Render", key="btn_render", use_container_width=True,
            )
        with ac2:
            if st.button("Clear All", key="btn_clear_fx", use_container_width=True):
                logger.info("Clear all: reset timeline to original")
                ss["_tl_segments"] = [{"id": 0, "source_id": "source_0", "src_start": 0.0, "src_end": orig_duration}]
                ss["_tl_texts"] = []
                ss["_tl_images"] = []
                ss["_tl_video_overlays"] = []
                ss["_tl_selected"] = None
                ss["_tl_next_id"] = 1
                ss["_tl_playhead"] = 0.0
                ss["_video_rendered_bytes"] = None
                st.rerun()

        if render_clicked:
            with st.spinner("Rendering..."):
                result = _render_video_pipeline(
                    sources, ss["_tl_segments"], ss["_tl_texts"], ss["_tl_images"],
                    ss["_tl_video_overlays"],
                )
            if result:
                ss["_video_rendered_bytes"] = result
                ss["_render_just_completed"] = True
                st.rerun()

        if ss.get("_video_rendered_bytes"):
            st.download_button(
                "Download Video",
                data=ss["_video_rendered_bytes"],
                file_name="edited_video.mp4",
                mime="video/mp4",
                use_container_width=True,
            )

    # ── Transport Bar (full width between canvas/controls and timeline) ────────
    st.divider()
    _render_transport_bar(ss, total_dur, playhead)

    # ── Preview Clip ─────────────────────────────────────────────────────────
    _render_preview_clip(ss, sources, segments, ss["_tl_texts"], ss["_tl_images"], playhead, total_dur, ss["_tl_video_overlays"])

    # ── Interactive Timeline (full width below columns) ───────────────────────
    colors = get_theme_colors()
    selected = ss.get("_tl_selected")

    # Prepare serializable data for the JS component
    seg_data = [
        {"id": s["id"], "src_start": s["src_start"], "src_end": s["src_end"],
         "source_id": s.get("source_id", "source_0"),
         "source_name": sources.get(s.get("source_id", "source_0"), {}).get("name", "?")}
        for s in segments
    ]
    txt_data = [
        {"id": t["id"], "text": t["text"], "start": t["start"], "end": t["end"]}
        for t in ss["_tl_texts"]
    ]
    img_data = [
        {"id": im["id"], "start": im["start"], "end": im["end"]}
        for im in ss["_tl_images"]
    ]
    vov_data = [
        {"id": v["id"], "source_id": v["source_id"], "start": v["start"], "end": v["end"],
         "source_name": sources.get(v["source_id"], {}).get("name", "?")}
        for v in ss["_tl_video_overlays"]
    ]

    tl_result = timeline_editor(
        segments=seg_data,
        texts=txt_data,
        images=img_data,
        video_overlays=vov_data,
        selected=selected,
        total_duration=total_dur,
        playhead=playhead,
        theme_colors=colors,
        key="timeline_editor",
    )
    if tl_result and isinstance(tl_result, dict) and tl_result.get("action"):
        ss["_tl_action"] = tl_result
        st.rerun()


# ── Dispatch ──────────────────────────────────────────────────────────────────
if _render_image:
    _render_image_editor(file_bytes)
else:
    _render_video_editor(file_bytes, uploaded.name)
