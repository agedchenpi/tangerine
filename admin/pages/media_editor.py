"""Media Editor — image and video editing tools."""

import base64
import io
import logging
import tempfile

import streamlit as st
from PIL import Image, ImageDraw

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
# VIDEO EDITOR
# ══════════════════════════════════════════════════════════════════════════════
def _render_video_editor(video_bytes: bytes, filename: str) -> None:
    size_mb = len(video_bytes) / (1024 * 1024)

    if size_mb > 500:
        show_error(f"File is {size_mb:.0f} MB — maximum allowed size is 500 MB.")
        st.stop()

    if size_mb > 200:
        show_warning(f"Large file ({size_mb:.0f} MB) — processing may be slow.")

    st.markdown("**Original Video**")
    st.video(video_bytes)

    try:
        import moviepy.editor as mpe
    except ImportError:
        show_warning("moviepy is not installed. Rebuild the Docker image to enable video editing.")
        return

    # Write upload to a temp file so moviepy can read it
    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".mp4"

    tab_trim, tab_text, tab_img_overlay = st.tabs(["✂️ Trim", "📝 Text Overlay", "🖼️ Image Overlay"])

    # ── Trim tab ──────────────────────────────────────────────────────────────
    with tab_trim:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src_f:
            src_f.write(video_bytes)
            src_path = src_f.name

        try:
            clip = mpe.VideoFileClip(src_path)
            duration = clip.duration
            clip.close()
        except Exception as e:
            show_error(f"Could not read video: {e}")
            return

        st.caption(f"Duration: {duration:.1f}s")
        start_t = st.number_input("Start time (s)", min_value=0.0, max_value=duration - 0.1, value=0.0, step=0.1, key="trim_start")
        end_t = st.number_input("End time (s)", min_value=0.1, max_value=duration, value=min(duration, 10.0), step=0.1, key="trim_end")

        if st.button("Apply Trim", key="btn_trim", use_container_width=True):
            if start_t >= end_t:
                show_warning("Start time must be before end time.")
            else:
                try:
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_f:
                        out_path = out_f.name
                    clip = mpe.VideoFileClip(src_path).subclip(start_t, end_t)
                    clip.write_videofile(out_path, logger=None)
                    clip.close()
                    with open(out_path, "rb") as f:
                        trimmed_bytes = f.read()
                    show_success(f"Trimmed to {end_t - start_t:.1f}s.")
                    st.video(trimmed_bytes)
                    st.download_button("⬇️ Download Trimmed Video", data=trimmed_bytes, file_name="trimmed.mp4", mime="video/mp4", use_container_width=True)
                except Exception as e:
                    show_error(str(e))

    # ── Text Overlay tab ──────────────────────────────────────────────────────
    with tab_text:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src_f2:
            src_f2.write(video_bytes)
            src_path2 = src_f2.name

        try:
            clip2 = mpe.VideoFileClip(src_path2)
            dur2 = clip2.duration
            clip2.close()
        except Exception as e:
            show_error(f"Could not read video: {e}")
            return

        vt_text = st.text_input("Text to overlay", value="Sample Text", key="vt_text")
        vt_size = st.slider("Font size", 12, 120, 48, key="vt_size")
        vt_color = st.color_picker("Text color", "#FFFFFF", key="vt_color")
        vt_start = st.number_input("Show from (s)", 0.0, dur2 - 0.1, 0.0, 0.1, key="vt_start")
        vt_end = st.number_input("Show until (s)", 0.1, dur2, min(dur2, 5.0), 0.1, key="vt_end")

        if st.button("Apply Text Overlay", key="btn_vtext", use_container_width=True):
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_f2:
                    out_path2 = out_f2.name
                base_clip = mpe.VideoFileClip(src_path2)
                txt_clip = (
                    mpe.TextClip(vt_text, fontsize=vt_size, color=vt_color)
                    .set_position("center")
                    .set_start(vt_start)
                    .set_end(vt_end)
                )
                comp = mpe.CompositeVideoClip([base_clip, txt_clip])
                comp.write_videofile(out_path2, logger=None)
                base_clip.close()
                with open(out_path2, "rb") as f:
                    result_bytes = f.read()
                show_success("Text overlay applied.")
                st.video(result_bytes)
                st.download_button("⬇️ Download Video", data=result_bytes, file_name="text_overlay.mp4", mime="video/mp4", use_container_width=True)
            except Exception as e:
                show_error(str(e))

    # ── Image Overlay tab ─────────────────────────────────────────────────────
    with tab_img_overlay:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src_f3:
            src_f3.write(video_bytes)
            src_path3 = src_f3.name

        try:
            clip3 = mpe.VideoFileClip(src_path3)
            dur3 = clip3.duration
            vw, vh = clip3.size
            clip3.close()
        except Exception as e:
            show_error(f"Could not read video: {e}")
            return

        ov_img_file = st.file_uploader("Overlay image", type=["png", "jpg", "jpeg", "webp"], key="vid_overlay_img")
        if ov_img_file:
            ov_scale = st.slider("Overlay size (% of video width)", 5, 80, 20, key="vid_ov_scale")
            ov_x_pct = st.slider("X position (%)", 0, 100, 10, key="vid_ov_x")
            ov_y_pct = st.slider("Y position (%)", 0, 100, 10, key="vid_ov_y")
            ov_start = st.number_input("Show from (s)", 0.0, dur3 - 0.1, 0.0, 0.1, key="vid_ov_start")
            ov_end = st.number_input("Show until (s)", 0.1, dur3, min(dur3, 5.0), 0.1, key="vid_ov_end")

            if st.button("Apply Image Overlay", key="btn_vid_overlay", use_container_width=True):
                try:
                    # Save overlay image to temp file
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as ov_f:
                        pil_ov = Image.open(ov_img_file).convert("RGBA")
                        new_w = max(1, int(vw * ov_scale / 100))
                        new_h = max(1, int(pil_ov.height * new_w / pil_ov.width))
                        pil_ov = pil_ov.resize((new_w, new_h), Image.LANCZOS)
                        pil_ov.save(ov_f.name)
                        ov_img_path = ov_f.name

                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as out_f3:
                        out_path3 = out_f3.name

                    base_clip3 = mpe.VideoFileClip(src_path3)
                    img_clip = (
                        mpe.ImageClip(ov_img_path)
                        .set_position((int(vw * ov_x_pct / 100), int(vh * ov_y_pct / 100)))
                        .set_start(ov_start)
                        .set_end(ov_end)
                    )
                    comp3 = mpe.CompositeVideoClip([base_clip3, img_clip])
                    comp3.write_videofile(out_path3, logger=None)
                    base_clip3.close()
                    with open(out_path3, "rb") as f:
                        result_bytes3 = f.read()
                    show_success("Image overlay applied.")
                    st.video(result_bytes3)
                    st.download_button("⬇️ Download Video", data=result_bytes3, file_name="image_overlay.mp4", mime="video/mp4", use_container_width=True)
                except Exception as e:
                    show_error(str(e))
        else:
            show_info("Upload an overlay image above.")


# ── Dispatch ──────────────────────────────────────────────────────────────────
if _render_image:
    _render_image_editor(file_bytes)
else:
    _render_video_editor(file_bytes, uploaded.name)
