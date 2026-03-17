# Plan: Fix Video TextClip Bug + Redesign Video Editor UX

## Context

The video editor's Text Overlay feature crashes because moviepy's `TextClip` requires ImageMagick, which isn't installed in the Docker image. Additionally, the current video editor uses disconnected tabs (Trim, Text, Image) where each operation is isolated — you can't combine effects. The user wants a simplified DaVinci Resolve / Adobe Premiere inspired layout with a unified effects pipeline.

## Files to Modify

1. **`Dockerfile.streamlit`** (line 18) — add `imagemagick fonts-liberation`, patch policy.xml
2. **`admin/pages/media_editor.py`** (lines 299–459) — rewrite `_render_video_editor()`

## Part 1: Fix ImageMagick (Dockerfile.streamlit)

Replace lines 16-20:

```dockerfile
# Install curl, ffmpeg, and ImageMagick for healthcheck + video editing
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ffmpeg imagemagick fonts-liberation && \
    sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

- `imagemagick` — required by moviepy's `TextClip` (uses `convert` binary)
- `fonts-liberation` — provides Liberation Sans font for text rendering
- `sed` fix — ImageMagick 6 default policy blocks `@` pattern (text rendering); `|| true` guards if path differs

## Part 2: Rewrite Video Editor UX

### New Layout (mirrors image editor pattern)

```
col_preview [3]            | col_controls [2]
───────────────────────────|──────────────────────────────
Video Preview              | Tool: [✂️ Trim | 📝 Text | 🖼️ Image]
(original or rendered)     |   (per-tool settings inline)
                           | ─────────
Duration / Resolution info | Effects Queue:
                           |   1. Trim 2.0s–8.0s  [✕]
                           |   2. Text "Hello" @ 0–3s  [✕]
                           | ─────────
                           | [▶ Render]  [↩️ Clear All]
                           | [⬇️ Download]
```

### Implementation Structure

#### A. Helper functions (before `_render_video_editor`)

**`_format_effect(fx)`** — returns human-readable label for queue display

**`_apply_effects(src_path, effects)`** — render pipeline:
- Opens `VideoFileClip` once
- Applies effects in order: trim → subclip, text → CompositeVideoClip, image → CompositeVideoClip
- Writes to temp file, stores bytes in `ss["_video_rendered_bytes"]`
- Uses `font="Liberation-Sans"` for TextClip
- Wraps in try/except with `show_error()`

#### B. `_render_video_editor()` rewrite

1. **Size guard** — keep existing 500MB limit / 200MB warning
2. **Import moviepy** — keep existing ImportError guard
3. **Session state init** (on new file upload):
   - Write temp file **once** (not 3x like current)
   - Read clip metadata **once** (duration, resolution)
   - Init `_video_effects = []`, `_video_rendered_bytes = None`
4. **Column layout**: `st.columns([3, 2], gap="large")`
5. **Left column** — video preview (rendered if available, else original) + metadata caption
6. **Right column**:
   - Segmented tool selector: `["trim", "text", "image"]`
   - Per-tool controls (only active tool shown):
     - **Trim**: start/end number inputs + "Add Trim" button
     - **Text**: text input, font size slider, 2-col (color picker + position select), start/end + "Add Text" button
     - **Image**: file uploader, scale slider, x/y position sliders, start/end + "Add Overlay" button
   - Each "Add" button appends to `_video_effects` list and reruns
   - Divider
   - **Effects Queue**: numbered list with remove (✕) buttons per effect
   - Caption: "Times are relative to clip after preceding effects"
   - Divider
   - **Action buttons**: [▶ Render] + [↩️ Clear All] in 2 columns
   - **Download button**: shown only after render completes

### Key Design Decisions

- **Effects pipeline** vs disconnected tabs — effects compose (trim then overlay works)
- **Single temp file** — eliminates 3x file duplication bug
- **Render-on-demand** — no auto-render; user clicks "Render" when ready
- **Add → queue → render** workflow — like NLE effects stack
- **Remove individual effects** — ✕ button on each queue item
- **Auto-clear rendered result** when effects change (add/remove)

## Verification

1. `docker compose build admin && docker compose up -d admin`
2. Upload MP4 → preview shows in left column, tools in right
3. Add trim effect → appears in queue
4. Add text effect → appears in queue (no ImageMagick crash)
5. Click "Render" → spinner, then rendered video replaces preview
6. Download works
7. Remove effect with ✕ → queue updates
8. "Clear All" resets everything
9. Upload new file → state resets cleanly
