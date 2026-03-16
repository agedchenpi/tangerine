# Plan: Media Editor Page for Tangerine Admin

## Context
The user wants to add a meme/video editor page to the existing Tangerine Streamlit admin interface. This is a creative tool — not a data management feature — that allows uploading an image or video, applying edits (text, shapes, image overlays, freehand drawing, video trimming), and downloading the result. It has no database interaction and no service layer.

## Files to Create / Modify

| File | Action |
|------|--------|
| `admin/pages/media_editor.py` | **Create** — new ~450-line page |
| `admin/app.py` | **Modify** — add page to navigation under a new "Tools" group |
| `requirements/admin.txt` | **Modify** — add Pillow, streamlit-drawable-canvas, moviepy |
| `Dockerfile.streamlit` | **Modify** — add `ffmpeg` system package (required by moviepy) |

---

## Implementation Plan

### 1. `requirements/admin.txt` — Add dependencies
```
Pillow>=10.0.0                       # Image manipulation
streamlit-drawable-canvas==0.9.3     # Freehand drawing component
moviepy==1.0.3                       # Video trimming and compositing
```
> Note: moviepy also pulls in `imageio`, `decorator`, `tqdm`.

### 2. `Dockerfile.streamlit` — Add system packages
In the `apt-get install` line, add `ffmpeg` alongside `curl`:
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ffmpeg && \
    ...
```

### 3. `admin/app.py` — Register new page
Add a new navigation group **"Tools"** before "System":
```python
"Tools": [
    st.Page("pages/media_editor.py", title="Media Editor", icon="🎨"),
],
```

### 4. `admin/pages/media_editor.py` — Full page implementation

#### Structure
```
load_custom_css()
add_page_header("Media Editor", icon="🎨")

# File uploader — images and videos
uploaded = st.file_uploader(...)

# Route by detected MIME type
if is_image:
    _render_image_editor(img_bytes)
elif is_video:
    _render_video_editor(video_bytes)
else:
    show_info(...)
```

#### Image Editor (`_render_image_editor`)
- **Preview**: `st.image()` of current PIL Image
- Four tabs: **Text | Shapes | Overlay | Draw**
  - **Text tab**: text input, font size slider, color picker → `ImageDraw.text()`; position (x%, y%) sliders
  - **Shapes tab**: shape type selectbox (rect/circle/line), color picker, position/size sliders → `ImageDraw.rectangle/ellipse/line()`
  - **Overlay tab**: second file uploader for overlay image; resize %, position sliders → `Image.paste()`
  - **Draw tab**: `streamlit_drawable_canvas` component set to `drawing_mode="freedraw"`; on submit, composite canvas strokes onto PIL image via `Image.fromarray()`
- **Download**: `st.download_button()` with `io.BytesIO` + `img.save()`

#### Video Editor (`_render_video_editor`)
- **Preview**: `st.video()` of original upload
- Three tabs: **Trim | Text Overlay | Image Overlay**
  - **Trim tab**: start/end time number inputs; on "Apply Trim", use `moviepy.VideoFileClip.subclip(start, end)` → write to temp file → offer download + show trimmed preview
  - **Text tab**: text input, font size, color; timestamp range sliders; use `moviepy.TextClip` + `CompositeVideoClip` → temp file + download
  - **Image Overlay tab**: upload image; position x/y%, timestamp range; use `moviepy.ImageClip` + `CompositeVideoClip` → temp file + download
- All video operations write to `tempfile.NamedTemporaryFile` and use `st.download_button`
- Size guard: warn if file > 200 MB; refuse > 500 MB

#### Error handling
- Invalid MIME type → `show_warning()`
- Processing exceptions → `show_error(str(e))` + `st.stop()`
- Library import errors → `show_warning("moviepy not installed")` with graceful degradation

#### Session state
- `st.session_state["editor_image"]` holds current PIL Image (persists across tab switches)
- `st.session_state["editor_operations"]` log for display (optional UX)

---

## Reused Patterns / Utilities
- `load_custom_css()` — `admin/utils/ui_helpers.py`
- `add_page_header()` — `admin/utils/ui_helpers.py`
- `show_success / show_error / show_warning / show_info` — `admin/components/notifications.py`

---

## Verification
1. Rebuild Docker image: `docker compose build streamlit`
2. Start app: `docker compose up streamlit`
3. Navigate to **Tools → Media Editor**
4. Test image upload → apply text + shapes + overlay + drawing → download PNG
5. Test video upload → trim 5s clip → download MP4
6. Test invalid file type shows warning
7. Test file > 500MB shows rejection message
