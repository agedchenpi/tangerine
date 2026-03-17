# Plan: Fix ANTIALIAS Error in Video Editor Render/Preview

## Context

After implementing V2 track support, render and preview fail with:
```
AttributeError: module 'PIL.Image' has no attribute 'ANTIALIAS'
```

**Root cause:** moviepy 1.0.3's `resize.py` (line 37) calls `Image.ANTIALIAS`, which was removed in Pillow 10+. The container has Pillow 11.3.0. This only triggers when `.resize()` is called on a moviepy clip — which happens for V2 video overlays (both render and preview pipelines use `.resize(vov.get("scale", 1.0))`).

## File to Modify

| File | Change |
|------|--------|
| `admin/pages/media_editor.py` | Add Pillow compatibility monkey-patch at module level |

## Fix

Add a Pillow compatibility shim at the top of `media_editor.py` (after the `from PIL import` line, ~line 9), before any moviepy import can execute:

```python
# moviepy 1.0.3 uses Image.ANTIALIAS, removed in Pillow 10+
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS
```

This is the standard fix for this well-known moviepy/Pillow incompatibility. `ANTIALIAS` was just an alias for `LANCZOS` before it was removed.

## Verification

1. `python3 -m py_compile admin/pages/media_editor.py`
2. `docker compose up -d --build admin`
3. Upload video → add a second video via +Video → Render → should succeed
4. Preview button → should play without error
5. `docker compose logs admin --tail 20` — no ANTIALIAS errors
