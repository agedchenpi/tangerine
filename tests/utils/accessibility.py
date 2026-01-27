"""
Accessibility testing utilities for WCAG 2.1 compliance.

Provides contrast ratio calculation and validation functions.
"""
import re
from typing import Tuple


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#FFFFFF" or "FFFFFF")

    Returns:
        Tuple of (R, G, B) values (0-255)

    Examples:
        >>> hex_to_rgb("#FFFFFF")
        (255, 255, 255)
        >>> hex_to_rgb("1E1E2E")
        (30, 30, 46)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """
    Calculate relative luminance following WCAG 2.1 formula.

    Formula: L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    where R, G, B are normalized and gamma-corrected values.

    Args:
        rgb: Tuple of (R, G, B) values (0-255)

    Returns:
        Relative luminance (0.0 to 1.0)

    Reference: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """
    # Normalize to 0-1 range
    r, g, b = [c / 255.0 for c in rgb]

    # Apply gamma correction
    def gamma_correct(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = gamma_correct(r)
    g_lin = gamma_correct(g)
    b_lin = gamma_correct(b)

    # Calculate luminance
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(color1: str, color2: str) -> float:
    """
    Calculate contrast ratio between two colors.

    Formula: (L1 + 0.05) / (L2 + 0.05)
    where L1 is the lighter color's luminance and L2 is the darker.

    Args:
        color1: First hex color (e.g., "#FFFFFF")
        color2: Second hex color (e.g., "#1E1E2E")

    Returns:
        Contrast ratio (1.0 to 21.0)

    Reference: https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio

    Examples:
        >>> contrast_ratio("#FFFFFF", "#1E1E2E")
        21.0  # Maximum contrast (white on very dark)
        >>> contrast_ratio("#FFFFFF", "#FFFFFF")
        1.0   # No contrast (same color)
    """
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)

    lum1 = relative_luminance(rgb1)
    lum2 = relative_luminance(rgb2)

    # Ensure L1 is the lighter color
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    return (lighter + 0.05) / (darker + 0.05)


def meets_wcag_aa(foreground: str, background: str, is_large_text: bool = False) -> bool:
    """
    Check if color combination meets WCAG AA standards.

    WCAG AA Requirements:
    - Normal text: 4.5:1 minimum contrast ratio
    - Large text: 3:1 minimum contrast ratio
      (Large text = ≥18pt or ≥14pt bold)

    Args:
        foreground: Foreground/text color hex
        background: Background color hex
        is_large_text: Whether the text is considered "large" per WCAG

    Returns:
        True if meets WCAG AA standards

    Reference: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
    """
    ratio = contrast_ratio(foreground, background)
    threshold = 3.0 if is_large_text else 4.5
    return ratio >= threshold


def meets_wcag_aaa(foreground: str, background: str, is_large_text: bool = False) -> bool:
    """
    Check if color combination meets WCAG AAA standards.

    WCAG AAA Requirements:
    - Normal text: 7:1 minimum contrast ratio
    - Large text: 4.5:1 minimum contrast ratio

    Args:
        foreground: Foreground/text color hex
        background: Background color hex
        is_large_text: Whether the text is considered "large" per WCAG

    Returns:
        True if meets WCAG AAA standards
    """
    ratio = contrast_ratio(foreground, background)
    threshold = 4.5 if is_large_text else 7.0
    return ratio >= threshold
