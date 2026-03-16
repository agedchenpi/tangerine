# Plan: Fix Image Upload Failures in Media Editor

## Context

The media editor has intermittent issues uploading images: sometimes a 400 error appears below the uploader, sometimes nothing happens at all (page appears stalled). Previous fixes (`update_streamlit=False`, base64 backgroundImage, stable canvas key) addressed WebSocket flooding but didn't fix the root cause.

**Root cause**: `streamlit-drawable-canvas==0.9.3` is archived and its React frontend has broken `baseUrlPath` routing for Streamlit 1.39.0+. This causes 400 errors from the component's HTTP requests, which destabilize the Streamlit session and cause subsequent file uploads to fail or hang.

**Solution**: Upgrade Streamlit from 1.39.0 → 1.49.1 and switch to the maintained fork `streamlit-drawable-canvas-fix==0.9.8`, which fixes the `image_to_url` import path and React frontend routing.

**Verified compatibility**: All dependencies resolve cleanly:
- `streamlit-aggrid==0.3.4.post3` — requires `>=0.87.0`, imports OK with 1.49.1
- `plotly==5.18.0` — no Streamlit version constraint
- `streamlit-drawable-canvas-fix==0.9.8` — requires `>=1.49.0`, imports OK
- No app code uses `st.experimental_*` or `streamlit.elements.image` directly

---

## Files to Modify

| File | Change |
|------|--------|
| `requirements/admin.txt` | Upgrade streamlit, swap canvas package |
| `admin/pages/media_editor.py` | Already has `update_streamlit=False` — no change needed |

---

## Implementation

### 1. Update `requirements/admin.txt`

```diff
- streamlit==1.39.0
+ streamlit==1.49.1

  ...

- streamlit-drawable-canvas==0.9.3  # Freehand drawing component
+ streamlit-drawable-canvas-fix==0.9.8  # Freehand drawing component (maintained fork)
```

The fork uses the same Python module name `streamlit_drawable_canvas` — no import changes needed anywhere.

### 2. No changes to `media_editor.py`

`update_streamlit=False` (line 152) is already applied from the previous fix. No other code changes needed — the fork is a drop-in replacement.

---

## What stays unchanged (already applied in working copy)

- `update_streamlit=False` — stops per-mouse-event WebSocket round trips
- `key="canvas"` — stable canvas key (prevents remount on mode switch)
- `background_image=None` + base64 `backgroundImage` in `initial_drawing` — avoids MediaFileHandler
- JPEG Q70 background compression — reduces payload size

---

## Verification

1. `docker compose build admin && docker compose up -d admin`
2. Upload a .png file — no 400 error, canvas loads immediately
3. Upload a second image — no stalling or 400
4. Paint freely — smooth strokes, no flashing
5. Switch modes — canvas state preserved
6. Download PNG — includes background + all edits
7. Hard refresh browser → re-upload → no errors
8. Verify other admin pages still work (imports, scheduler, etc. that use AgGrid)
