"""
Unit tests for accessibility utilities.

Tests contrast ratio calculation and WCAG compliance functions.
"""
import pytest
from tests.utils.accessibility import (
    hex_to_rgb,
    relative_luminance,
    contrast_ratio,
    meets_wcag_aa,
    meets_wcag_aaa
)


@pytest.mark.unit
class TestHexToRgb:
    """Test hex color to RGB conversion."""

    def test_white_color(self):
        """White (#FFFFFF) converts correctly"""
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("FFFFFF") == (255, 255, 255)  # Without #

    def test_black_color(self):
        """Black (#000000) converts correctly"""
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_dark_sidebar_background(self):
        """Dark mode sidebar background (#1E1E2E) converts correctly"""
        assert hex_to_rgb("#1E1E2E") == (30, 30, 46)

    def test_tangerine_color(self):
        """Tangerine primary (#FFA05C) converts correctly"""
        assert hex_to_rgb("#FFA05C") == (255, 160, 92)


@pytest.mark.unit
class TestRelativeLuminance:
    """Test relative luminance calculation."""

    def test_white_luminance(self):
        """White has luminance ~1.0"""
        lum = relative_luminance((255, 255, 255))
        assert 0.99 < lum <= 1.0

    def test_black_luminance(self):
        """Black has luminance ~0.0"""
        lum = relative_luminance((0, 0, 0))
        assert lum == 0.0

    def test_dark_background_luminance(self):
        """Dark sidebar background has low luminance"""
        lum = relative_luminance((30, 30, 46))
        assert 0.01 < lum < 0.02  # Very dark


@pytest.mark.unit
class TestContrastRatio:
    """Test contrast ratio calculation."""

    def test_maximum_contrast(self):
        """White on black gives maximum contrast (21:1)"""
        ratio = contrast_ratio("#FFFFFF", "#000000")
        assert 20.9 < ratio <= 21.0

    def test_minimum_contrast(self):
        """Same colors give minimum contrast (1:1)"""
        ratio = contrast_ratio("#FFFFFF", "#FFFFFF")
        assert ratio == 1.0

    def test_dark_mode_header_contrast(self):
        """White headers on dark sidebar meet WCAG AAA"""
        ratio = contrast_ratio("#FFFFFF", "#1E1E2E")
        assert ratio >= 16.0  # Should be ~16.4:1

    def test_dark_mode_link_contrast(self):
        """Light gray links on dark sidebar meet WCAG AAA"""
        ratio = contrast_ratio("#E8E8E8", "#1E1E2E")
        assert ratio >= 13.0  # Should be ~13.4:1

    def test_tangerine_accent_contrast(self):
        """Tangerine accent on dark sidebar meets WCAG AA"""
        ratio = contrast_ratio("#FFA05C", "#1E1E2E")
        assert ratio >= 8.0  # Should be ~8.2:1


@pytest.mark.unit
class TestWcagCompliance:
    """Test WCAG AA/AAA compliance checking."""

    def test_wcag_aa_normal_text_pass(self):
        """White on dark passes WCAG AA for normal text (4.5:1)"""
        assert meets_wcag_aa("#FFFFFF", "#1E1E2E", is_large_text=False) is True

    def test_wcag_aa_normal_text_fail(self):
        """Low contrast fails WCAG AA for normal text"""
        assert meets_wcag_aa("#CCCCCC", "#BBBBBB", is_large_text=False) is False

    def test_wcag_aa_large_text_pass(self):
        """Lower contrast passes WCAG AA for large text (3:1)"""
        # This would fail for normal text but pass for large text
        assert meets_wcag_aa("#959595", "#000000", is_large_text=True) is True

    def test_wcag_aaa_pass(self):
        """White on dark passes WCAG AAA (7:1)"""
        assert meets_wcag_aaa("#FFFFFF", "#1E1E2E", is_large_text=False) is True

    def test_wcag_aaa_fail(self):
        """Moderate contrast fails WCAG AAA"""
        # 4.5:1 ratio - passes AA but fails AAA
        assert meets_wcag_aaa("#767676", "#000000", is_large_text=False) is False


@pytest.mark.unit
class TestDarkModeColors:
    """Test actual Tangerine dark mode color compliance."""

    def test_nav_headers_wcag_aaa(self):
        """Navigation headers (white on dark) exceed WCAG AAA"""
        ratio = contrast_ratio("#FFFFFF", "#1E1E2E")
        assert ratio >= 7.0  # WCAG AAA threshold
        assert meets_wcag_aaa("#FFFFFF", "#1E1E2E", is_large_text=True) is True

    def test_nav_links_wcag_aaa(self):
        """Navigation links (gray on dark) exceed WCAG AAA"""
        ratio = contrast_ratio("#E8E8E8", "#1E1E2E")
        assert ratio >= 7.0
        assert meets_wcag_aaa("#E8E8E8", "#1E1E2E") is True

    def test_tangerine_accent_wcag_aa(self):
        """Tangerine accent (orange on dark) meets WCAG AA"""
        ratio = contrast_ratio("#FFA05C", "#1E1E2E")
        assert ratio >= 4.5
        assert meets_wcag_aa("#FFA05C", "#1E1E2E") is True

    def test_muted_text_wcag_aa(self):
        """Muted text color meets WCAG AA"""
        ratio = contrast_ratio("#8A8F98", "#1E1E2E")
        assert ratio >= 4.5
        assert meets_wcag_aa("#8A8F98", "#1E1E2E") is True


@pytest.mark.unit
class TestLightModeColors:
    """Test Tangerine light mode color compliance."""

    def test_nav_headers_light_mode(self):
        """Navigation headers (dark on white) meet WCAG AAA"""
        ratio = contrast_ratio("#1E1E2E", "#FFFFFF")
        assert ratio >= 7.0
        assert meets_wcag_aaa("#1E1E2E", "#FFFFFF", is_large_text=True) is True

    def test_nav_links_light_mode(self):
        """Navigation links in light mode meet WCAG AA"""
        ratio = contrast_ratio("#4A4A4A", "#FFFFFF")
        assert ratio >= 4.5
        assert meets_wcag_aa("#4A4A4A", "#FFFFFF") is True

    def test_tangerine_accent_light_mode(self):
        """Tangerine accent in light mode has low contrast (decorative only)"""
        ratio = contrast_ratio("#FF8C42", "#FFFFFF")
        # Note: This color combination does NOT meet WCAG AA standards
        # Tangerine accent in light mode should only be used for:
        # - Decorative elements (borders, icons, non-text)
        # - Non-critical UI elements
        # - Background accents
        # For text content, use --tangerine-dark (#D67130) which has better contrast
        assert ratio >= 2.0  # Actual: ~2.31:1
        assert meets_wcag_aa("#FF8C42", "#FFFFFF", is_large_text=False) is False
        assert meets_wcag_aa("#FF8C42", "#FFFFFF", is_large_text=True) is False
