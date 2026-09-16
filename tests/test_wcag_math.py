"""
VisionGuard AI - WCAG Math Engine Unit Tests
===============================================
Comprehensive tests for the deterministic WCAG 2.1 math engine.

These tests verify that every calculation matches the W3C specification
exactly. The WCAG checker must be 100% mathematically accurate — there
is zero tolerance for error in accessibility compliance math.

Run with: python -m pytest tests/test_wcag_math.py -v
"""

import math
import sys
import os

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dom_accessibility.wcag_checker import (
    parse_color,
    linearize_srgb_channel,
    relative_luminance,
    contrast_ratio,
    check_contrast,
    audit_computed_styles,
    simulate_color_blindness,
    check_contrast_for_color_blind,
    suggest_fix_color,
    _is_large_text,
    _alpha_composite,
    _gamma_compress,
    ContrastResult,
    AccessibilityAuditResult,
)
from dom_accessibility.dom_parser import DOMParser, DOMAnalysisResult
from dom_accessibility.ast_extractor import ASTExtractor, CSSValidationResult


# ═══════════════════════════════════════════════════════════════
# COLOR PARSING TESTS
# ═══════════════════════════════════════════════════════════════

class TestColorParsing:
    """Tests for CSS color string parsing."""

    def test_parse_hex_6(self):
        """#RRGGBB format."""
        assert parse_color("#ff0000") == (255, 0, 0, 1.0)
        assert parse_color("#00ff00") == (0, 255, 0, 1.0)
        assert parse_color("#0000ff") == (0, 0, 255, 1.0)
        assert parse_color("#000000") == (0, 0, 0, 1.0)
        assert parse_color("#ffffff") == (255, 255, 255, 1.0)

    def test_parse_hex_3(self):
        """#RGB shorthand format."""
        assert parse_color("#f00") == (255, 0, 0, 1.0)
        assert parse_color("#0f0") == (0, 255, 0, 1.0)
        assert parse_color("#00f") == (0, 0, 255, 1.0)
        assert parse_color("#fff") == (255, 255, 255, 1.0)

    def test_parse_hex_8(self):
        """#RRGGBBAA format with alpha."""
        result = parse_color("#ff000080")
        assert result[0] == 255
        assert result[1] == 0
        assert result[2] == 0
        assert abs(result[3] - 0.502) < 0.01  # 128/255 ≈ 0.502

    def test_parse_rgb(self):
        """rgb(r, g, b) format."""
        assert parse_color("rgb(255, 0, 0)") == (255, 0, 0, 1.0)
        assert parse_color("rgb(128, 128, 128)") == (128, 128, 128, 1.0)
        assert parse_color("rgb(0, 0, 0)") == (0, 0, 0, 1.0)

    def test_parse_rgba(self):
        """rgba(r, g, b, a) format."""
        assert parse_color("rgba(255, 0, 0, 1.0)") == (255, 0, 0, 1.0)
        assert parse_color("rgba(255, 0, 0, 0.5)") == (255, 0, 0, 0.5)
        assert parse_color("rgba(0, 0, 0, 0)") == (0, 0, 0, 0.0)

    def test_parse_named_colors(self):
        """Named CSS colors."""
        assert parse_color("black") == (0, 0, 0, 1.0)
        assert parse_color("white") == (255, 255, 255, 1.0)
        assert parse_color("red") == (255, 0, 0, 1.0)
        assert parse_color("green") == (0, 128, 0, 1.0)
        assert parse_color("blue") == (0, 0, 255, 1.0)

    def test_parse_transparent(self):
        """transparent keyword."""
        assert parse_color("transparent") == (0, 0, 0, 0.0)

    def test_parse_case_insensitive(self):
        """Colors should be parsed case-insensitively."""
        assert parse_color("RED") == (255, 0, 0, 1.0)
        assert parse_color("White") == (255, 255, 255, 1.0)
        assert parse_color("#FF0000") == (255, 0, 0, 1.0)

    def test_parse_invalid_returns_none(self):
        """Invalid color strings should return None."""
        assert parse_color("") is None
        assert parse_color("notacolor") is None
        assert parse_color(None) is None
        assert parse_color("hsl(120, 100%, 50%)") is None  # HSL not supported

    def test_parse_whitespace_handling(self):
        """Whitespace around color strings should be trimmed."""
        assert parse_color("  #ff0000  ") == (255, 0, 0, 1.0)
        assert parse_color("  rgb(255, 0, 0)  ") == (255, 0, 0, 1.0)


# ═══════════════════════════════════════════════════════════════
# sRGB LINEARIZATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestSRGBLinearization:
    """Tests for the WCAG 2.1 sRGB linearization formula."""

    def test_black_linearizes_to_zero(self):
        """Channel value 0 should linearize to 0.0."""
        assert linearize_srgb_channel(0) == 0.0

    def test_white_linearizes_to_one(self):
        """Channel value 255 should linearize to 1.0."""
        result = linearize_srgb_channel(255)
        assert abs(result - 1.0) < 0.001

    def test_low_values_use_linear_formula(self):
        """
        For sRGB values <= 0.04045 (about channel 10),
        the formula c/12.92 should be used.
        """
        # Channel 10 -> 10/255 = 0.0392 < 0.04045 -> use linear path
        c = 10 / 255.0
        expected = c / 12.92
        assert abs(linearize_srgb_channel(10) - expected) < 0.0001

    def test_high_values_use_gamma_formula(self):
        """
        For sRGB values > 0.04045,
        the formula ((c + 0.055) / 1.055) ^ 2.4 should be used.
        """
        # Channel 128 -> 128/255 = 0.502 > 0.04045 -> use gamma path
        c = 128 / 255.0
        expected = math.pow((c + 0.055) / 1.055, 2.4)
        result = linearize_srgb_channel(128)
        assert abs(result - expected) < 0.0001

    def test_midpoint_value(self):
        """Channel 128 (middle gray) should linearize to ~0.2158."""
        result = linearize_srgb_channel(128)
        assert abs(result - 0.2158) < 0.001


# ═══════════════════════════════════════════════════════════════
# RELATIVE LUMINANCE TESTS
# ═══════════════════════════════════════════════════════════════

class TestRelativeLuminance:
    """Tests for WCAG 2.1 relative luminance calculation."""

    def test_black_luminance_is_zero(self):
        """Pure black (0,0,0) has luminance 0."""
        assert relative_luminance(0, 0, 0) == 0.0

    def test_white_luminance_is_one(self):
        """Pure white (255,255,255) has luminance 1.0."""
        result = relative_luminance(255, 255, 255)
        assert abs(result - 1.0) < 0.001

    def test_red_luminance(self):
        """Pure red (255,0,0) luminance = 0.2126 * 1.0 = 0.2126."""
        result = relative_luminance(255, 0, 0)
        assert abs(result - 0.2126) < 0.001

    def test_green_luminance(self):
        """Pure green (0,255,0) luminance = 0.7152 * 1.0 = 0.7152."""
        result = relative_luminance(0, 255, 0)
        assert abs(result - 0.7152) < 0.001

    def test_blue_luminance(self):
        """Pure blue (0,0,255) luminance = 0.0722 * 1.0 = 0.0722."""
        result = relative_luminance(0, 0, 255)
        assert abs(result - 0.0722) < 0.001

    def test_gray_luminance(self):
        """Middle gray (128,128,128) luminance ≈ 0.2158."""
        result = relative_luminance(128, 128, 128)
        assert abs(result - 0.2158) < 0.001


# ═══════════════════════════════════════════════════════════════
# CONTRAST RATIO TESTS
# ═══════════════════════════════════════════════════════════════

class TestContrastRatio:
    """Tests for WCAG 2.1 contrast ratio calculation."""

    def test_black_on_white_is_21(self):
        """
        The maximum contrast ratio is black on white = 21:1.
        C = (1.0 + 0.05) / (0.0 + 0.05) = 1.05 / 0.05 = 21.0
        """
        ratio = contrast_ratio((0, 0, 0), (255, 255, 255))
        assert abs(ratio - 21.0) < 0.1

    def test_white_on_black_is_21(self):
        """Order shouldn't matter — always lighter/darker."""
        ratio = contrast_ratio((255, 255, 255), (0, 0, 0))
        assert abs(ratio - 21.0) < 0.1

    def test_identical_colors_is_1(self):
        """Same color on same color = 1:1 (no contrast)."""
        ratio = contrast_ratio((128, 128, 128), (128, 128, 128))
        assert abs(ratio - 1.0) < 0.001

    def test_gray_on_white_known_value(self):
        """
        #777777 on #FFFFFF is a known WCAG failure case.
        Expected contrast ratio ≈ 4.48:1 (fails AA normal text).
        """
        ratio = contrast_ratio((0x77, 0x77, 0x77), (255, 255, 255))
        assert abs(ratio - 4.48) < 0.1

    def test_low_contrast_pair(self):
        """Light gray on white should have very low contrast."""
        ratio = contrast_ratio((200, 200, 200), (255, 255, 255))
        assert ratio < 2.0  # Very low contrast


# ═══════════════════════════════════════════════════════════════
# FULL CONTRAST CHECK TESTS
# ═══════════════════════════════════════════════════════════════

class TestCheckContrast:
    """Tests for the full contrast check with WCAG level evaluation."""

    def test_black_on_white_passes_all(self):
        """Black on white passes every WCAG level."""
        result = check_contrast("#000000", "#ffffff")
        assert result.passes_aa_normal is True
        assert result.passes_aa_large is True
        assert result.passes_aaa_normal is True
        assert result.passes_aaa_large is True
        assert result.wcag_level_met == "AAA"
        assert abs(result.contrast_ratio - 21.0) < 0.1

    def test_gray_on_white_fails_aa_normal(self):
        """#777 on white has ~4.48:1, passes AA large but fails AA normal."""
        result = check_contrast("rgb(119, 119, 119)", "rgb(255, 255, 255)")
        assert result.passes_aa_large is True
        assert result.passes_aa_normal is False
        assert result.passes_aaa_normal is False

    def test_large_text_uses_lower_threshold(self):
        """Large text (>= 24px) only needs 3.0:1 for AA."""
        # rgb(128,128,128) on white has ~3.95:1 contrast — passes AA large (3.0:1) but fails AA normal (4.5:1)
        result = check_contrast("rgb(128, 128, 128)", "rgb(255, 255, 255)", font_size_px=24.0)
        assert result.is_large_text is True
        assert result.passes_required is True  # 3.95:1 >= 3.0:1 for large text

    def test_bold_large_text(self):
        """Bold text >= 14pt (18.67px) counts as large text."""
        result = check_contrast("rgb(150, 150, 150)", "rgb(255, 255, 255)",
                                font_size_px=19.0, font_weight=700)
        assert result.is_large_text is True

    def test_rgb_string_parsing(self):
        """Should correctly parse rgb() color format from browser."""
        result = check_contrast("rgb(0, 0, 0)", "rgb(255, 255, 255)")
        assert abs(result.contrast_ratio - 21.0) < 0.1

    def test_rgba_with_alpha(self):
        """Semi-transparent foreground should be composited over background."""
        result = check_contrast("rgba(0, 0, 0, 0.5)", "rgb(255, 255, 255)")
        # 50% black on white = medium gray, so contrast < 21:1
        assert result.contrast_ratio < 21.0
        assert result.contrast_ratio > 1.0


# ═══════════════════════════════════════════════════════════════
# LARGE TEXT DETECTION TESTS
# ═══════════════════════════════════════════════════════════════

class TestLargeText:
    """Tests for WCAG large text classification."""

    def test_normal_text(self):
        """16px normal weight is not large text."""
        assert _is_large_text(16.0, 400) is False

    def test_18pt_normal_is_large(self):
        """24px (18pt) at normal weight IS large text."""
        assert _is_large_text(24.0, 400) is True

    def test_14pt_bold_is_large(self):
        """18.67px (14pt) at bold weight IS large text."""
        assert _is_large_text(18.67, 700) is True

    def test_14pt_normal_is_not_large(self):
        """18.67px (14pt) at normal weight is NOT large text."""
        assert _is_large_text(18.67, 400) is False

    def test_30px_always_large(self):
        """Very large text is always classified as large."""
        assert _is_large_text(30.0, 400) is True
        assert _is_large_text(30.0, 700) is True


# ═══════════════════════════════════════════════════════════════
# ALPHA COMPOSITING TESTS
# ═══════════════════════════════════════════════════════════════

class TestAlphaComposite:
    """Tests for alpha compositing of semi-transparent colors."""

    def test_fully_opaque(self):
        """Fully opaque foreground returns foreground unchanged."""
        result = _alpha_composite((255, 0, 0, 1.0), (0, 0, 255, 1.0))
        assert result == (255, 0, 0)

    def test_fully_transparent(self):
        """Fully transparent foreground returns background."""
        result = _alpha_composite((255, 0, 0, 0.0), (0, 0, 255, 1.0))
        assert result == (0, 0, 255)

    def test_half_transparent(self):
        """50% red on blue = (128, 0, 128) approximately."""
        result = _alpha_composite((255, 0, 0, 0.5), (0, 0, 255, 1.0))
        assert abs(result[0] - 128) <= 1
        assert result[1] == 0
        assert abs(result[2] - 128) <= 1


# ═══════════════════════════════════════════════════════════════
# COLOR BLINDNESS SIMULATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestColorBlindness:
    """Tests for color vision deficiency simulation."""

    def test_protanopia_changes_red(self):
        """Protanopia (red-blind) should significantly alter pure red."""
        sim = simulate_color_blindness(255, 0, 0, "protanopia")
        # Red should be perceived differently — not (255, 0, 0)
        assert sim[0] != 255 or sim[1] != 0 or sim[2] != 0

    def test_black_unchanged(self):
        """Black should remain black in all color blindness types."""
        for cb_type in ["protanopia", "deuteranopia", "tritanopia"]:
            sim = simulate_color_blindness(0, 0, 0, cb_type)
            assert sim == (0, 0, 0)

    def test_white_approximately_unchanged(self):
        """White should remain approximately white."""
        for cb_type in ["protanopia", "deuteranopia", "tritanopia"]:
            sim = simulate_color_blindness(255, 255, 255, cb_type)
            assert all(abs(c - 255) < 5 for c in sim)

    def test_invalid_type_raises(self):
        """Invalid color blindness type should raise ValueError."""
        with pytest.raises(ValueError):
            simulate_color_blindness(255, 0, 0, "invalid_type")

    def test_contrast_for_color_blind(self):
        """check_contrast_for_color_blind should return results for all types."""
        results = check_contrast_for_color_blind("#000000", "#ffffff")
        assert "normal" in results
        assert "protanopia" in results
        assert "deuteranopia" in results
        assert "tritanopia" in results
        # Black on white should pass in all cases
        for vision_type, result in results.items():
            assert result.contrast_ratio > 15.0


# ═══════════════════════════════════════════════════════════════
# SUGGEST FIX COLOR TESTS
# ═══════════════════════════════════════════════════════════════

class TestSuggestFix:
    """Tests for the color fix suggestion engine."""

    def test_suggest_fix_for_low_contrast(self):
        """Should suggest a darker color for low contrast text."""
        suggestion = suggest_fix_color("rgb(180, 180, 180)", "rgb(255, 255, 255)")
        assert suggestion is not None
        assert suggestion.startswith("#")

    def test_no_fix_needed_for_high_contrast(self):
        """Black on white already passes — fix should still be found (it's already good)."""
        suggestion = suggest_fix_color("#000000", "#ffffff", target_ratio=4.5)
        # It should find #000000 at step 0
        assert suggestion is not None

    def test_fix_actually_meets_target(self):
        """Suggested fix should actually meet the target contrast ratio."""
        suggestion = suggest_fix_color("rgb(180, 180, 180)", "rgb(255, 255, 255)", 4.5)
        if suggestion:
            result = check_contrast(suggestion, "rgb(255, 255, 255)")
            assert result.contrast_ratio >= 4.5


# ═══════════════════════════════════════════════════════════════
# FULL AUDIT ON COMPUTED STYLES TESTS
# ═══════════════════════════════════════════════════════════════

class TestAuditComputedStyles:
    """Tests for the full audit pipeline on browser-extracted styles."""

    def test_audit_catches_low_contrast(self):
        """Audit should catch elements with insufficient contrast."""
        styles = [
            {
                "tag": "p",
                "text": "This text is hard to read",
                "color": "rgb(180, 180, 180)",
                "backgroundColor": "rgb(255, 255, 255)",
                "fontSize": "16px",
                "fontWeight": "400",
                "boundingBox": {"x": 0, "y": 0, "width": 100, "height": 20},
                "selector": "p.light-text",
            },
        ]
        result = audit_computed_styles(styles, url="https://test.com")
        assert result.total_violations > 0
        assert result.contrast_violations[0].contrast_ratio < 4.5

    def test_audit_passes_good_contrast(self):
        """Audit should pass elements with sufficient contrast."""
        styles = [
            {
                "tag": "p",
                "text": "This text is readable",
                "color": "rgb(0, 0, 0)",
                "backgroundColor": "rgb(255, 255, 255)",
                "fontSize": "16px",
                "fontWeight": "400",
                "boundingBox": {"x": 0, "y": 0, "width": 100, "height": 20},
                "selector": "p.dark-text",
            },
        ]
        result = audit_computed_styles(styles, url="https://test.com")
        assert result.total_violations == 0
        assert result.overall_score == 100.0

    def test_audit_severity_levels(self):
        """Very low contrast should get higher severity."""
        styles = [
            {
                "tag": "p",
                "text": "Barely visible",
                "color": "rgb(240, 240, 240)",
                "backgroundColor": "rgb(255, 255, 255)",
                "fontSize": "16px",
                "fontWeight": "400",
                "boundingBox": {"x": 0, "y": 0, "width": 100, "height": 20},
                "selector": "p.invisible",
            },
        ]
        result = audit_computed_styles(styles)
        assert result.total_violations > 0
        # Very low contrast = critical severity
        assert result.contrast_violations[0].severity == "critical"

    def test_audit_empty_styles(self):
        """Empty input should return clean result with no violations."""
        result = audit_computed_styles([])
        assert result.total_violations == 0
        assert result.total_elements_checked == 0

    def test_audit_multiple_elements(self):
        """Audit should process multiple elements correctly."""
        styles = [
            {
                "tag": "h1",
                "text": "Title",
                "color": "rgb(0, 0, 0)",
                "backgroundColor": "rgb(255, 255, 255)",
                "fontSize": "32px",
                "fontWeight": "700",
                "boundingBox": {"x": 0, "y": 0, "width": 500, "height": 40},
                "selector": "h1",
            },
            {
                "tag": "p",
                "text": "Faded paragraph",
                "color": "rgb(200, 200, 200)",
                "backgroundColor": "rgb(255, 255, 255)",
                "fontSize": "14px",
                "fontWeight": "400",
                "boundingBox": {"x": 0, "y": 50, "width": 500, "height": 20},
                "selector": "p.faded",
            },
        ]
        result = audit_computed_styles(styles)
        assert result.total_elements_checked == 2
        assert result.total_violations == 1  # Only the faded paragraph


# ═══════════════════════════════════════════════════════════════
# DOM PARSER TESTS
# ═══════════════════════════════════════════════════════════════

class TestDOMParser:
    """Tests for the HTML DOM accessibility parser."""

    def setup_method(self):
        self.parser = DOMParser()

    def test_missing_alt_on_image(self):
        """Should detect images without alt attributes."""
        html = '<html><body><img src="photo.jpg"></body></html>'
        result = self.parser.analyze(html)
        assert result.images_missing_alt == 1
        assert any(v.rule_id == "img-alt" for v in result.violations)

    def test_image_with_alt_passes(self):
        """Images with alt attributes should not be flagged."""
        html = '<html><body><img src="photo.jpg" alt="A photo"></body></html>'
        result = self.parser.analyze(html)
        assert result.images_missing_alt == 0

    def test_decorative_image_passes(self):
        """alt='' (empty alt) is valid for decorative images."""
        html = '<html><body><img src="divider.png" alt=""></body></html>'
        result = self.parser.analyze(html)
        assert result.images_missing_alt == 0

    def test_missing_lang_attribute(self):
        """Should detect missing lang on <html>."""
        html = "<html><body>Hello</body></html>"
        result = self.parser.analyze(html)
        assert not result.has_lang_attribute
        assert any(v.rule_id == "html-has-lang" for v in result.violations)

    def test_has_lang_attribute(self):
        """Should not flag when lang is present."""
        html = '<html lang="en"><body>Hello</body></html>'
        result = self.parser.analyze(html)
        assert result.has_lang_attribute

    def test_missing_page_title(self):
        """Should detect missing or empty <title>."""
        html = "<html><head></head><body>Hello</body></html>"
        result = self.parser.analyze(html)
        assert not result.has_page_title
        assert any(v.rule_id == "page-has-title" for v in result.violations)

    def test_heading_hierarchy_skip(self):
        """Should detect skipped heading levels (h1 -> h3)."""
        html = "<html><body><h1>Title</h1><h3>Subtitle</h3></body></html>"
        result = self.parser.analyze(html)
        assert any(v.rule_id == "heading-order" for v in result.violations)

    def test_correct_heading_hierarchy(self):
        """h1 -> h2 -> h3 should not be flagged."""
        html = "<html><body><h1>T</h1><h2>S</h2><h3>S2</h3></body></html>"
        result = self.parser.analyze(html)
        assert not any(v.rule_id == "heading-order" for v in result.violations)

    def test_missing_link_text(self):
        """Links without discernible text should be flagged."""
        html = '<html><body><a href="/page"></a></body></html>'
        result = self.parser.analyze(html)
        assert result.links_missing_text == 1

    def test_link_with_text_passes(self):
        """Links with visible text should not be flagged."""
        html = '<html><body><a href="/page">Click here</a></body></html>'
        result = self.parser.analyze(html)
        assert result.links_missing_text == 0

    def test_link_with_aria_label(self):
        """Links with aria-label should not be flagged."""
        html = '<html><body><a href="/page" aria-label="Go to page"></a></body></html>'
        result = self.parser.analyze(html)
        assert result.links_missing_text == 0

    def test_input_without_label(self):
        """Form inputs without labels should be flagged."""
        html = '<html><body><input type="text" id="name"></body></html>'
        result = self.parser.analyze(html)
        assert result.inputs_missing_labels == 1

    def test_input_with_label(self):
        """Form inputs with associated labels should pass."""
        html = '<html><body><label for="name">Name</label><input type="text" id="name"></body></html>'
        result = self.parser.analyze(html)
        assert result.inputs_missing_labels == 0

    def test_viewport_no_user_scale(self):
        """Should detect viewport meta disabling zoom."""
        html = '<html><head><meta name="viewport" content="width=device-width, user-scalable=no"></head></html>'
        result = self.parser.analyze(html)
        assert any(v.rule_id == "meta-viewport-scale" for v in result.violations)

    def test_autoplay_media(self):
        """Should detect autoplaying audio/video."""
        html = '<html><body><video autoplay src="video.mp4"></video></body></html>'
        result = self.parser.analyze(html)
        assert any(v.rule_id == "no-autoplay" for v in result.violations)

    def test_empty_html(self):
        """Empty HTML should return empty result, not crash."""
        result = self.parser.analyze("")
        assert result.total_violations == 0


# ═══════════════════════════════════════════════════════════════
# AST EXTRACTOR TESTS
# ═══════════════════════════════════════════════════════════════

class TestASTExtractor:
    """Tests for the CSS AST extractor and validator."""

    def setup_method(self):
        self.extractor = ASTExtractor()

    def test_extract_style_block(self):
        """Should extract CSS rules from <style> blocks."""
        html = '<html><head><style>body { color: red; }</style></head></html>'
        rules = self.extractor.extract_css_from_html(html)
        assert len(rules) >= 1
        assert any(r.selector == "body" for r in rules)

    def test_extract_inline_styles(self):
        """Should extract inline style attributes."""
        html = '<html><body><p style="color: blue; font-size: 14px;">Text</p></body></html>'
        rules = self.extractor.extract_css_from_html(html)
        assert any(r.source == "inline" for r in rules)

    def test_validate_valid_css(self):
        """Valid CSS should pass validation."""
        css = "p { color: #333333; font-size: 16px; }"
        result = self.extractor.validate_css_patch(css)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_empty_css(self):
        """Empty CSS should fail validation."""
        result = self.extractor.validate_css_patch("")
        assert result.is_valid is False

    def test_validate_rejects_javascript_injection(self):
        """Should reject CSS with JavaScript injection attempts."""
        css = 'body { background: expression(alert("XSS")); }'
        result = self.extractor.validate_css_patch(css)
        assert result.is_valid is False
        assert any("expression" in e.lower() for e in result.errors)

    def test_validate_rejects_javascript_url(self):
        """Should reject CSS with javascript: URLs."""
        css = 'a { background: url(javascript:void(0)); }'
        result = self.extractor.validate_css_patch(css)
        assert result.is_valid is False

    def test_validate_multiple_rules(self):
        """Should handle multiple CSS rules."""
        css = """
        h1 { color: #111; }
        p { font-size: 18px; }
        .warning { border: 2px solid red; }
        """
        result = self.extractor.validate_css_patch(css)
        assert result.is_valid is True
        assert len(result.parsed_rules) == 3

    def test_build_unified_diagnostic(self):
        """Should build a unified diagnostic from DOM + WCAG results."""
        dom_result = DOMAnalysisResult()
        from dom_accessibility.wcag_checker import AccessibilityAuditResult
        wcag_result = AccessibilityAuditResult()

        diagnostic = self.extractor.build_unified_diagnostic(
            dom_result=dom_result,
            wcag_result=wcag_result,
            url="https://example.com",
        )

        assert diagnostic.url == "https://example.com"
        assert diagnostic.timestamp  # Should have a timestamp

    def test_diagnostic_to_json(self):
        """Should serialize diagnostic to valid JSON."""
        from dom_accessibility.ast_extractor import UnifiedDiagnostic
        diagnostic = UnifiedDiagnostic(url="https://test.com")
        json_str = self.extractor.diagnostic_to_json(diagnostic)
        import json
        parsed = json.loads(json_str)
        assert parsed["url"] == "https://test.com"

    def test_find_rules_for_selector(self):
        """Should find matching CSS rules by selector."""
        from dom_accessibility.ast_extractor import CSSRule
        rules = [
            CSSRule(selector="p.intro", declarations={"color": "red"}, source="test"),
            CSSRule(selector="h1", declarations={"font-size": "32px"}, source="test"),
            CSSRule(selector="p", declarations={"margin": "10px"}, source="test"),
        ]
        matches = self.extractor.find_rules_for_selector(rules, "p")
        assert len(matches) >= 2  # Should match "p" and "p.intro"


# ═══════════════════════════════════════════════════════════════
# GAMMA COMPRESSION TESTS (inverse of linearization)
# ═══════════════════════════════════════════════════════════════

class TestGammaCompress:
    """Tests for the sRGB gamma compression (inverse of linearize)."""

    def test_zero_stays_zero(self):
        assert _gamma_compress(0.0) == 0.0

    def test_one_stays_one(self):
        result = _gamma_compress(1.0)
        assert abs(result - 1.0) < 0.001

    def test_roundtrip(self):
        """Linearize then compress should return original value."""
        for channel in [0, 10, 50, 128, 200, 255]:
            c = channel / 255.0
            linearized = linearize_srgb_channel(channel)
            compressed = _gamma_compress(linearized)
            assert abs(compressed - c) < 0.01
