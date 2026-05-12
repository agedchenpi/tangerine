# Media Editor: Add Minute-Based Time Inputs

## Context

`http://100.67.142.87:8501/media_editor` exposes 12 time/duration inputs (segment trim points, overlay start/end times for text/video/image overlays) — all currently in seconds with 0.1s step. For longer footage that's tedious: typing `90.0` to mean "1 minute 30 seconds" is unfriendly when a clip is 10+ minutes.

User wants to keep seconds **and** also be able to enter the same values in **minutes**, via a unit toggle per panel (selected in clarifying Q). Storage stays in seconds (session_state, no DB), so this is purely a UI-boundary change with conversion at read time.

## Approach

Add a small **helper function** at the top of `admin/pages/media_editor.py` that renders either a seconds or minutes `number_input` and always returns seconds. Then, at the top of each properties/creation panel, render a `st.radio("Time unit", ["Seconds", "Minutes"], horizontal=True)` and pass that unit into every time-input call in that panel.

## Files to modify

- **`admin/pages/media_editor.py`** — only file. Add one helper + a unit radio + replace 12 `st.number_input(...)` calls with the helper. No service or schema changes (no service layer exists; data is ephemeral session_state per the Phase-1 exploration).

## The helper (add near the top of `media_editor.py`, e.g. just above `_render_clip_properties` at line 553)

```python
def _time_number_input(
    label: str,
    value_sec: float,
    min_sec: float,
    unit: str,
    key: str,
    *,
    max_sec: float | None = None,
    step_sec: float = 0.1,
) -> float:
    """Render a time input in either Seconds or Minutes; always return seconds.

    The widget key is suffixed with the unit so toggling the radio resets the
    widget cleanly rather than reinterpreting a stale value in the new unit.
    """
    if unit == "Minutes":
        kwargs = {
            "min_value": round(min_sec / 60.0, 4),
            "value": round(value_sec / 60.0, 4),
            "step": max(round(step_sec / 60.0, 4), 0.01),  # ~0.6s granularity
            "key": f"{key}_min",
        }
        if max_sec is not None:
            kwargs["max_value"] = round(max_sec / 60.0, 4)
        return st.number_input(f"{label} (min)", **kwargs) * 60.0

    kwargs = {
        "min_value": min_sec,
        "value": value_sec,
        "step": step_sec,
        "key": f"{key}_sec",
    }
    if max_sec is not None:
        kwargs["max_value"] = max_sec
    return st.number_input(f"{label} (s)", **kwargs)
```

Why this shape: matches the existing call patterns (some inputs pass `max_value`, some don't — see line 561 vs 567), preserves the current 0.1s step, and the unit-suffixed key prevents Streamlit from reusing the prior numeric value when the user flips the radio.

## Call-site changes (6 panels, 12 inputs total)

In each block below, add `unit_<x> = st.radio("Time unit", ["Seconds", "Minutes"], horizontal=True, key="<panel>_unit")` immediately before the first time input, then replace both `st.number_input` calls with `_time_number_input(...)`. Keys listed below are the existing widget keys to preserve (the helper appends `_sec`/`_min`).

| Panel | File location | Radio key | Inputs to convert |
|---|---|---|---|
| Segment properties | `_render_clip_properties`, `track=="segment"` — lines 560–568 | `prop_seg_unit` | `prop_seg_start`, `prop_seg_end` |
| Text overlay properties | `track=="text"` — lines 608–613 | `prop_txt_unit` | `prop_txt_start`, `prop_txt_end` |
| Video overlay (V2) properties | `track=="video_overlay"` — lines 631–636 | `prop_vov_unit` | `prop_vov_start`, `prop_vov_end` |
| Image overlay properties | `track=="image"` — lines 684–689 | `prop_img_unit` | `prop_img_start`, `prop_img_end` |
| Add Text creation tool | `tool=="text"` — lines 1339–1344 | `v_txt_unit` | `v_txt_start`, `v_txt_end` |
| Add Image overlay creation tool | `tool=="image"` — lines 1359–1364 | `v_ov_unit` | `v_ov_start`, `v_ov_end` |

### Example transformation (segment panel, lines 560–568)

Before:
```python
new_start = st.number_input(
    "Source start (s)", min_value=0.0, value=clip["src_start"],
    step=0.1, key="prop_seg_start",
)
max_end = src.get("duration", clip["src_end"] + 60.0)
new_end = st.number_input(
    "Source end (s)", min_value=0.1, value=clip["src_end"],
    max_value=max_end, step=0.1, key="prop_seg_end",
)
```

After:
```python
unit_seg = st.radio(
    "Time unit", ["Seconds", "Minutes"], horizontal=True, key="prop_seg_unit",
)
new_start = _time_number_input(
    "Source start", value_sec=clip["src_start"], min_sec=0.0,
    unit=unit_seg, key="prop_seg_start",
)
max_end = src.get("duration", clip["src_end"] + 60.0)
new_end = _time_number_input(
    "Source end", value_sec=clip["src_end"], min_sec=0.1, max_sec=max_end,
    unit=unit_seg, key="prop_seg_end",
)
```

The other 5 panels follow the same mechanical pattern. No changes to the surrounding Update/Delete buttons, no changes to validation logic (`new_start < new_end` etc.) — those still receive seconds.

## Why a helper instead of editing each call

12 call sites, 4 of which have slightly different signatures (with/without `max_value`, different defaults). Inlining the if/else 12 times would balloon the panel code and add a real chance of a typo on one of them. The helper keeps each call site to a single line and centralises the conversion.

## What is NOT changing

- `_format_timecode` (line ~860) and `format_duration` (utils) — display helpers, already work in seconds.
- The render pipeline (moviepy `subclip(...)`) — receives seconds as before.
- The dict schemas (`_tl_segments`, `_tl_texts`, `_tl_images`, `_tl_video_overlays`) — fields stay as floats in seconds.
- The 4 non-time `st.number_input` calls (X/Y positions on lines 606–607, 639–641, 1337–1338) — those are pixels.

## Verification

End-to-end smoke test in the browser at the URL the user provided:

1. **Visual sanity**: open the page, upload any video ≥30s, select a segment.
   - Properties panel shows the new `Time unit: ( ) Seconds  ( ) Minutes` radio above the start/end fields. Default is Seconds — existing layout/numbers unchanged.
2. **Round-trip conversion**: with a segment whose `src_start=30.0`, flip the radio to Minutes — field re-renders as `0.5` (min). Flip back — shows `30.0` (s). No NaN, no out-of-range error.
3. **Editing in minutes**: in Minutes mode, change end to `1.25`, click **Update**. Render the video — the clip is 75 seconds, not 1.25 seconds (i.e., conversion happened on the way *in*, not just on display).
4. **All 6 panels covered**: repeat (1)+(3) once for a text overlay, video overlay, image overlay, and each of the two "Add ..." creation tools.
5. **No regression to non-time fields**: X/Y position inputs and the Scale slider still work; the Update button still validates `start < end`.
6. **Rebuild required**: admin image bakes the source (`Dockerfile.streamlit:38`), so after editing:
   ```bash
   docker compose up -d --build admin
   ```
   Then hard-refresh the browser tab.

No unit tests to add (the page has none today, per `tests/` layout). No CHANGELOG entry needed for a small UX additive change unless the user asks.
