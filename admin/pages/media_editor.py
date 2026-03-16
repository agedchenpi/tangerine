"""Media Editor — image and video editing tools."""

import io
import tempfile

import streamlit as st
from PIL import Image, ImageDraw

from utils.ui_helpers import load_custom_css, add_page_header
from components.notifications import show_success, show_error, show_warning, show_info

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
file_bytes = uploaded.read()

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
    # Initialise session state image
    if "editor_image" not in st.session_state or st.session_state.get("_editor_file") != uploaded.name:
        st.session_state["editor_image"] = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        st.session_state["_editor_file"] = uploaded.name

    img: Image.Image = st.session_state["editor_image"]
    w, h = img.size

    col_preview, col_controls = st.columns([2, 3], gap="large")

    with col_preview:
        st.markdown("**Preview**")
        # Display as RGB for st.image compatibility
        st.image(img.convert("RGB"), use_column_width=True)
        st.caption(f"{w} × {h} px")

        # Download button
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        st.download_button(
            "⬇️ Download PNG",
            data=buf.getvalue(),
            file_name="edited_image.png",
            mime="image/png",
            use_container_width=True,
        )

        if st.button("↩️ Reset Image", use_container_width=True):
            st.session_state["editor_image"] = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
            st.rerun()

    with col_controls:
        tab_text, tab_shapes, tab_overlay, tab_draw = st.tabs(["✏️ Text", "🔷 Shapes", "🖼️ Overlay", "🎨 Draw"])

        # ── Text tab ──────────────────────────────────────────────────────────
        with tab_text:
            text_input = st.text_input("Text", value="Hello!")
            font_size = st.slider("Font size", 10, 200, 40, key="txt_size")
            text_color = st.color_picker("Color", "#FFFFFF", key="txt_color")
            x_pct = st.slider("X position (%)", 0, 100, 10, key="txt_x")
            y_pct = st.slider("Y position (%)", 0, 100, 10, key="txt_y")

            if st.button("Add Text", key="btn_text", use_container_width=True):
                try:
                    draw = ImageDraw.Draw(img.copy() if False else img)
                    working = img.copy()
                    draw2 = ImageDraw.Draw(working)
                    x = int(w * x_pct / 100)
                    y = int(h * y_pct / 100)
                    # Parse hex color → RGBA
                    r = int(text_color[1:3], 16)
                    g = int(text_color[3:5], 16)
                    b = int(text_color[5:7], 16)
                    draw2.text((x, y), text_input, fill=(r, g, b, 255))
                    st.session_state["editor_image"] = working
                    show_success("Text added.")
                    st.rerun()
                except Exception as e:
                    show_error(str(e))

        # ── Shapes tab ────────────────────────────────────────────────────────
        with tab_shapes:
            shape = st.selectbox("Shape", ["Rectangle", "Ellipse", "Line"], key="shape_type")
            shape_color = st.color_picker("Color", "#FF0000", key="shape_color")
            shape_width = st.slider("Line width (px)", 1, 20, 3, key="shape_lw")
            x1_pct = st.slider("X1 (%)", 0, 100, 20, key="sx1")
            y1_pct = st.slider("Y1 (%)", 0, 100, 20, key="sy1")
            x2_pct = st.slider("X2 (%)", 0, 100, 80, key="sx2")
            y2_pct = st.slider("Y2 (%)", 0, 100, 80, key="sy2")

            if st.button("Add Shape", key="btn_shape", use_container_width=True):
                try:
                    working = img.copy()
                    draw = ImageDraw.Draw(working)
                    x1 = int(w * x1_pct / 100)
                    y1 = int(h * y1_pct / 100)
                    x2 = int(w * x2_pct / 100)
                    y2 = int(h * y2_pct / 100)
                    r = int(shape_color[1:3], 16)
                    g = int(shape_color[3:5], 16)
                    b = int(shape_color[5:7], 16)
                    fill_color = (r, g, b, 255)
                    if shape == "Rectangle":
                        draw.rectangle([x1, y1, x2, y2], outline=fill_color, width=shape_width)
                    elif shape == "Ellipse":
                        draw.ellipse([x1, y1, x2, y2], outline=fill_color, width=shape_width)
                    else:
                        draw.line([x1, y1, x2, y2], fill=fill_color, width=shape_width)
                    st.session_state["editor_image"] = working
                    show_success("Shape added.")
                    st.rerun()
                except Exception as e:
                    show_error(str(e))

        # ── Overlay tab ───────────────────────────────────────────────────────
        with tab_overlay:
            overlay_file = st.file_uploader("Overlay image", type=["png", "jpg", "jpeg", "webp"], key="overlay_file")
            if overlay_file:
                overlay_scale = st.slider("Overlay size (%)", 5, 100, 30, key="ov_scale")
                ox_pct = st.slider("X position (%)", 0, 100, 50, key="ov_x")
                oy_pct = st.slider("Y position (%)", 0, 100, 50, key="ov_y")

                if st.button("Apply Overlay", key="btn_overlay", use_container_width=True):
                    try:
                        overlay = Image.open(overlay_file).convert("RGBA")
                        new_w = max(1, int(w * overlay_scale / 100))
                        new_h = max(1, int(overlay.height * new_w / overlay.width))
                        overlay = overlay.resize((new_w, new_h), Image.LANCZOS)
                        ox = int(w * ox_pct / 100)
                        oy = int(h * oy_pct / 100)
                        working = img.copy()
                        working.paste(overlay, (ox, oy), overlay)
                        st.session_state["editor_image"] = working
                        show_success("Overlay applied.")
                        st.rerun()
                    except Exception as e:
                        show_error(str(e))
            else:
                show_info("Upload an overlay image above.")

        # ── Draw tab ──────────────────────────────────────────────────────────
        with tab_draw:
            try:
                from streamlit_drawable_canvas import st_canvas

                draw_color = st.color_picker("Brush color", "#FF0000", key="draw_color")
                draw_width = st.slider("Brush size", 1, 50, 5, key="draw_width")

                canvas_result = st_canvas(
                    fill_color="rgba(0,0,0,0)",
                    stroke_width=draw_width,
                    stroke_color=draw_color,
                    background_image=img.convert("RGB"),
                    height=min(h, 500),
                    width=min(w, 700),
                    drawing_mode="freedraw",
                    key="canvas",
                )

                if st.button("Apply Drawing", key="btn_draw", use_container_width=True):
                    if canvas_result.image_data is not None:
                        try:
                            import numpy as np
                            canvas_arr = canvas_result.image_data  # RGBA numpy array
                            canvas_img = Image.fromarray(canvas_arr.astype("uint8"), "RGBA")
                            # Scale canvas back to original image size if needed
                            if canvas_img.size != (w, h):
                                canvas_img = canvas_img.resize((w, h), Image.LANCZOS)
                            working = img.copy()
                            working.paste(canvas_img, (0, 0), canvas_img)
                            st.session_state["editor_image"] = working
                            show_success("Drawing applied.")
                            st.rerun()
                        except Exception as e:
                            show_error(str(e))
                    else:
                        show_warning("Draw something on the canvas first.")
            except ImportError:
                show_warning("streamlit-drawable-canvas is not installed. Rebuild the Docker image to enable this feature.")


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
