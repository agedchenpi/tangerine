# Music Visualizer — Emoji Fix in Title Overlay

## Context
Emojis entered in the Title Overlay (track name / artist fields) render as white tofu squares (□) in the final video. Investigation found two compounding root causes:

1. **`NotoColorEmoji.ttf` fails to load** — it's a CBDT color-bitmap font; FreeType only supports it at its native 128px size. Any other size throws `OSError: invalid pixel size`. So `font_emoji` stays `None`.
2. **Silent fallback to Liberation Sans** — which has no emoji glyphs → tofu for every emoji character.

## Solution: `pilmoji`

Replace the failing per-run font-switching approach with `pilmoji`, a purpose-built library that composites emoji PNGs (downloaded/cached from CDN on first use) over the Pillow image. It bypasses the FreeType CBDT limitation entirely.

- Pillow version in Docker: 11.3.0 (supports `pilmoji`)
- Docker containers have outbound internet → CDN downloads work; PNGs are cached after first render

## Critical Files
- `requirements/admin.txt` — add `pilmoji>=2.0`
- `admin/pages/music_visualizer.py` — simplify `_make_title_overlay`

---

## Changes

### 1. `requirements/admin.txt`
Add to the Music visualizer section:
```
pilmoji>=2.0                    # Emoji rendering in title overlay
```

### 2. `admin/pages/music_visualizer.py`

**Remove** the now-unused helpers:
- `_is_emoji(char)` function
- `_text_runs(text)` function

**Remove** from `_make_title_overlay`:
- NotoColorEmoji font loading block (the `for emoji_path in (...)` loop)
- `_font_for()` inner function
- `_measure_line()` inner function (replaced with simpler measurement)
- The per-run rendering loop

**Replace rendering in `_make_title_overlay`** with `pilmoji`:

```python
from PIL import Image, ImageDraw, ImageFont
from pilmoji import Pilmoji

# Load text font only
try:
    font_text = ImageFont.truetype(
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", font_size
    )
except OSError:
    font_text = ImageFont.load_default()

# Measure lines using regular font for sizing (emoji width approx)
dummy_img = Image.new("RGBA", (1, 1))
draw = ImageDraw.Draw(dummy_img)
line_bboxes = [draw.textbbox((0, 0), line, font=font_text) for line in lines]
line_heights = [bb[3] - bb[1] for bb in line_bboxes]
# Add generous emoji-width padding (emoji glyphs are wider than text)
line_widths = [(bb[2] - bb[0]) + font_size * line.count for bb in line_bboxes]
# simpler: count emoji chars * font_size per line as extra padding
```

Wait — measuring with Liberation Sans will give width=0 for emoji chars. To size the canvas properly, count non-text chars and add `font_size` per emoji:

```python
import unicodedata

def _rough_line_width(line, draw, font):
    # Measure with Liberation Sans (gives 0-width for emoji), then add font_size per emoji char
    bb = draw.textbbox((0, 0), line, font=font)
    text_w = bb[2] - bb[0]
    emoji_count = sum(1 for c in line if ord(c) > 0x2000)
    return text_w + emoji_count * font_size

line_widths = [_rough_line_width(ln, draw, font_text) for ln in lines]
```

Then render:
```python
txt_img = Image.new("RGBA", (max_w + font_size * 2, total_h + 4), (0, 0, 0, 0))
with Pilmoji(txt_img) as pilmoji:
    y_cursor = 0
    for i, line in enumerate(lines):
        pilmoji.text((0, y_cursor), line, fill=(*title_rgb, opacity), font=font_text)
        y_cursor += line_heights[i] + 4
```

After rendering, crop to non-transparent content:
```python
# Crop to actual bounding box of non-transparent pixels
bbox = txt_img.getbbox()
if bbox:
    txt_img = txt_img.crop(bbox)
txt_arr = np.array(txt_img)
```

This eliminates need for precise pre-measurement of emoji widths.

---

## Verification
1. `docker compose build admin && docker compose up -d admin`
2. Enable Title Overlay, enter track name with emoji (e.g. `🎵 My Song 🔥`)
3. Render → emoji appear correctly in video title
4. Text-only titles still work as before
