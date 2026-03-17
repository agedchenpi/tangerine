"""Interactive timeline editor — custom Streamlit component."""

import streamlit.components.v1 as components
from pathlib import Path

_component_func = components.declare_component(
    "timeline_editor",
    path=str(Path(__file__).parent / "frontend"),
)


def timeline_editor(segments, texts, images, selected, total_duration, playhead, theme_colors, video_overlays=None, key="timeline_editor"):
    """Render interactive timeline and return user actions (select/resize/move/scrub)."""
    return _component_func(
        segments=segments,
        texts=texts,
        images=images,
        video_overlays=video_overlays or [],
        selected=selected,
        total_duration=total_duration,
        playhead=playhead,
        theme_colors=theme_colors,
        key=key,
        default=None,
    )
